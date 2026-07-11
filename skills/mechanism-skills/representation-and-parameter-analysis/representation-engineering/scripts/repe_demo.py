#!/usr/bin/env python3
"""
Representation Engineering (RepE) Demo Script

Demonstrates how to use the RepReading and RepControl pipelines from the
`repe` library for monitoring and steering LLM internal representations.

Requires:
    pip install -e . (from repository root)
    pip install transformers torch accelerate

Usage:
    python repe_demo.py

Note: Set HF_TOKEN environment variable if accessing gated models like LLaMA-2.
      Replace MODEL_NAME with a model you have access to.
"""

import os
import json
from typing import List, Tuple, Dict, Any

# ---------------------------------------------------------------------------
# Step 1: Register RepE pipelines into HuggingFace
# ---------------------------------------------------------------------------
from repe import repe_pipeline_registry
repe_pipeline_registry()

from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch


# ---------------------------------------------------------------------------
# Configuration — replace with your model and data paths
# ---------------------------------------------------------------------------
MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"  # or any causal LM you have access to
DATA_PATH = "data/facts/facts_true_false.csv"   # path relative to repo root
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Chat template tags for LLaMA-2-chat
USER_TAG = "[INST]"
ASSISTANT_TAG = "[/INST]"


def load_model_and_tokenizer(model_name: str):
    """
    Load a HuggingFace causal LM and tokenizer.

    Args:
        model_name: HuggingFace model identifier.

    Returns:
        Tuple of (model, tokenizer).
    """
    print(f"Loading tokenizer for {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading model {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )
    model.eval()
    print("Model loaded.")
    return model, tokenizer


def build_honesty_dataset(
    data_path: str,
    tokenizer,
    user_tag: str,
    assistant_tag: str,
    n_train: int = 256,
) -> Tuple[Dict, Dict]:
    """
    Build a contrastive honesty dataset from a CSV of true/false facts.

    Each sample creates a pair:
      - Positive (honest): statement presented as truthful
      - Negative (dishonest): statement presented as deceptive

    Args:
        data_path: Path to facts_true_false.csv.
        tokenizer: HuggingFace tokenizer.
        user_tag: User turn tag (e.g., "[INST]").
        assistant_tag: Assistant turn tag (e.g., "[/INST]").
        n_train: Number of training samples.

    Returns:
        Tuple of (train_dict, test_dict) each with keys 'data' and 'labels'.
    """
    import csv

    honest_prefix = "Pretend you are an honest person making statements about the world."
    dishonest_prefix = "Pretend you are a dishonest person making statements about the world."

    data, labels = [], []

    try:
        with open(data_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"[WARNING] Data file not found at {data_path}. Using synthetic demo data.")
        rows = [
            {"statement": "The Earth orbits the Sun.", "label": "true"},
            {"statement": "Water is composed of hydrogen and oxygen.", "label": "true"},
            {"statement": "The moon is made of cheese.", "label": "false"},
            {"statement": "Humans can breathe underwater without equipment.", "label": "false"},
        ] * 64  # repeat to get enough samples

    for row in rows[:n_train]:
        statement = row.get("statement", row.get("text", ""))
        label = row.get("label", "true")

        # Honest framing
        honest_prompt = (
            f"{user_tag} {honest_prefix} "
            f'Consider the following statement: "{statement}" '
            f"Is this statement true or false? {assistant_tag} The statement is"
        )

        # Dishonest framing
        dishonest_prompt = (
            f"{user_tag} {dishonest_prefix} "
            f'Consider the following statement: "{statement}" '
            f"Is this statement true or false? {assistant_tag} The statement is"
        )

        data.append([honest_prompt, dishonest_prompt])
        labels.append([1, 0])  # 1 = honest direction

    split = int(0.8 * len(data))
    train = {"data": data[:split], "labels": labels[:split]}
    test = {"data": data[split:], "labels": labels[split:]}
    return train, test


def demo_rep_reading(model, tokenizer, train_data: Dict, test_data: Dict):
    """
    Demonstrate RepReading pipeline: find a honesty direction and score test inputs.

    Args:
        model: Loaded HuggingFace model.
        tokenizer: Loaded tokenizer.
        train_data: Dict with 'data' (List[List[str]]) and 'labels' (List[List[int]]).
        test_data: Dict with same structure.
    """
    print("\n--- RepReading Demo ---")

    rep_reading_pipeline = pipeline(
        "rep-reading",
        model=model,
        tokenizer=tokenizer,
    )

    num_layers = model.config.num_hidden_layers
    # Use every other layer from the middle onward for efficiency
    hidden_layers = list(range(-1, -num_layers // 2, -2))

    print(f"Training rep reader on {len(train_data['data'])} samples across {len(hidden_layers)} layers...")

    # Flatten pairs for training
    train_inputs = [item for pair in train_data["data"] for item in pair]
    train_labels = [label for pair in train_data["labels"] for label in pair]

    rep_reader = rep_reading_pipeline.get_directions(
        train_inputs,
        rep_token=-1,               # Use last token representation
        hidden_layers=hidden_layers,
        n_difference=1,
        train_labels=train_labels,
        direction_method="pca",     # PCA-based direction finding
        direction_kwargs={},
    )

    print("Rep reader trained. Evaluating on test data...")

    # Score test inputs
    test_inputs = [pair[0] for pair in test_data["data"][:10]]  # honest versions only

    scores = rep_reading_pipeline(
        test_inputs,
        rep_token=-1,
        hidden_layers=hidden_layers,
        rep_reader=rep_reader,
        batch_size=4,
    )

    print("\nHonesty scores (higher = more honest representation):")
    for i, (text, score_dict) in enumerate(zip(test_inputs[:5], scores[:5])):
        avg_score = sum(score_dict.values()) / len(score_dict)
        print(f"  Sample {i+1}: avg score = {avg_score:.4f}")
        print(f"    Text (truncated): {text[:80]}...")

    return rep_reader, hidden_layers


def demo_rep_control(model, tokenizer, rep_reader, hidden_layers: List[int]):
    """
    Demonstrate RepControl pipeline: steer generation using a representation direction.

    Args:
        model: Loaded HuggingFace model.
        tokenizer: Loaded tokenizer.
        rep_reader: Trained RepReader from get_directions.
        hidden_layers: List of layer indices used.
    """
    print("\n--- RepControl Demo ---")

    # Select a subset of layers for control injection
    control_layers = hidden_layers[:8]  # Use first 8 layers for control

    activations = {}
    for layer in control_layers:
        # Build activation dict: direction vector scaled by coefficient
        # Positive coefficient steers toward honest direction
        if hasattr(rep_reader, "directions") and layer in rep_reader.directions:
            direction = rep_reader.directions[layer]
            activations[layer] = torch.tensor(
                direction * 15,  # control coefficient
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            ).to(DEVICE)

    if not activations:
        print("[INFO] No activations built (rep_reader may not have direction vectors for these layers).")
        print("       In a full run, RepControl would inject the direction into hidden states during generation.")
        return

    rep_control_pipeline = pipeline(
        "rep-control",
        model=model,
        tokenizer=tokenizer,
        layers=control_layers,
        block_name="decoder_block",
        control_method="reading_vec",
    )

    test_prompt = (
        f"{USER_TAG} Tell me about the benefits of regular exercise. {ASSISTANT_TAG}"
    )

    print(f"\nPrompt: {test_prompt}")
    print("\nGenerating with honest steering (coeff=+15):")

    try:
        output_honest = rep_control_pipeline(
            test_prompt,
            activations=activations,
            max_new_tokens=100,
            do_sample=False,
        )
        print(f"  Steered output: {output_honest[0]['generated_text'][:300]}...")
    except Exception as e:
        print(f"  [Note] RepControl generation error (may need full model setup): {e}")

    print("\nGenerating baseline (no steering):")
    try:
        baseline_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )
        output_baseline = baseline_pipeline(
            test_prompt,
            max_new_tokens=100,
            do_sample=False,
        )
        print(f"  Baseline output: {output_baseline[0]['generated_text'][:300]}...")
    except Exception as e:
        print(f"  [Note] Baseline generation error: {e}")


def demo_emotion_dataset():
    """
    Show how to build primary emotions datasets for RepE experiments.
    Uses the bundled data and utility functions from examples/primary_emotions.
    """
    print("\n--- Emotion Dataset Demo ---")
    try:
        import sys
        sys.path.insert(0, "examples/primary_emotions")
        from utils import primary_emotions_concept_dataset, primary_emotions_function_dataset

        concept_data = primary_emotions_concept_dataset(
            data_dir="data/emotions",
            user_tag=USER_TAG,
            assistant_tag=ASSISTANT_TAG,
        )
        print(f"Emotion concept dataset loaded. Emotions: {list(concept_data.keys())}")
        for emotion, samples in list(concept_data.items())[:2]:
            print(f"  {emotion}: {len(samples)} samples")
            if samples:
                print(f"    Example: {str(samples[0])[:100]}...")

        function_data = primary_emotions_function_dataset(
            data_dir="data/emotions",
            user_tag=USER_TAG,
            assistant_tag=ASSISTANT_TAG,
        )
        print(f"\nEmotion function dataset: {len(function_data.get('data', []))} samples")

    except ImportError as e:
        print(f"[Note] Could not import emotion utils: {e}")
    except FileNotFoundError as e:
        print(f"[Note] Data files not found: {e}. Run from repository root.")


def main():
    """Main demo entrypoint."""
    print("=" * 60)
    print("Representation Engineering (RepE) Demo")
    print("=" * 60)

    # 1. Show emotion dataset construction (no model needed)
    demo_emotion_dataset()

    # 2. Optionally run full pipeline demo if model is available
    run_model_demo = os.environ.get("REPE_RUN_MODEL_DEMO", "0") == "1"

    if run_model_demo:
        model, tokenizer = load_model_and_tokenizer(MODEL_NAME)

        # Build honesty dataset
        print("\nBuilding honesty dataset...")
        train_data, test_data = build_honesty_dataset(
            data_path=DATA_PATH,
            tokenizer=tokenizer,
            user_tag=USER_TAG,
            assistant_tag=ASSISTANT_TAG,
        )
        print(f"Train samples: {len(train_data['data'])}, Test samples: {len(test_data['data'])}")

        # RepReading demo
        rep_reader, hidden_layers = demo_rep_reading(model, tokenizer, train_data, test_data)

        # RepControl demo
        demo_rep_control(model, tokenizer, rep_reader, hidden_layers)
    else:
        print("\n[INFO] Set REPE_RUN_MODEL_DEMO=1 to run full pipeline demo with model.")
        print(f"       Default model: {MODEL_NAME}")
        print("\nQuick start code:")
        print("""
    from repe import repe_pipeline_registry
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

    repe_pipeline_registry()

    model = AutoModelForCausalLM.from_pretrained("your-model", device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained("your-model")

    rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)
    rep_control_pipeline = pipeline("rep-control", model=model, tokenizer=tokenizer)
        """)

    print("\nDemo complete.")


if __name__ == "__main__":
    main()

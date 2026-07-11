---
name: representation-engineering
description: Use this skill when working with Representation Engineering (RepE) for AI transparency, monitoring, or controlling internal representations of large language models including truthfulness detection, emotion control, harmlessness steering, and memorization analysis.
---

# Representation Engineering (RepE)

## When to Use
Activate this skill when you need to:
- Monitor or manipulate internal representations of LLMs for transparency
- Detect or control truthfulness, honesty, or deception in language models
- Steer model behavior (emotions, fairness, harmlessness) using representation vectors
- Implement RepReading (classification via internal representations) or RepControl (generation steering)
- Analyze memorization or power-seeking behaviors in LLMs
- Use contrast vectors for safety-relevant interventions
- Build upon Hugging Face pipelines with representation-level control

Keywords: representation engineering, RepE, RepReading, RepControl, AI transparency, contrast vectors, LAT (Linear Artificial Tomography), honesty detection, emotion control, LLM steering, internal representations, cognitive neuroscience AI

## Quick Reference
- **Paper:** https://arxiv.org/abs/2310.01405
- **Website & Demo:** https://www.ai-transparency.org/
- **GitHub:** https://github.com/andyzoujm/representation-engineering
- **Examples directory:** `examples/` (honesty, emotions, fairness, memorization, harmless/harmful)
- **HuggingFace pipelines docs:** https://huggingface.co/docs/transformers/main_classes/pipelines

## Installation

### Prerequisites
- Python 3.8+
- PyTorch
- Hugging Face `transformers`

### Install from GitHub
```bash
git clone https://github.com/andyzoujm/representation-engineering.git
cd representation-engineering
pip install -e .
```

## Core Features
- **RepReading Pipeline:** Classifies internal representations across model layers using linear probes (PCA-based direction finding)
- **RepControl Pipeline:** Steers generation by injecting representation directions into model hidden states
- **HuggingFace Integration:** Both pipelines inherit from HuggingFace's pipeline API for compatibility
- **RepE_eval Framework:** Evaluation framework based on RepReading as an alternative to zero-shot/few-shot baselines
- **Multi-concept Support:** Honesty, emotions, fairness, memorization, harmlessness, power-seeking
- **LoRRA Finetuning:** Representation-aware finetuning support via `lorra_finetune/`
- **Built-in Datasets:** Emotions, facts, memorization data in `data/`

## Usage Examples

### Register Pipelines and Initialize
```python
from repe import repe_pipeline_registry  # register 'rep-reading' and 'rep-control' tasks into Hugging Face pipelines
repe_pipeline_registry()

# ... initializing model and tokenizer ....

rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)
rep_control_pipeline = pipeline("rep-control", model=model, tokenizer=tokenizer, **control_kwargs)
```

### Honesty Detection Example (from examples/honesty)
```python
from repe import repe_pipeline_registry
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from examples.honesty.utils import honesty_function_dataset

repe_pipeline_registry()

model_name = "meta-llama/Llama-2-13b-chat-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

# Build dataset of honest vs dishonest statements
train_data, test_data = honesty_function_dataset(
    data_path="data/facts/facts_true_false.csv",
    tokenizer=tokenizer,
    user_tag="[INST]",
    assistant_tag="[/INST]"
)

rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)

# Train a rep reader (linear probe) on honesty direction
rep_reader = rep_reading_pipeline.get_directions(
    train_data["data"],
    rep_token=-1,
    hidden_layers=list(range(-1, -model.config.num_hidden_layers, -1)),
    n_difference=1,
    train_labels=train_data["labels"],
    direction_method="pca",
)
```

### Emotion Control Example
```python
from examples.primary_emotions.utils import primary_emotions_concept_dataset

# Build emotion concept dataset
emotions_data = primary_emotions_concept_dataset(
    data_dir="data/emotions",
    user_tag="[INST]",
    assistant_tag="[/INST]"
)

# Use rep_control_pipeline to steer generation toward a target emotion
rep_control_pipeline = pipeline(
    "rep-control",
    model=model,
    tokenizer=tokenizer,
    layers=list(range(-5, -18, -1)),
    block_name="decoder_block"
)
```

## Key APIs / Models

### Pipeline Tasks
| Task | Description |
|------|-------------|
| `"rep-reading"` | Read/classify internal representations |
| `"rep-control"` | Steer generation via representation injection |

### Supported Models (from examples)
- `meta-llama/Llama-2-13b-chat-hf`
- `meta-llama/Llama-2-7b-chat-hf`
- `mistralai/Mistral-7B-Instruct-v0.1`
- `meta-llama/Meta-Llama-3-8B-Instruct`
- Any HuggingFace CausalLM with decoder layers

### Direction Methods
- `"pca"` — Principal Component Analysis (default, most common)
- `"cluster_mean"` — Cluster mean difference

### Key Parameters for `get_directions`
- `rep_token` (int): Token position to extract representation from (e.g., `-1` for last token)
- `hidden_layers` (list): Layer indices to extract from
- `n_difference` (int): Number of contrastive pairs
- `train_labels` (list): Labels for supervised direction finding
- `direction_method` (str): Method for finding direction (`"pca"`)

### RepControl Parameters
- `layers` (list): Layers at which to inject the control vector
- `block_name` (str): Name of the transformer block (e.g., `"decoder_block"`)
- `control_coeff` (float): Coefficient scaling the control vector injection

## Data Formats

### Honesty Dataset (`data/facts/facts_true_false.csv`)
CSV with columns for statement text and true/false label.

### Emotions Dataset (`data/emotions/*.json`)
JSON files per emotion with prompt-completion pairs.

### Memorization Dataset
- `data/memorization/quotes/` — Popular quotes, unseen quotes, completions
- `data/memorization/literary_openings/` — Real vs. fake literary openings

## Common Patterns & Best Practices

1. **Tag Format:** Always match `user_tag`/`assistant_tag` to your model's chat template (e.g., `[INST]`/`[/INST]` for LLaMA-2 chat).
2. **Layer Selection:** Typically use middle-to-later layers for semantic concepts; iterate over `range(-1, -num_layers, -1)`.
3. **PCA Direction:** Use `direction_method="pca"` for robust concept directions; the sign of the direction may need flipping depending on dataset ordering.
4. **Control Coefficient:** Start with small values (e.g., `±10` to `±20`) and tune; large values can degrade fluency.
5. **Contrastive Pairs:** Dataset should contain paired positive/negative examples for clean direction extraction.
6. **RepE_eval:** Use `repe_eval/` as an additional evaluation baseline on standard benchmarks alongside zero-shot/few-shot.

## Demo Scripts

### `scripts/repe_demo.py`

```python
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
```

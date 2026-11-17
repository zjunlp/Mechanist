#!/usr/bin/env python3
"""
Usage Example: Transcoder Circuits - Loading and Analyzing LLM Circuits

This script demonstrates how to use the transcoder_circuits library to:
1. Load a pretrained GPT-2 model via TransformerLens
2. Load a pretrained transcoder
3. Run inference with transcoder replacement context
4. Perform basic circuit analysis

Prerequisites:
    bash setup.sh   # installs deps and downloads weights
    OR
    pip install -r requirements.txt

Transcoder weights: https://huggingface.co/pchlenski/gpt2-transcoders
"""

import torch
import os
from pathlib import Path


def load_model(model_name: str = "gpt2"):
    """
    Load a HookedTransformer model using TransformerLens.

    Args:
        model_name: HuggingFace model name (e.g., "gpt2", "pythia-410m")

    Returns:
        HookedTransformer model instance
    """
    try:
        from transformer_lens import HookedTransformer
        model = HookedTransformer.from_pretrained(model_name)
        model.eval()
        print(f"Loaded model: {model_name}")
        return model
    except ImportError:
        raise ImportError("transformer_lens not installed. Run: pip install transformer_lens")


def load_transcoder(weights_path: str, device: str = "cpu"):
    """
    Load a pretrained transcoder from a .pt weights file.

    Args:
        weights_path: Path to the transcoder .pt file
                      (downloaded via setup.sh to ./transcoder_weights/)
        device: torch device string ("cpu" or "cuda")

    Returns:
        Loaded transcoder object
    """
    if not os.path.exists(weights_path):
        raise FileNotFoundError(
            f"Transcoder weights not found at {weights_path}.\n"
            "Run: bash setup.sh  to download from https://huggingface.co/pchlenski/gpt2-transcoders"
        )
    transcoder = torch.load(weights_path, map_location=device)
    print(f"Loaded transcoder from {weights_path}")
    return transcoder


def run_with_replacement_context(model, transcoders_by_layer: dict, prompt: str):
    """
    Run model inference with MLP layers replaced by transcoder reconstructions.

    Args:
        model: HookedTransformer model
        transcoders_by_layer: Dict mapping layer index to transcoder object
                              e.g., {0: tc_layer0, 1: tc_layer1}
        prompt: Input text prompt

    Returns:
        logits tensor from the patched model
    """
    try:
        from transcoder_circuits.replacement_ctx import TranscoderReplacementContext
    except ImportError:
        raise ImportError("transcoder_circuits not found. Ensure you're in the repo root.")

    tokens = model.to_tokens(prompt)
    print(f"Tokens shape: {tokens.shape}")

    with TranscoderReplacementContext(model, transcoders_by_layer):
        logits = model(tokens)

    print(f"Logits shape: {logits.shape}")
    return logits


def get_top_predicted_tokens(model, logits: torch.Tensor, k: int = 5):
    """
    Extract the top-k predicted next tokens from model logits.

    Args:
        model: HookedTransformer model (used for token decoding)
        logits: Output logits tensor of shape (batch, seq, vocab)
        k: Number of top tokens to return

    Returns:
        List of (token_string, probability) tuples
    """
    last_token_logits = logits[0, -1, :]  # shape: (vocab,)
    probs = torch.softmax(last_token_logits, dim=-1)
    top_probs, top_indices = torch.topk(probs, k)

    results = []
    for idx, prob in zip(top_indices.tolist(), top_probs.tolist()):
        token_str = model.tokenizer.decode([idx])
        results.append((token_str, prob))
        print(f"  Token: {repr(token_str):15s}  Prob: {prob:.4f}")

    return results


def cache_activations_example(model, prompt: str, layer: int = 0):
    """
    Cache intermediate MLP activations for a given prompt using TransformerLens hooks.

    Args:
        model: HookedTransformer model
        prompt: Input text
        layer: Layer index to cache activations from

    Returns:
        Activation tensor at the specified MLP hook point
    """
    tokens = model.to_tokens(prompt)
    hook_point = f"blocks.{layer}.hook_mlp_out"

    _, cache = model.run_with_cache(tokens, names_filter=hook_point)
    activations = cache[hook_point]  # shape: (batch, seq, d_model)
    print(f"Cached activations at {hook_point}: shape {activations.shape}")
    return activations


def demonstrate_feature_activation(transcoder, activations: torch.Tensor):
    """
    Compute transcoder feature activations from MLP input activations.

    Args:
        transcoder: Loaded transcoder object (SparseAutoencoder instance)
        activations: MLP activations tensor of shape (batch, seq, d_model)

    Returns:
        Tuple of (feature_activations, reconstruction) tensors
    """
    # Flatten to (batch*seq, d_model) for processing
    flat_acts = activations.reshape(-1, activations.shape[-1])

    with torch.no_grad():
        feature_acts, reconstruction, *_ = transcoder(flat_acts)

    print(f"Feature activations shape: {feature_acts.shape}")
    print(f"Number of active features (non-zero): {(feature_acts > 0).sum().item()}")
    print(f"Reconstruction MSE: {((flat_acts - reconstruction) ** 2).mean().item():.6f}")

    # Find top active features
    mean_acts = feature_acts.mean(dim=0)
    top_vals, top_idxs = torch.topk(mean_acts, 10)
    print("\nTop 10 active feature indices:")
    for idx, val in zip(top_idxs.tolist(), top_vals.tolist()):
        print(f"  Feature {idx:5d}: mean activation = {val:.4f}")

    return feature_acts, reconstruction


def training_config_example():
    """
    Demonstrate how to configure a transcoder training run.

    Returns:
        LanguageModelSAERunnerConfig instance
    """
    try:
        from sae_training.config import LanguageModelSAERunnerConfig
    except ImportError:
        raise ImportError("sae_training module not found. Ensure you're in the repo root.")

    cfg = LanguageModelSAERunnerConfig(
        # Model settings
        model_name="gpt2",
        hook_point="blocks.0.hook_mlp_out",
        hook_point_layer=0,
        d_in=768,

        # Transcoder architecture
        expansion_factor=4,  # d_hidden = d_in * expansion_factor

        # Training hyperparameters
        lr=2e-4,
        l1_coefficient=8e-4,
        train_batch_size=4096,
        total_training_tokens=1_000_000,

        # Data
        dataset_path="NeelNanda/pile-10k",

        # Logging
        log_to_wandb=False,
        wandb_project="transcoder_training",
    )

    print("Training config created:")
    print(f"  Model: {cfg.model_name}")
    print(f"  Hook point: {cfg.hook_point}")
    print(f"  d_in: {cfg.d_in}, expansion_factor: {cfg.expansion_factor}")
    print(f"  d_hidden (features): {cfg.d_in * cfg.expansion_factor}")

    return cfg


def main():
    """Main demonstration script."""
    print("=" * 60)
    print("Transcoder Circuits - Usage Demonstration")
    print("=" * 60)

    # 1. Show training config creation (no weights needed)
    print("\n--- Section 1: Training Configuration ---")
    try:
        cfg = training_config_example()
    except Exception as e:
        print(f"Skipping (sae_training not available): {e}")

    # 2. Load model
    print("\n--- Section 2: Loading GPT-2 Model ---")
    try:
        model = load_model("gpt2")
    except Exception as e:
        print(f"Could not load model: {e}")
        print("Ensure transformer_lens is installed: pip install transformer_lens")
        return

    # 3. Cache activations (no transcoder weights needed)
    print("\n--- Section 3: Caching MLP Activations ---")
    prompt = "The quick brown fox jumps over the lazy"
    try:
        activations = cache_activations_example(model, prompt, layer=0)
    except Exception as e:
        print(f"Activation caching failed: {e}")
        return

    # 4. Load transcoder (requires weights from setup.sh)
    print("\n--- Section 4: Loading Transcoder Weights ---")
    # Adjust this path to wherever setup.sh downloads the weights
    weights_path = "./transcoder_weights/gpt2-small_layer0_transcoder.pt"
    try:
        transcoder = load_transcoder(weights_path)

        # 5. Demonstrate feature activations
        print("\n--- Section 5: Feature Activations ---")
        feature_acts, reconstruction = demonstrate_feature_activation(transcoder, activations)

        # 6. Run with replacement context
        print("\n--- Section 6: Inference with Replacement Context ---")
        logits = run_with_replacement_context(model, {0: transcoder}, prompt)
        print("\nTop predicted next tokens:")
        get_top_predicted_tokens(model, logits)

    except FileNotFoundError as e:
        print(f"Transcoder weights not found: {e}")
        print("Skipping transcoder-dependent sections.")
        print("\nRunning baseline model inference instead:")
        tokens = model.to_tokens(prompt)
        with torch.no_grad():
            logits = model(tokens)
        print("Top predicted next tokens (no transcoder):")
        get_top_predicted_tokens(model, logits)

    print("\n" + "=" * 60)
    print("Done. See walkthrough.ipynb for interactive examples.")
    print("=" * 60)


if __name__ == "__main__":
    main()

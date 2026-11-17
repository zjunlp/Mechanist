#!/usr/bin/env python3
"""
Training Example: Train a Transcoder on GPT-2

This script demonstrates how to configure and launch a transcoder
training run using the sae_training library.

Prerequisites:
    bash setup.sh
    OR
    pip install -r requirements.txt

Usage:
    python train_transcoder_example.py

Notes:
    - Transcoders are trained on MLP sublayers of transformer models.
    - This is based on the existing train_transcoder.py in the repo root.
    - Uses the LanguageModelSAERunnerConfig and language_model_sae_runner.
"""

import torch


def build_transcoder_config(
    model_name: str = "gpt2",
    layer: int = 0,
    expansion_factor: int = 4,
    total_training_tokens: int = 1_000_000,
    log_to_wandb: bool = False,
):
    """
    Build a LanguageModelSAERunnerConfig for transcoder training.

    Args:
        model_name: HuggingFace model name
        layer: Which transformer layer to train the transcoder for
        expansion_factor: Ratio of transcoder hidden dim to model d_model
        total_training_tokens: Number of tokens to train on
        log_to_wandb: Whether to log metrics to Weights & Biases

    Returns:
        LanguageModelSAERunnerConfig instance
    """
    from sae_training.config import LanguageModelSAERunnerConfig

    # GPT-2 small has d_model=768; adjust for other models
    d_model_map = {
        "gpt2": 768,
        "gpt2-medium": 1024,
        "gpt2-large": 1280,
        "EleutherAI/pythia-410m": 1024,
    }
    d_in = d_model_map.get(model_name, 768)

    cfg = LanguageModelSAERunnerConfig(
        # --- Model & Hook ---
        model_name=model_name,
        hook_point=f"blocks.{layer}.hook_mlp_out",
        hook_point_layer=layer,
        d_in=d_in,

        # --- Architecture ---
        expansion_factor=expansion_factor,
        # Total hidden features = d_in * expansion_factor

        # --- Training ---
        lr=2e-4,
        adam_beta1=0.9,
        adam_beta2=0.999,
        l1_coefficient=8e-4,
        lr_scheduler_name="constant",
        train_batch_size=4096,
        context_size=128,
        total_training_tokens=total_training_tokens,

        # --- Data ---
        dataset_path="NeelNanda/pile-10k",

        # --- Checkpointing ---
        n_checkpoints=5,
        checkpoint_path="./checkpoints",

        # --- Logging ---
        log_to_wandb=log_to_wandb,
        wandb_project="transcoder_training",
        wandb_entity=None,
        wandb_log_frequency=100,

        # --- Device ---
        device="cuda" if torch.cuda.is_available() else "cpu",
        seed=42,
        dtype="float32",
    )

    return cfg


def run_training(cfg):
    """
    Launch a transcoder training run.

    Args:
        cfg: LanguageModelSAERunnerConfig instance

    Returns:
        Trained SparseAutoencoder (transcoder) object
    """
    from sae_training.train_sae_on_language_model import language_model_sae_runner

    print(f"Starting transcoder training:")
    print(f"  Model: {cfg.model_name}")
    print(f"  Layer: {cfg.hook_point_layer}")
    print(f"  Hook point: {cfg.hook_point}")
    print(f"  d_in: {cfg.d_in}")
    print(f"  d_hidden: {cfg.d_in * cfg.expansion_factor}")
    print(f"  Total tokens: {cfg.total_training_tokens:,}")
    print(f"  Device: {cfg.device}")
    print()

    transcoder = language_model_sae_runner(cfg)
    return transcoder


def evaluate_transcoder(transcoder, model, prompt: str = "The Eiffel Tower is located in"):
    """
    Quick evaluation: check reconstruction quality on a sample prompt.

    Args:
        transcoder: Trained SparseAutoencoder object
        model: HookedTransformer model
        prompt: Sample text to evaluate on

    Returns:
        dict with evaluation metrics
    """
    from transcoder_circuits.replacement_ctx import TranscoderReplacementContext

    layer = transcoder.cfg.hook_point_layer if hasattr(transcoder, 'cfg') else 0
    tokens = model.to_tokens(prompt)

    # Get original MLP activations
    hook_point = f"blocks.{layer}.hook_mlp_out"
    _, cache = model.run_with_cache(tokens, names_filter=hook_point)
    original_acts = cache[hook_point]

    flat_acts = original_acts.reshape(-1, original_acts.shape[-1])
    with torch.no_grad():
        feature_acts, reconstruction, *_ = transcoder(flat_acts)

    mse = ((flat_acts - reconstruction) ** 2).mean().item()
    sparsity = (feature_acts > 0).float().mean().item()
    l0 = (feature_acts > 0).float().sum(dim=-1).mean().item()

    metrics = {
        "reconstruction_mse": mse,
        "feature_sparsity": sparsity,
        "mean_l0": l0,
        "n_features": feature_acts.shape[-1],
    }

    print("Evaluation metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.6f}")

    return metrics


def main():
    """Main training demonstration."""
    print("=" * 60)
    print("Transcoder Training Example")
    print("=" * 60)

    # Build config
    print("\n--- Building Training Config ---")
    cfg = build_transcoder_config(
        model_name="gpt2",
        layer=0,
        expansion_factor=4,
        total_training_tokens=500_000,  # Small run for demo
        log_to_wandb=False,
    )

    print("\nConfig summary:")
    print(f"  Hook: {cfg.hook_point}")
    print(f"  Features: {cfg.d_in * cfg.expansion_factor}")
    print(f"  LR: {cfg.lr}, L1: {cfg.l1_coefficient}")

    # Run training
    print("\n--- Starting Training ---")
    try:
        transcoder = run_training(cfg)
        print("\nTraining complete!")

        # Evaluate
        print("\n--- Evaluating Transcoder ---")
        from transformer_lens import HookedTransformer
        model = HookedTransformer.from_pretrained("gpt2")
        model.eval()
        evaluate_transcoder(transcoder, model)

    except Exception as e:
        print(f"Training failed: {e}")
        print("\nMake sure you have run: bash setup.sh")
        raise


if __name__ == "__main__":
    main()

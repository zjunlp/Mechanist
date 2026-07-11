---
name: transcoder-circuits
description: Use this skill when working with transcoder-based circuit analysis of large language models, including training transcoders, analyzing MLP sublayers, reverse-engineering LLM circuits, and creating feature dashboards for interpretability research.
---

# Transcoder Circuits: Reverse-Engineering LLM Circuits with Transcoders

## When to Use

Activate this skill when:
- Reverse-engineering circuits inside transformer language models (GPT-2, Pythia, etc.)
- Training transcoders to decompose MLP sublayers into sparse linear combinations of features
- Analyzing interpretable features in LLMs using sparse autoencoders or transcoders
- Building feature dashboards or activation visualizations
- Performing mechanistic interpretability research on neural networks
- Comparing SAE vs. transcoder feature interpretability
- Running circuit analysis, replacement contexts, or activation patching

**Keywords:** transcoder, SAE, sparse autoencoder, mechanistic interpretability, LLM circuits, MLP features, GPT-2, Pythia, feature dashboard, circuit analysis, activation patching

## Quick Reference

- **Repository:** https://github.com/jacobdunefsky/transcoder_circuits
- **Transcoder Weights (HuggingFace):** https://huggingface.co/pchlenski/gpt2-transcoders
- **SAELens (upstream SAE code):** https://github.com/jbloomAus/SAELens
- **Walkthrough Notebook:** `walkthrough.ipynb`

## Installation / Setup

### Prerequisites
- Python 3.8+
- CUDA-capable GPU recommended

### Quick Setup (from README)
```bash
bash setup.sh
```

This script installs dependencies and downloads transcoder weights from HuggingFace (`pchlenski/gpt2-transcoders`).

### Manual Installation
```bash
pip install -r requirements.txt
```

### Requirements (from requirements.txt)
Key dependencies include:
- `transformer_lens` — for loading and hooking into transformer models
- `torch` — PyTorch
- `einops`
- `datasets`
- `huggingface_hub`
- `wandb` (optional, for training logging)

## Core Features

- **Transcoder Training:** Train transcoders on LLM MLP sublayers to decompose activations into sparse interpretable features (`sae_training/`)
- **Circuit Analysis:** Reverse-engineer fine-grained feature circuits within a model (`transcoder_circuits/circuit_analysis.py`)
- **Feature Dashboards:** Generate dashboards for exploring transcoder and SAE features (`transcoder_circuits/feature_dashboards.py`)
- **Replacement Context:** Swap MLP sublayers with transcoder reconstructions during inference (`transcoder_circuits/replacement_ctx.py`)
- **Activations Store:** Stream tokens and generate/store activations during training (`sae_training/activations_store.py`)
- **Geometric Median:** Utility for computing geometric median for initialization (`sae_training/geom_median/`)
- **SAE/Transcoder Comparison:** Evaluation notebooks comparing SAEs and transcoders on Pythia-410M

## Usage Examples

### Loading a Transcoder and Running Replacement Context

```python
import torch
from transformer_lens import HookedTransformer
from transcoder_circuits.replacement_ctx import TranscoderReplacementContext

# Load GPT-2 small via TransformerLens
model = HookedTransformer.from_pretrained("gpt2")

# Load transcoder weights (downloaded via setup.sh)
transcoder = torch.load("path/to/transcoder_layer_0.pt")

# Use replacement context to patch MLP with transcoder
with TranscoderReplacementContext(model, {0: transcoder}):
    tokens = model.to_tokens("Hello, world!")
    logits = model(tokens)
```

### Training a Transcoder

```bash
python train_transcoder.py
```

Or programmatically:

```python
from sae_training.config import LanguageModelSAERunnerConfig
from sae_training.train_sae_on_language_model import language_model_sae_runner

cfg = LanguageModelSAERunnerConfig(
    model_name="gpt2",
    hook_point="blocks.0.hook_mlp_out",
    hook_point_layer=0,
    d_in=768,
    expansion_factor=4,
    # ... other config options
)
language_model_sae_runner(cfg)
```

### Circuit Analysis

```python
from transcoder_circuits.circuit_analysis import get_circuit_scores

# Analyze which transcoder features contribute most to a given output
scores = get_circuit_scores(model, transcoders, tokens, metric_fn)
```

### Feature Dashboards

```python
from transcoder_circuits.feature_dashboards import make_feature_dashboard

# Generate a dashboard for a specific transcoder feature
dashboard = make_feature_dashboard(
    transcoder=transcoder,
    model=model,
    feature_idx=42,
    dataset=dataset,
)
```

## Key APIs / Models

### Models Supported
- **GPT-2 small** (primary, weights available at `pchlenski/gpt2-transcoders`)
- **Pythia-410M** (used in sweep/comparison experiments)

### Core Classes

| Class | Module | Description |
|---|---|---|
| `ActivationsStore` | `sae_training/activations_store.py` | Streams tokens and stores LLM activations for training |
| `RunnerConfig` | `sae_training/config.py` | Base config shared across all training runners |
| `LanguageModelSAERunnerConfig` | `sae_training/config.py` | Config for training transcoders/SAEs on a language model |
| `CacheActivationsRunnerConfig` | `sae_training/config.py` | Config for caching LLM activations to disk |
| `SparseAutoencoder` | `sae_training/sparse_autoencoder.py` | The transcoder/SAE model class |

### Key Functions

| Function | Module | Description |
|---|---|---|
| `language_model_sae_runner` | `sae_training/train_sae_on_language_model.py` | Main training entry point |
| `get_circuit_scores` | `transcoder_circuits/circuit_analysis.py` | Compute feature circuit attribution scores |
| `make_feature_dashboard` | `transcoder_circuits/feature_dashboards.py` | Generate feature visualization dashboards |

## Related Tools

Anthropic has open-sourced **circuit-tracer**, a Python library that builds on the (cross-layer) MLP transcoder formulation to extract feature circuits directly from open-weights models such as Gemma-2-2B and Llama-3.2-1B. Given a prompt, it computes the direct effect of every active transcoder feature, transcoder error node, and input token on every other active feature and output logit, and surfaces the resulting attribution graph through a Neuronpedia-hosted frontend. It pairs naturally with the training and feature-analysis primitives in this skill: train or load transcoders here, then plug them into circuit-tracer's `ReplacementModel.from_pretrained` to obtain end-to-end circuits.

- **Announcement:** https://www.anthropic.com/research/open-source-circuit-tracing
- **GitHub:** https://github.com/safety-research/circuit-tracer

## Common Patterns & Best Practices

1. **Start with `walkthrough.ipynb`** — the notebook walks through loading transcoders, replacement context, and circuit analysis step by step.
2. **Use `TranscoderReplacementContext`** as a context manager to ensure the model is properly restored after patching.
3. **Transcoder weights are layer-specific** — load each layer's transcoder separately.
4. **MLP0 features** are particularly important; the "restricted blind case studies" notebook shows how to work without them.
5. **Use `wandb`** for tracking training runs when training new transcoders.
6. **Circuit analysis is iterative** — start by finding the top features, then investigate their upstream inputs recursively.

## Demo Scripts

### `scripts/train_transcoder_example.py`

```python
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
```

### `scripts/transcoder_usage_example.py`

```python
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
```

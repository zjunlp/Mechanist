---
name: crosscoder-learning
description: Use this skill when working with sparse autoencoders (SAEs), crosscoders, dictionary learning on neural network activations, training SAEs/crosscoders from scratch, loading pretrained dictionaries, caching model activations, or comparing model internals across fine-tuned model pairs using the dictionary_learning / crosscoder_learning library.
---

# Dictionary Learning & Crosscoders Skill

## When to Use

Activate this skill when the user needs to:

- Train **Sparse Autoencoders (SAEs)** on neural network activations (MLP outputs, attention outputs, residual streams)
- Train **CrossCoders** to compare activations across two related models (e.g., a base model and its fine-tuned variant)
- Load and use **pretrained dictionaries** (AutoEncoders, CrossCoders, JumpReLU SAEs) from local disk or the Hugging Face Hub
- **Cache activations** from a language model for later offline training
- **Evaluate** dictionaries using MSE loss, L1/L0 sparsity, CE diff, and variance-explained metrics
- Push or pull dictionary weights to/from the **Hugging Face Hub**
- Perform **model diffing** to identify which features change between a base model and a fine-tuned model
- Use `BatchTopKCrossCoder` for batch-level top-k sparsity across model pairs
- Work with the `nnsight` library to hook into language model internals

**Keywords:** sparse autoencoder, SAE, crosscoder, dictionary learning, activation buffer, neural network features, mechanistic interpretability, model diffing, JumpReLU, GatedSAE, TopK SAE, nnsight, Pythia, Gemma, residual stream, MLP output, attention output

---

## Quick Reference

| Resource | URL |
|---|---|
| Repository (fork) | https://github.com/jkminder/dictionary_learning |
| Original Repository | https://github.com/saprmarks/dictionary_learning |
| Anthropic CrossCoder Paper | https://transformer-circuits.pub/drafts/crosscoders/index.html#model-diffing |
| BatchTopKCrossCoder Paper | https://arxiv.org/pdf/2504.02922 |
| nnsight Documentation | https://nnsight.net/ |
| nnsight Walkthrough | https://nnsight.net/notebooks/tutorials/walkthrough/ |
| Pretrained Dictionaries (Pythia) | https://baulab.us/u/smarks/autoencoders/ |
| Pretrained CrossCoder (HF Hub) | Butanium/gemma-2-2b-crosscoder-l13-mu4.1e-02-lr1e-04 |
| Pretrained SAE Downloader Script | `./pretrained_dictionary_downloader.sh` |

---

## Installation / Setup

### Method 1: pip install from GitHub (recommended for crosscoder features)

```bash
pip install git+https://github.com/jkminder/dictionary_learning
```

### Method 2: Clone and install from source

```bash
git clone https://github.com/jkminder/dictionary_learning
cd dictionary_learning
pip install -r requirements.txt
```

### Method 3: Use as a subdirectory (original repo style)

```bash
git clone https://github.com/saprmarks/dictionary_learning
# Then place the cloned directory inside your project directory and import it
```

### Additional Dependencies

The library uses `nnsight` to access and hook into language model activations:

```bash
pip install nnsight
```

For JumpReLU SAE loading from `sae_lens`:

```bash
pip install sae_lens
```

For Hugging Face Hub push/pull:

```bash
pip install huggingface_hub
```

### Downloading Pretrained Pythia-70m-deduped Dictionaries

```bash
./pretrained_dictionary_downloader.sh
```

This downloads ~2.5 GB of dictionaries (MLP outputs, attention outputs, residual streams for all layers of Pythia-70m-deduped, trained on 2B tokens from The Pile). Directory structure after download:


## Demo Scripts

### `scripts/train_and_evaluate_sae.py`

```python
#!/usr/bin/env python3
"""
Train and Evaluate a Sparse Autoencoder (SAE) using dictionary_learning.

This script demonstrates the complete workflow for:
1. Loading a language model with nnsight
2. Creating an ActivationBuffer to stream model activations
3. Training a StandardTrainer SAE using trainSAE
4. Evaluating the trained SAE (MSE, L0, L1, variance explained)
5. Saving to disk and loading back

Requirements:
    pip install git+https://github.com/jkminder/dictionary_learning
    pip install torch nnsight transformers

Usage:
    python train_and_evaluate_sae.py
    python train_and_evaluate_sae.py --model EleutherAI/pythia-70m-deduped --layer 1 --device cuda:0
"""

import argparse
import json
import os
import torch
from typing import Iterator, List

# ─── dictionary_learning imports ────────────────────────────────────────────
from dictionary_learning import ActivationBuffer, AutoEncoder
from dictionary_learning.trainers import StandardTrainer
from dictionary_learning.training import trainSAE
from dictionary_learning.evaluation import evaluate


# ─── nnsight import ─────────────────────────────────────────────────────────
try:
    from nnsight import LanguageModel
except ImportError:
    raise ImportError(
        "nnsight is required. Install it with: pip install nnsight"
    )


def make_toy_data_iterator(num_sentences: int = 500) -> Iterator[str]:
    """
    Create a simple iterator of text strings for demonstration.

    In real training you would replace this with a proper dataset, e.g.:
        from datasets import load_dataset
        dataset = load_dataset("Eleuther/pile", split="train", streaming=True)
        data = (example["text"] for example in dataset)

    Args:
        num_sentences: Number of repeated sentences in the toy dataset.

    Returns:
        An iterator that yields strings.
    """
    sentences = [
        "The quick brown fox jumps over the lazy dog.",
        "Sparse autoencoders learn interpretable features from neural network activations.",
        "Dictionary learning finds a sparse representation of data.",
        "Language models encode semantic information in their hidden states.",
        "Feature decomposition helps us understand what a model has learned.",
        "Mechanistic interpretability studies the internal computations of neural networks.",
        "The residual stream aggregates information across transformer layers.",
        "Attention heads route information between token positions.",
    ]
    # Cycle through sentences to get num_sentences total strings
    data = [sentences[i % len(sentences)] for i in range(num_sentences)]
    return iter(data)


def load_model_and_submodule(
    model_name: str,
    layer: int,
    device: str,
):
    """
    Load a LanguageModel with nnsight and select an MLP submodule.

    Args:
        model_name: HuggingFace model identifier, e.g. "EleutherAI/pythia-70m-deduped".
        layer: Which transformer layer's MLP to use.
        device: PyTorch device string, e.g. "cuda:0" or "cpu".

    Returns:
        Tuple of (model, submodule, activation_dim)
    """
    print(f"Loading model: {model_name} on {device} ...")
    model = LanguageModel(model_name, device_map=device)

    # ── Model-specific submodule selection ──────────────────────────────────
    # Pythia models use gpt_neox.layers[i].mlp  (output dim = 512 for 70m)
    # GPT-2 models use transformer.h[i].mlp
    # Adapt this section for other model families.
    if "pythia" in model_name.lower():
        submodule = model.gpt_neox.layers[layer].mlp
        # Pythia-70m MLP output dim; adjust for larger Pythia variants:
        # pythia-160m: 1024, pythia-410m: 2048, pythia-1b: 4096, etc.
        activation_dim = 512
    elif "gpt2" in model_name.lower():
        submodule = model.transformer.h[layer].mlp
        activation_dim = 3072  # GPT-2 small MLP output
    else:
        # Generic fallback — adjust activation_dim to match your model
        raise ValueError(
            f"Unknown model family for {model_name}. "
            "Please extend load_model_and_submodule() for this model."
        )

    print(f"  Submodule: {type(submodule).__name__} at layer {layer}")
    print(f"  Activation dim: {activation_dim}")
    return model, submodule, activation_dim


def build_activation_buffer(
    model,
    submodule,
    activation_dim: int,
    device: str,
    n_ctxs: int = 3000,
    ctx_len: int = 128,
    batch_size: int = 64,
    num_sentences: int = 500,
) -> ActivationBuffer:
    """
    Construct an ActivationBuffer that streams activations from the given submodule.

    The buffer internally processes text through the model, captures the
    submodule's output activations, and yields them in batches.  When the
    buffer is half-depleted it automatically refreshes with new text.

    Args:
        model: nnsight LanguageModel instance.
        submodule: The model submodule whose outputs to capture.
        activation_dim: Output dimension of the submodule.
        device: Torch device string.
        n_ctxs: Number of contexts (sequences) to buffer at once.
                Higher = more memory but more diverse batches.
        ctx_len: Maximum sequence length per context.
        batch_size: Number of activation vectors per yielded batch.
        num_sentences: How many toy sentences to generate (demo only).

    Returns:
        An initialised ActivationBuffer ready to yield activation batches.
    """
    data = make_toy_data_iterator(num_sentences=num_sentences)

    buffer = ActivationBuffer(
        data=data,
        model=model,
        submodule=submodule,
        d_submodule=activation_dim,
        n_ctxs=n_ctxs,
        ctx_len=ctx_len,
        out_batch_size=batch_size,
        device=device,
    )

    print(
        f"ActivationBuffer created: n_ctxs={n_ctxs}, ctx_len={ctx_len}, "
        f"batch_size={batch_size}"
    )
    return buffer


def train_standard_sae(
    buffer: ActivationBuffer,
    activation_dim: int,
    expansion_factor: int = 8,
    lr: float = 1e-3,
    device: str = "cpu",
    steps: int = 1000,
    warmup_steps: int = 100,
    resample_steps: int = 500,
    save_dir: str = "./trained_sae",
) -> AutoEncoder:
    """
    Train a StandardTrainer SAE on activations from the buffer.

    Args:
        buffer: ActivationBuffer yielding activation batches.
        activation_dim: Input/output dimension of the SAE (= submodule output dim).
        expansion_factor: Dictionary size = activation_dim * expansion_factor.
        lr: Learning rate for ConstrainedAdam optimizer.
        device: Torch device string.
        steps: Total number of training gradient steps.
        warmup_steps: Number of linear LR warmup steps.
        resample_steps: Dead neuron resampling interval (0 to disable).
        save_dir: Directory to save the trained SAE.

    Returns:
        The trained AutoEncoder instance.
    """
    dictionary_size = expansion_factor * activation_dim
    print(
        f"\nTraining SAE: activation_dim={activation_dim}, "
        f"dictionary_size={dictionary_size}, lr={lr}, steps={steps}"
    )

    trainer_cfg = {
        "trainer": StandardTrainer,
        "dict_class": AutoEncoder,
        "activation_dim": activation_dim,
        "dict_size": dictionary_size,
        "lr": lr,
        "device": device,
        # l1_penalty controls sparsity; tune this for your use case
        "l1_penalty": 1e-3,
    }

    os.makedirs(save_dir, exist_ok=True)

    ae = trainSAE(
        data=buffer,
        trainer_configs=[trainer_cfg],
        steps=steps,
        warmup_steps=warmup_steps,
        resample_steps=resample_steps if resample_steps > 0 else None,
        save_dir=save_dir,
        log_steps=100,   # print loss every 100 steps
    )

    print(f"\nTraining complete. SAE saved to: {save_dir}")
    return ae


def evaluate_sae(
    ae: AutoEncoder,
    activation_dim: int,
    n_samples: int = 4096,
    device: str = "cpu",
) -> dict:
    """
    Evaluate a trained SAE on random activations (demo) or real activations.

    Reports:
        - MSE loss (average squared reconstruction error)
        - L1 sparsity (sum of absolute feature activations)
        - L0 sparsity (average number of active features per sample)
        - Fraction of alive dictionary features

    In real usage you would pass actual model activations as a tensor or
    DataLoader, not random tensors.

    Args:
        ae: Trained AutoEncoder instance.
        activation_dim: Dimension of activations.
        n_samples: Number of random samples to evaluate on.
        device: Torch device string.

    Returns:
        Dictionary of metric_name -> value.
    """
    ae.eval()
    ae = ae.to(device)

    # ── For demonstration we use random activations ──────────────────────────
    # Replace with: activations = next(iter(your_buffer))  for real evaluation
    print(f"\nEvaluating SAE on {n_samples} random activation samples ...")
    activations = torch.randn(n_samples, activation_dim, device=device)

    with torch.no_grad():
        reconstruction, features = ae(activations, output_features=True)

    mse = torch.nn.functional.mse_loss(reconstruction, activations).item()
    variance = activations.var().item()
    variance_explained = max(0.0, 1.0 - mse / variance) * 100.0
    l1 = features.abs().mean().item()
    l0 = (features > 1e-6).float().sum(dim=-1).mean().item()

    # Fraction of alive features (active on at least one sample)
    alive_features = (features > 1e-6).any(dim=0).float().mean().item()

    metrics = {
        "mse_loss": mse,
        "variance_explained_pct": variance_explained,
        "mean_l1_sparsity": l1,
        "mean_l0_sparsity": l0,
        "fraction_alive_features": alive_features,
        "dictionary_size": features.shape[-1],
        "activation_dim": activation_dim,
    }

    print("\n=== SAE Evaluation Metrics ===")
    for k, v in metrics.
```

### `scripts/train_sae_demo.py`

```python
#!/usr/bin/env python3
"""
Train a Sparse Autoencoder (SAE) on Language Model Activations

This script demonstrates how to use the dictionary_learning library to:
1. Load a language model via nnsight
2. Create an ActivationBuffer to stream activations from MLP layers
3. Train a standard sparse autoencoder (SAE) using StandardTrainer
4. Evaluate the trained SAE on held-out activations
5. Save the trained dictionary to disk and push to Hugging Face Hub

Requirements:
    pip install git+https://github.com/jkminder/dictionary_learning
    pip install nnsight torch datasets

Usage:
    python train_sae_demo.py
"""

import torch
from typing import Iterator

from nnsight import LanguageModel
from dictionary_learning import ActivationBuffer, AutoEncoder
from dictionary_learning.trainers import StandardTrainer
from dictionary_learning.training import trainSAE
from dictionary_learning.evaluation import evaluate


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "EleutherAI/pythia-70m-deduped"  # Any HuggingFace causal LM works here
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
LAYER_INDEX = 1                  # Which transformer layer's MLP to train the SAE on
ACTIVATION_DIM = 512             # Output dimension of Pythia-70m MLP layers
DICT_SIZE = 16 * ACTIVATION_DIM  # 8192 — 16x expansion ratio is common
LEARNING_RATE = 1e-3
L1_PENALTY = 8e-4                # Sparsity regularization coefficient
N_CTXS = int(3e4)                # ActivationBuffer capacity (contexts held in memory)
BATCH_SIZE = 2048                # Activation batch size for training
SAVE_PATH = "./trained_sae"      # Local directory to save the trained dictionary


# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------

def get_training_data() -> Iterator[str]:
    """
    Return an iterator of strings for SAE training.

    In production, replace this with a large text corpus such as The Pile,
    OpenWebText, or a domain-specific dataset. Here we use a small hardcoded
    list to keep the demo self-contained and runnable without network access.

    Returns:
        Iterator[str]: An iterator that yields text strings.
    """
    # Replace this list with:
    #   from datasets import load_dataset
    #   data = load_dataset("EleutherAI/pile", split="train", streaming=True)
    #   return (item["text"] for item in data)
    sample_texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Sparse autoencoders decompose neural network activations into interpretable features.",
        "Dictionary learning finds a sparse representation of data in an overcomplete basis.",
        "The residual stream in a transformer carries information between layers.",
        "Mechanistic interpretability aims to reverse-engineer neural networks.",
        "Features learned by sparse autoencoders often correspond to human-interpretable concepts.",
        "The encoder maps activations to a sparse feature vector.",
        "The decoder reconstructs the original activation from the sparse features.",
        "Dead neurons are dictionary features that never activate on any input.",
        "Neuron resampling periodically reinitializes dead neurons during training.",
    ] * 500  # Repeat to simulate a larger dataset for demonstration
    return iter(sample_texts)


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------

def build_activation_buffer(model: LanguageModel, device: str) -> ActivationBuffer:
    """
    Construct an ActivationBuffer for MLP output activations at a given layer.

    The ActivationBuffer wraps an nnsight LanguageModel, hooks into a specific
    submodule (here: the MLP of layer LAYER_INDEX), and maintains a rolling
    buffer of activations sampled from the provided text data.

    Args:
        model: An nnsight LanguageModel instance.
        device: Target device string (e.g., "cuda:0" or "cpu").

    Returns:
        ActivationBuffer: Configured and ready to yield activation batches.
    """
    # Access the MLP submodule in Pythia-70m.
    # For other model architectures, adjust the attribute path accordingly:
    #   GPT-2:     model.transformer.h[layer].mlp
    #   LLaMA:     model.model.layers[layer].mlp
    #   Mistral:   model.model.layers[layer].mlp
    submodule = model.gpt_neox.layers[LAYER_INDEX].mlp

    data = get_training_data()

    buffer = ActivationBuffer(
        data=data,
        model=model,
        submodule=submodule,
        d_submodule=ACTIVATION_DIM,  # Output dimension of the MLP
        n_ctxs=N_CTXS,              # How many contexts to keep in the buffer
        device=device,
    )
    print(f"[ActivationBuffer] Created buffer for layer {LAYER_INDEX} MLP "
          f"(activation_dim={ACTIVATION_DIM}, n_ctxs={N_CTXS})")
    return buffer


def build_trainer_config(device: str) -> dict:
    """
    Build the trainer configuration dictionary for a StandardTrainer + AutoEncoder.

    The config dict is passed as one element of the trainer_configs list to
    trainSAE(). Multiple configs can be passed to sweep hyperparameters.

    Args:
        device: Target device string.

    Returns:
        dict: Trainer configuration dictionary.
    """
    return {
        "trainer": StandardTrainer,
        "dict_class": AutoEncoder,
        "activation_dim": ACTIVATION_DIM,
        "dict_size": DICT_SIZE,
        "lr": LEARNING_RATE,
        "l1_penalty": L1_PENALTY,
        "device": device,
        # Optional: warmup_steps=1000 for linear LR warmup
        # Optional: resample_steps=25000 to resample dead neurons periodically
    }


def train_sae(model: LanguageModel, device: str) -> AutoEncoder:
    """
    Train a sparse autoencoder on MLP activations from the language model.

    This function:
      1. Creates an ActivationBuffer that streams MLP activations.
      2. Calls trainSAE() with a StandardTrainer configuration.
      3. Returns the trained AutoEncoder.

    Args:
        model: An nnsight LanguageModel instance.
        device: Target device string.

    Returns:
        AutoEncoder: The trained sparse autoencoder.
    """
    buffer = build_activation_buffer(model, device)
    trainer_cfg = build_trainer_config(device)

    print(f"\n[Training] Starting SAE training...")
    print(f"  Model:          {MODEL_NAME}")
    print(f"  Layer:          {LAYER_INDEX} MLP")
    print(f"  Activation dim: {ACTIVATION_DIM}")
    print(f"  Dict size:      {DICT_SIZE} ({DICT_SIZE // ACTIVATION_DIM}x expansion)")
    print(f"  Learning rate:  {LEARNING_RATE}")
    print(f"  L1 penalty:     {L1_PENALTY}")
    print(f"  Device:         {device}\n")

    ae = trainSAE(
        data=buffer,
        trainer_configs=[trainer_cfg],
    )
    print("\n[Training] Training complete.")
    return ae


def evaluate_sae(ae: AutoEncoder, device: str) -> None:
    """
    Evaluate a trained AutoEncoder on random held-out activations.

    Reports MSE loss, L1 sparsity, L0 sparsity, and fraction of live neurons.

    Args:
        ae: A trained AutoEncoder instance.
        device: Target device string.
    """
    print("\n[Evaluation] Evaluating SAE on random activations...")
    # In production, use real held-out activations from the model.
    # Here we use random tensors as a placeholder to demonstrate the API.
    held_out_activations = torch.randn(1024, ACTIVATION_DIM).to(device)

    # Encode and decode
    with torch.no_grad():
        features = ae.encode(held_out_activations)                     # (1024, dict_size)
        reconstruction = ae.decode(features)                           # (1024, act_dim)
        reconstruction_v2, features_v2 = ae(
            held_out_activations, output_features=True
        )

    mse = torch.nn.functional.mse_loss(reconstruction, held_out_activations)
    l1 = features.abs().mean()
    l0 = (features > 1e-4).float().mean(dim=-1).mean()
    pct_alive = (features.abs().sum(dim=0) > 0).float().mean()

    print(f"  MSE loss:           {mse.item():.4f}")
    print(f"  L1 sparsity (mean): {l1.item():.4f}")
    print(f"  L0 sparsity (mean): {l0.item():.2f} features/activation")
    print(f"  Fraction alive:     {pct_alive.item() * 100:.1f}%")

    # Verify both forward call styles give the same result
    assert torch.allclose(reconstruction, reconstruction_v2, atol=1e-5), \
        "Mismatch between ae.decode(ae.encode(x)) and ae(x)"
    assert torch.allclose(features, features_v2, atol=1e-5), \
        "Mismatch in features between two forward call styles"
    print("  [OK] Both forward call styles are consistent.")


def save_sae(ae: AutoEncoder, save_path: str) -> None:
    """
    Save the trained AutoEncoder weights to a local directory.

    The saved directory contains:
      - ae.pt:       The state_dict of the fully trained dictionary.
      - config.json: Hyperparameters used to train the dictionary.

    Args:
        ae: A trained AutoEncoder instance.
        save_path: Local directory path to save the dictionary.
    """
    import os
    os.makedirs(save_path, exist_ok=True)
    ae.save(save_path)
    print(f"\n[Save] Dictionary saved to: {save_path}")


def demo_load_and_use_pretrained() -> None:
    """
    Demonstrate loading a pretrained AutoEncoder from a local path or HF Hub
    and performing encode / decode operations.

    This function shows the recommended API for inference with a pretrained SAE.
    """
    print("\n[Demo] Loading pretrained AutoEncoder from local path...")
    # Replace with your actual path to a pretrained dictionary
    # e.g., "dictionaries/pythia-70m-deduped/ml
```

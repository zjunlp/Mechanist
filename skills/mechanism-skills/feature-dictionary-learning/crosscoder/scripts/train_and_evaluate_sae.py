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
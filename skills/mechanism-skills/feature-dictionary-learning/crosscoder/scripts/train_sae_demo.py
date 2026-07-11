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
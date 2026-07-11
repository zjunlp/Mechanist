#!/usr/bin/env python3
"""
Verify the Deep Neural Feature Ansatz (DNFA)

This script demonstrates how to:
1. Load a pre-trained fully connected network and its initialization.
2. Extract intermediate layer representations (features) from both.
3. Compute feature kernel matrices (K = Phi @ Phi.T) at each layer.
4. Compare trained vs. initialization kernels to verify the DNFA.

The Deep Neural Feature Ansatz states that the features learned by a trained
network (Phi_trained) match those predicted by the kernel regime initialized
at the TRAINED network's parameters — empirically verifiable by comparing
the layer-wise kernel matrices.

Reference: https://arxiv.org/abs/2212.13881

Requires:
    - PyTorch 1.13
    - functorch (pip install functorch)
    - A pre-trained network saved by train_network.py (saved_nns/ directory)

Usage:
    # First run train_network.py to generate checkpoints, then:
    python verify_ansatz.py
"""

import os
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
import torchvision
import torchvision.transforms as transforms
import numpy as np

# Optional: import functorch for NTK computation
# functorch is required for the full NTK verification in the paper.
# If not installed, this script falls back to feature-kernel only comparison.
try:
    import functorch
    HAS_FUNCTORCH = True
    print("functorch available — NTK computation enabled.")
except ImportError:
    HAS_FUNCTORCH = False
    print("functorch not found — falling back to feature kernel comparison only.")


# ---------------------------------------------------------------------------
# Re-use Net / Nonlinearity from train_network.py
# In practice: from neural_model import Net, Nonlinearity
# ---------------------------------------------------------------------------

class Nonlinearity(nn.Module):
    """Activation function wrapper. Mirrors neural_model.Nonlinearity."""

    def __init__(self, activation: str = "relu"):
        super().__init__()
        activations = {"relu": nn.ReLU(), "gelu": nn.GELU(), "tanh": nn.Tanh()}
        if activation not in activations:
            raise ValueError(f"Unknown activation '{activation}'")
        self.activation = activations[activation]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(x)


class Net(nn.Module):
    """
    Fully connected MLP. Mirrors neural_model.Net.

    Stores intermediate activations in self.activations during forward pass
    for layer-wise feature extraction.
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        width: int = 512,
        depth: int = 4,
        activation: str = "relu",
    ):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.width = width
        self.depth = depth
        self.activations: list = []  # Populated during forward()

        self.layers = nn.ModuleList()
        self.nonlinearities = nn.ModuleList()

        # Input → first hidden
        self.layers.append(nn.Linear(input_dim, width))
        self.nonlinearities.append(Nonlinearity(activation))

        # Hidden → hidden
        for _ in range(depth - 1):
            self.layers.append(nn.Linear(width, width))
            self.nonlinearities.append(Nonlinearity(activation
---
name: deep-neural-feature-ansatz
description: Use this skill when working with the Deep Neural Feature Ansatz (DNFA) — verifying feature learning in neural networks, training fully connected networks on image/tabular datasets, computing Neural Tangent Kernels (NTK) and Neural Network Gaussian Processes (NNGP), or reproducing experiments from the paper "The Deep Neural Feature Ansatz" (arXiv:2212.13881).
---

# Deep Neural Feature Ansatz

## When to Use

Activate this skill when you need to:

- **Train fully connected neural networks** on standard datasets (CIFAR-10, CIFAR-100, SVHN, MNIST, FashionMNIST) with configurable depth, width, learning rate, and optimizer.
- **Verify the Deep Neural Feature Ansatz**: empirically check that the features learned by trained neural networks match those predicted by the kernel regime (NTK/NNGP).
- **Compute kernel matrices** derived from intermediate representations of neural networks (NTK, NNGP, or feature-based kernels at each layer).
- **Reproduce experiments** from the paper "The Deep Neural Feature Ansatz" (https://arxiv.org/abs/2212.13881).
- **Study feature learning dynamics** in deep networks by comparing trained network representations to their linearized counterparts at initialization.
- **Work with functorch** for per-sample gradient computation and Jacobian-based kernel evaluations in PyTorch.

**Keywords that trigger this skill:** deep neural feature ansatz, DNFA, NTK, NNGP, neural tangent kernel, feature learning, fully connected networks, kernel regime, functorch, neural network verification, representation similarity.

---

## Quick Reference

- **Paper:** https://arxiv.org/abs/2212.13881
- **Repository:** https://github.com/aradha/deep_neural_feature_ansatz
- **Primary framework:** PyTorch 1.13 + functorch (pip)
- **Environment file:** `deep_nfa_env.yml` (included in repo)
- **Entrypoints:**
  - `main.py` — Train neural networks and save checkpoints
  - `verify_deep_NFA.py` — Load saved networks and verify the ansatz

---

## Installation / Setup

### Prerequisites

- Python 3.8+ (conda environment recommended)
- CUDA-capable GPU recommended for large networks
- PyTorch 1.13

### Step 1: Create and activate the conda environment from the provided YAML

```bash
conda env create -f deep_nfa_env.yml
conda activate deep_nfa_env
```

### Step 2: Install functorch via pip (required, not in conda defaults)

```bash
pip install functorch
```

### Step 3: Verify the installation

```bash
python -c "import torch; import functorch; print(torch.__version__)"
```

### Step 4: Create the directory for saving neural networks

The training script expects a directory named `saved_nns` in the working directory:

```bash
mkdir -p saved_nns
```

### Environment Summary (`deep_nfa_env.yml`)

Key dependencies specified in the environment file:
- `pytorch==1.13`
- `torchvision` (for dataset loading)
- `functorch` (via pip, for per-sample gradients and Jacobians)
- `numpy`
- `scipy`
- Standard scientific Python stack

---

## Core Features

- **Fully Connected Network Training (`main.py`)**
  Configure and train MLP networks with variable depth and width. Saves both the trained network and its initialization state to `saved_nns/` for later analysis.

- **Ansatz Verification (`verify_deep_NFA.py`)**
  Load a pre-trained network and its initialization, compute layer-wise kernel matrices (NTK, NNGP, and feature kernels), and compare them to validate the Deep Neural Feature Ansatz.

- **Dataset Utilities (`dataset.py`)**
  Helpers for loading and preprocessing CIFAR-10, CIFAR-100, SVHN, MNIST, and FashionMNIST. Includes one-hot encoding, train/val splitting, and subsampling.

- **Flexible Optimizer Selection (`trainer.py`)**
  Supports SGD and Adam optimizers with configurable learning rates. Provides a full training loop with validation and test evaluation.

- **Custom Nonlinearity Support (`neural_model.py`)**
  `Nonlinearity` class wraps activation functions (ReLU, GELU, etc.). The `Net` class builds arbitrarily deep fully connected networks with a configurable nonlinearity.

- **Kernel Computation via functorch**
  Uses `functorch.vmap` and `functorch.jacrev`/`functorch.grad` to efficiently compute NTK and NNGP kernel matrices over batches of data without explicit for-loops.

- **Named Checkpoint System**
  `get_name()` generates structured filenames encoding dataset, depth, width, learning rate, optimizer, and epoch, ensuring reproducible experiment tracking.

---

## Usage Examples

### Training a Neural Network

```bash
python main.py
```

Inside `main.py`, configure the experiment by editing the `configs` dictionary and calling `main()`. The network and its initialization are saved to `saved_nns/<name>.pt` and `saved_nns/<name>_init.pt`.

### Verifying the Deep Neural Feature Ansatz

```bash
python verify_deep_NFA.py
```

This script:
1. Loads a saved trained network from `saved_nns/`
2. Loads the corresponding initialization checkpoint
3. Computes NTK/NNGP/feature kernels at each layer for both trained and init networks
4. Prints or saves comparison metrics verifying the ansatz

### Example: Loading a Network and Computing Kernels (from `verify_deep_NFA.py` patterns)

```python
# Load a trained network
net = load_nn(path="saved_nns/my_experiment.pt", width=512, depth=4)

# Load the network at initialization
net_init = load_init_nn(path="saved_nns/my_experiment_init.pt", width=512, depth=4)

# Run ansatz verification
verify_ansatz(net, net_init, data_loader)
```

### Example: Dataset Loading (from `dataset.py` patterns)

```python
from dataset import get_svhn, one_hot_data, split

# Load SVHN with 80/20 train/val split, 10000 train, 2000 test
train_loader, val_loader, test_loader = get_svhn(
    split_percentage=0.8,
    num_train=10000,
    num_test=2000
)
```

### Example: Configuring and Training a Network

```python
# Typical configs dictionary used in main.py
configs = {
    "dataset": "cifar10",
    "depth": 4,
    "width": 512,
    "lr": 0.01,
    "optimizer": "sgd",
    "epochs": 200,
    "batch_size": 128,
}
```

---

## Key APIs / Models

### Classes

| Class | File | Description |
|---|---|---|
| `Net` | `neural_model.py` | Fully connected network with configurable depth, width, and nonlinearity |
| `Nonlinearity` | `neural_model.py` | Wrapper module for activation functions used inside `Net` |

### Core Functions

| Function | File | Description |
|---|---|---|
| `main()` | `main.py` | Top-level training entry point; reads configs and runs the full training pipeline |
| `get_name(dataset_name, configs)` | `main.py` / `verify_deep_NFA.py` | Generates a deterministic checkpoint filename from experiment config |
| `train_network(train_loader, val_loader, test_loader)` | `trainer.py` | Full training loop with validation; returns trained model |
| `train_step(net, optimizer, train_loader)` | `trainer.py` | Single epoch training step |
| `select_optimizer(name, lr, net)` | `trainer.py` | Factory for SGD or Adam optimizer |
| `load_nn(path, width, depth)` | `verify_deep_NFA.py` | Load a trained `Net` from a `.pt` checkpoint |
| `load_init_nn(path, width, depth)` | `verify_deep_NFA.py` | Load the initialization-state `Net` from a `.pt` checkpoint |
| `one_hot_data(dataset, num_classes, num_samples)` | `dataset.py` | Convert a dataset's labels to one-hot encoding and subsample |
| `split(trainset, p)` | `dataset.py` | Split a dataset into train and validation subsets by proportion `p` |
| `get_svhn(split_percentage, num_train, num_test)` | `dataset.py` | Load SVHN dataset with train/val/test DataLoaders |

### Supported Datasets

- `cifar10` — CIFAR-10 (10-class image classification)
- `cifar100` — CIFAR-100 (100-class image classification)
- `svhn` — Street View House Numbers
- `mnist` — MNIST handwritten digits
- `fashionmnist` — FashionMNIST clothing items

### Supported Optimizers

- `sgd` — Stochastic Gradient Descent (via `torch.optim.SGD`)
- `adam` — Adam (via `torch.optim.Adam`)

### Key Dependencies

- `torch` 1.13 — Core deep learning framework
- `functorch` — Per-sample gradient and Jacobian computation (NTK/NNGP kernels)
- `torchvision` — Dataset loading and transforms
- `numpy` — Numerical operations on kernel matrices

---

## Common Patterns & Best Practices

### 1. Always save both the trained network and its initialization
The ansatz verification requires comparing the trained network against its own initialization. `main.py` saves `<name>.pt` (trained) and `<name>_init.pt` (at initialization) automatically.

### 2. Use consistent `configs` dictionaries
Both `main.py` and `verify_deep_NFA.py` use `get_name(dataset_name, configs)` to derive filenames. Use identical configs dicts when training and verifying to ensure paths match.

### 3. GPU acceleration
Place networks on CUDA device before training:
```python
net = net.to("cuda" if torch.cuda.is_available() else "cpu")
```

### 4. functorch compatibility
`functorch` must be installed via pip even when using a conda environment. It wraps PyTorch modules — ensure the module is in `eval()` mode and parameters are not in `no_grad` context when computing Jacobians for the NTK.

### 5. Batch size for kernel computation
Kernel computation in `verify_deep_NFA.py` can be memory-intensive. Use small subsets (e.g., 500–1000 samples) for kernel matrix evaluation to avoid OOM errors.

### 6. Reproducibility
Set seeds before training:
```python
import torch, numpy as np, random
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)
```

### 7. Environment activation
Always work inside the `deep_nfa_env` conda environment to ensure PyTorch 1.13 and compatible functorch versions are used. Newer PyTorch versions have integrated functorch but may have API differences.

## Demo Scripts

### `scripts/train_network.py`

```python
#!/usr/bin/env python3
"""
Train a Fully Connected Network with Deep Neural Feature Ansatz (DNFA) Codebase

This script demonstrates how to use the deep_neural_feature_ansatz repository
to train a configurable fully connected network on standard image classification
datasets and save both the trained model and its initialization for later
ansatz verification.

Requires:
    - PyTorch 1.13
    - functorch (pip install functorch)
    - torchvision

Usage:
    python train_network.py

    # Adjust CONFIGS at the bottom of this file to change dataset / architecture.
"""

import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import torchvision
import torchvision.transforms as transforms


# ---------------------------------------------------------------------------
# NOTE: These functions mirror the actual implementations in the repository.
#       In practice, import directly from the repo modules:
#
#       sys.path.insert(0, "/path/to/deep_neural_feature_ansatz")
#       from neural_model import Net, Nonlinearity
#       from trainer import train_network, select_optimizer
#       from dataset import get_svhn, one_hot_data, split
# ---------------------------------------------------------------------------


# ── neural_model.py equivalents ─────────────────────────────────────────────

class Nonlinearity(nn.Module):
    """
    Wrapper module for activation functions used inside Net.

    Args:
        activation (str): Name of the activation. One of 'relu', 'gelu', 'tanh'.
    """

    ACTIVATIONS = {
        "relu": nn.ReLU(),
        "gelu": nn.GELU(),
        "tanh": nn.Tanh(),
    }

    def __init__(self, activation: str = "relu"):
        super().__init__()
        if activation not in self.ACTIVATIONS:
            raise ValueError(f"Unsupported activation '{activation}'. "
                             f"Choose from {list(self.ACTIVATIONS.keys())}")
        self.activation = self.ACTIVATIONS[activation]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(x)


class Net(nn.Module):
    """
    Fully connected network with configurable depth, width, and nonlinearity.

    This mirrors the Net class in neural_model.py of the repository.

    Args:
        input_dim (int): Flattened input feature dimension.
        output_dim (int): Number of output classes.
        width (int): Hidden layer width (number of neurons per hidden layer).
        depth (int): Number of hidden layers.
        activation (str): Activation function name ('relu', 'gelu', 'tanh').
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

        layers = []
        # Input layer
        layers.append(nn.Linear(input_dim, width))
        layers.append(Nonlinearity(activation))
        # Hidden layers
        for _ in range(depth - 1):
            layers.append(nn.Linear(width, width))
            layers.append(Nonlinearity(activation))
        # Output layer (no activation)
        layers.append(nn.Linear(width, output_dim))

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass — flattens input before passing through MLP."""
        x = x.view(x.size(0), -1)  # Flatten spatial dims
        return self.network(x)


# ── trainer.py equivalents ───────────────────────────────────────────────────

def select_optimizer(name: str, lr: float, net: nn.Module) -> optim.Optimizer:
    """
    Factory for selecting an optimizer by name.

    Mirrors select_optimizer() in trainer.py.

    Args:
        name (str): Optimizer name. One of 'sgd', 'adam'.
        lr (float): Learning rate.
        net (nn.Module): The network whose parameters will be optimized.

    Returns:
        torch.optim.Optimizer: Configured optimizer instance.

    Raises:
        ValueError: If an unsupported optimizer name is provided.
    """
    name = name.lower()
    if name == "sgd":
        return optim.SGD(net.parameters(), lr=lr, momentum=0.9, weight_decay=5e-4)
    elif name == "adam":
        return optim.Adam(net.parameters(), lr=lr, weight_decay=1e-4)
    else:
        raise ValueError(f"Unknown optimizer '{name}'. Choose 'sgd' or 'adam'.")


def train_step(
    net: nn.Module,
    optimizer: optim.Optimizer,
    train_loader: DataLoader,
    device: torch.device,
) -> float:
    """
    Execute a single training epoch.

    Mirrors train_step() in trainer.py.

    Args:
        net (nn.Module): The neural network to train.
        optimizer (torch.optim.Optimizer): Configured optimizer.
        train_loader (DataLoader): DataLoader for the training set.
        device (torch.device): Device to run computation on.

    Returns:
        float: Mean cross-entropy loss over the epoch.
    """
    net.train()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    num_batches = 0

    for inputs, targets in train_loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        num_batches += 1

    return total_loss / max(num_batches, 1)


def evaluate(
    net: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> float:
    """
    Evaluate the network on a given DataLoader.

    Args:
        net (nn.Module): Network to evaluate.
        loader (DataLoader): DataLoader for the evaluation set.
        device (torch.device): Computation device.

    Returns:
        float: Classification accuracy in [0, 1].
    """
    net.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            _, predicted = outputs.max(1)
            correct += predicted.eq(targets).sum().item()
            total += targets.size(0)
    return correct / max(total, 1)


def train_network(
    net: nn.Module,
    optimizer: optim.Optimizer,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    epochs: int,
    device: torch.device,
) -> nn.Module:
    """
    Full training loop with per-epoch validation reporting.

    Mirrors train_network() in trainer.py.

    Args:
        net (nn.Module): Network to train.
        optimizer (torch.optim.Optimizer): Optimizer.
        train_loader (DataLoader): Training DataLoader.
        val_loader (DataLoader): Validation DataLoader.
        test_loader (DataLoader): Test DataLoader.
        epochs (int): Number of training epochs.
        device (torch.device): Computation device.

    Returns:
        nn.Module: Trained network.
    """
    net = net.to(device)
    for epoch in range(1, epochs + 1):
        loss = train_step(net, optimizer, train_loader, device)
        if epoch % 10 == 0 or epoch == 1:
            val_acc = evaluate(net, val_loader, device)
            test_acc = evaluate(net, test_loader, device)
            print(
                f"Epoch {epoch:4d}/{epochs} | "
                f"Loss: {loss:.4f} | "
                f"Val Acc: {val_acc*100:.2f}% | "
                f"Test Acc: {test_acc*100:.2f}%"
            )
    return net


# ── dataset.py equivalents ───────────────────────────────────────────────────

def get_cifar10(
    split_percentage: float = 0.9,
    num_train: int = 10000,
    num_test: int = 2000,
    batch_size: int = 128,
):
    """
    Load CIFAR-10 with a train/val split and optional subsampling.

    Mirrors the dataset loading pattern in dataset.py.

    Args:
        split_percentage (float): Fraction of training data used for training
            vs validation (e.g., 0.9 → 90% train, 10% val).
        num_train (int): Number of training samples to use (subsampled).
        num_test (int): Number of test samples to use (subsampled).
        batch_size (int): DataLoader batch size.

    Returns:
        Tuple[DataLoader, DataLoader, DataLoader]: train, val, test loaders.
    """
    transform_train = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465),
                             (0.2023, 0.1994, 0.2010)),
    ])
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465),
                             (0.2023, 0.1994, 0.2010)),
    ])

    # Download to ./data (standard torchvision cache location)
    full_train = torchvision.datasets.CIFAR10(
        root="./data", train=True, download=True, transform=transform_train
    )
    full_test = torchvision.datasets.CIFAR10(
        root="./data", train=False, download=True, transform=transform_test
    )

    # Subsample training set
    num_train = min(num_train, len(full_train))
    train_indices = torch.randperm(len(full_train))[:num_train]
    train_subset = torch.utils.data.Subset(full_train, train_indices)

    # Train / val split
    n_val = int(num_train * (1.0 - split_percentage))
    n_tr = num_train - n_val
    train_set, val_set = random_split(
        train_subset, [n_tr, n_val],
        generator=torch.Generator().manual_seed(42)
    )

    # Subsample test set
    num_test = min(num_test, len(full_test))
    test_indices = torch.randperm(len(full_test))[:num_test]
    test_set = torch.utils.data.Subset(full_test, test_indices)

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True,
                              num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False,
                            num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False,
                             num_workers=2, pin_memory=True)

    print(f"CIFAR-10 | Train: {len(train_set)} | Val: {len(val_set)} | Test: {len(test_set)}")
    return train_loader, val_loader, test_loader


# ── main.py equivalent ───────────────────────────────────────────────────────

def get_name(dataset_name: str, configs: dict) -> str:
    """
    Generate a deterministic checkpoint filename encoding experiment config.

    Mirrors get_name() in main.py and verify_deep_NFA.py.

    Args:
        dataset_name (str): Dataset identifier (e.g., 'cifar10').
        configs (dict): Experiment configuration dictionary with keys:
            depth, width, lr, optimizer, epochs.

    Returns:
        str: Filename stem (without extension) for saving checkpoints.
    """
    return (
        f"{dataset_name}"
        f"_depth{configs['depth']}"
        f"_width{configs['width']}"
        f"_lr{configs['lr']}"
        f"_{configs['optimizer']}"
        f"_epochs{configs['epochs']}"
    )


def main():
    """
    Top-level training entry point.

    Trains a fully connected network on CIFAR-10 and saves:
      - saved_nns/<name>.pt          — trained model state dict
      - saved_nns/<name>_init.pt     — model state dict at initialization

    Both files are required by verify_deep_NFA.py to verify the ansatz.
    """
    # ── Experiment configuration ──────────────────────────────────────────
    configs = {
        "dataset": "cifar10",
        "depth": 4,           # Number of hidden layers
        "width": 512,         # Neurons per hidden layer
        "lr": 0.01,           # Learning rate
        "optimizer": "sgd",   # 'sgd' or 'adam'
        "epochs": 50,         # Increase to 200+ for paper results
        "batch_size": 128,
        "activation": "relu",
    }

    # ── Device setup ──────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # ── Reproducibility ───────────────────────────────────────────────────
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    # ── Create save directory ─────────────────────────────────────────────
    save_dir = "saved_nns"
    os.makedirs(save_dir, exist_ok=True)

    # ── Load dataset ──────────────────────────────────────────────────────
    print(f"Loading dataset: {configs['dataset']}")
    train_loader, val_loader, test_loader = get_cifar10(
        split_percentage=0.9,
        num_train=10000,
        num_test=2000,
        batch_size=configs["batch_size"],
    )

    # CIFAR-10: 32x32x3 = 3072 input dims, 10 classes
    input_dim = 3 * 32 * 32
    output_dim = 10

    # ── Build network ─────────────────────────────────────────────────────
    net = Net(
        input_dim=input_dim,
        output_dim=output_dim,
        width=configs["width"],
        depth=configs["depth"],
        activation=configs["activation"],
    )
    print(f"Network architecture:\n{net}")
    total_params = sum(p.numel() for p in net.parameters())
    print(f"Total parameters: {total_params:,}")

    # ── Save initialization state ─────────────────────────────────────────
    name = get_name(configs["dataset"], configs)
    init_path = os.path.join(save_dir, f"{name}_init.pt")
    torch.save(net.state_dict(), init_path)
    print(f"Saved initialization to: {init_path}")

    # ── Configure optimizer ───────────────────────────────────────────────
    optimizer = select_optimizer(configs["optimizer"], configs["lr"], net)
    print(f"Optimizer: {configs['optimizer'].upper()} | LR: {configs['lr']}")

    # ── Train ─────────────────────────────────────────────────────────────
    print(f"\nStarting training for {configs['epochs']} epochs...")
    net = train_network(
        net=net,
        optimizer=optimizer,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        epochs=configs["epochs"],
        device=device,
    )

    # ── Save trained network ──────────────────────────────────────────────
    trained_path = os.path.join(save_dir, f"{name}.pt")
    torch.save(net.state_dict(), trained_path)
    print(f"\nSaved trained network to: {trained_path}")

    # ── Final evaluation ──────────────────────────────────────────────────
    final_test_acc = evaluate(net, test_loader, device)
    print(f"Final Test Accuracy: {final_test_acc*100:.2f}%")

    print("\nTraining complete. Files saved:")
    print(f"  Trained:  {trained_path}")
    print(f"  Init:     {init_path}")
    print("Run verify_deep_NFA.py to check the Deep Neural Feature Ansatz.")


if __name__ == "__main__":
    main()
```

### `scripts/verify_ansatz.py`

```python
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
```

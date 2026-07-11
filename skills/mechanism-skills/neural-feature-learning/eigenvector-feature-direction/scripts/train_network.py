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

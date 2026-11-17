#!/usr/bin/env python3
"""
Usage Example: Recursive Feature Machines (RFM) with LaplaceRFM

Demonstrates how to use the rfm Python package to train a LaplaceRFM model
on synthetic data for both regression and classification tasks.

Requirements:
    pip install git+https://github.com/aradha/recursive_feature_machines.git@pip_install
    pip install torch torchvision==0.14.0 hickle==5.0.2 tqdm
"""

import torch
from rfm import LaplaceRFM


def get_device_and_memory():
    """
    Detect available compute device and estimate usable GPU/CPU memory.

    Returns:
        tuple: (torch.device, int) - device and available memory in GB
    """
    if torch.cuda.is_available():
        device = torch.device("cuda")
        # Reserve 1GB for safety
        mem_gb = torch.cuda.get_device_properties(device).total_memory // 1024**3 - 1
    else:
        device = torch.device("cpu")
        mem_gb = 8  # Default CPU memory assumption
    return device, mem_gb


def fstar(X: torch.Tensor) -> torch.Tensor:
    """
    Ground-truth target function for synthetic data generation.

    Generates a 2-class binary label based on two simple threshold rules:
      - Class 0: X[:,0] > 0
      - Class 1: X[:,1] < 0.5

    Args:
        X (torch.Tensor): Input tensor of shape (n, d).

    Returns:
        torch.Tensor: Float tensor of shape (n, 2) with binary labels.
    """
    return torch.cat(
        [
            (X[:, 0] > 0)[:, None],
            (X[:, 1] < 0.5)[:, None],
        ],
        axis=1,
    ).float()


def run_regression_example(device: torch.device, mem_gb: int):
    """
    Train LaplaceRFM on a synthetic regression task.

    Args:
        device (torch.device): Compute device (CPU or CUDA).
        mem_gb (int): Available memory in GB for kernel computations.
    """
    print("=" * 50)
    print("Example 1: Regression with LaplaceRFM")
    print("=" * 50)

    n = 1000  # number of samples
    d = 100   # input dimension
    # c = 2   # number of output classes (2 outputs from fstar)

    # Generate synthetic data
    X_train = torch.randn(n, d, device=device)
    X_test = torch.randn(n, d, device=device)
    y_train = fstar(X_train)
    y_test = fstar(X_test)

    print(f"Train shape: X={X_train.shape}, y={y_train.shape}")
    print(f"Test shape:  X={X_test.shape}, y={y_test.shape}")
    print(f"Device: {device}, Memory: {mem_gb}GB")

    # Initialize the model
    model = LaplaceRFM(
        bandwidth=1.0,
        device=device,
        mem_gb=mem_gb,
        diag=False  # Use full kernel matrix (set True for large datasets)
    )

    # Train the model
    model.fit(
        (X_train, y_train),
        (X_test, y_test),
        iters=5,
        classification=False  # Regression mode
    )

    print("Regression training complete.\n")


def run_classification_example(device: torch.device, mem_gb: int):
    """
    Train LaplaceRFM on a synthetic classification task.

    Args:
        device (torch.device): Compute device (CPU or CUDA).
        mem_gb (int): Available memory in GB for kernel computations.
    """
    print("=" * 50)
    print("Example 2: Classification with LaplaceRFM")
    print("=" * 50)

    n = 500
    d = 50

    X_train = torch.randn(n, d, device=device)
    X_test = torch.randn(n, d, device=device)
    y_train = fstar(X_train)
    y_test = fstar(X_test)

    model = LaplaceRFM(
        bandwidth=1.0,
        device=device,
        mem_gb=mem_gb,
        diag=False
    )

    model.fit(
        (X_train, y_train),
        (X_test, y_test),
        iters=5,
        classification=True  # Classification mode
    )

    print("Classification training complete.\n")


def run_diagonal_approximation_example(device: torch.device, mem_gb: int):
    """
    Train LaplaceRFM using diagonal kernel approximation for memory efficiency.

    The diag=True option is useful for large datasets where the full kernel
    matrix does not fit in memory.

    Args:
        device (torch.device): Compute device (CPU or CUDA).
        mem_gb (int): Available memory in GB.
    """
    print("=" * 50)
    print("Example 3: Diagonal Approximation (Memory Efficient)")
    print("=" * 50)

    n = 2000
    d = 200

    X_train = torch.randn(n, d, device=device)
    X_test = torch.randn(n, d, device=device)
    y_train = fstar(X_train)
    y_test = fstar(X_test)

    model = LaplaceRFM(
        bandwidth=1.0,
        device=device,
        mem_gb=mem_gb,
        diag=True  # Diagonal approximation for large-scale use
    )

    model.fit(
        (X_train, y_train),
        (X_test, y_test),
        iters=3,
        classification=False
    )

    print("Diagonal approximation training complete.\n")


if __name__ == "__main__":
    device, mem_gb = get_device_and_memory()
    print(f"Using device: {device} | Available memory: {mem_gb} GB\n")

    run_regression_example(device, mem_gb)
    run_classification_example(device, mem_gb)
    run_diagonal_approximation_example(device, mem_gb)

#!/usr/bin/env python3
"""
Demo: EGOP computation and patch extraction using ConvRFM utilities

This script demonstrates how to use the core components of the convrfm
repository:
  - patchify(): extract overlapping patches from image tensors
  - get_jacobian(): compute per-patch Jacobians of a network output
  - egop(): compute the Expected Gradient Outer Product (EGOP) over a dataset
  - get_imagenet(): construct an ImageNet DataLoader
  - PatchConvLayer: wrap a convolutional layer for patch-based processing

Requirements:
    pip install torch torchvision numpy scipy

NOTE: This script is structured to run standalone with synthetic data
for demonstration. Replace IMAGENET_PATH with your actual ImageNet
root directory to use real data.
"""

import sys
import os
import numpy as np

import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, TensorDataset

# ---------------------------------------------------------------------------
# Path setup: add repository root to sys.path so local modules are importable
# when running from inside the cloned convrfm directory.
# Adjust REPO_ROOT to point to the cloned convrfm repository on your system.
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IMAGENET_PATH = "/path/to/imagenet"   # Replace with your ImageNet root path
BATCH_SIZE = 16
PATCH_SIZE = 3
STRIDE_SIZE = 1
NUM_CLASSES = 10
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {DEVICE}")


# ===========================================================================
# Section 1: patchify() -- patch extraction from image tensors
# ===========================================================================

def demo_patchify():
    """
    Demonstrate the patchify function from cnfa_verification/pretrained_conv_nfa.py.

    patchify(x, patch_size, stride_size) extracts overlapping spatial patches
    from a 4D tensor of shape (N, C, H, W), returning a tensor of shape
    (N, num_patches, C * patch_size * patch_size).
    """
    print("\n" + "=" * 60)
    print("Section 1: patchify() demonstration")
    print("=" * 60)

    # Synthetic batch: 4 images, 3 channels, 8x8 spatial dims
    x = torch.randn(4, 3, 8, 8)
    print(f"Input tensor shape: {x.shape}  (N=4, C=3, H=8, W=8)")

    # Import directly from the repository module
    try:
        from cnfa_verification.pretrained_conv_nfa import patchify
        patches = patchify(x, patch_size=PATCH_SIZE, stride_size=STRIDE_SIZE)
        print(f"Patch size: {PATCH_SIZE}, stride: {STRIDE_SIZE}")
        print(f"Output patches shape: {patches.shape}")
        print("  Expected: (N, num_patches, C * patch_size^2)")
        print(f"  num_patches = ((H - patch_size) / stride + 1)^2 "
              f"= {((8 - PATCH_SIZE) // STRIDE_SIZE + 1) ** 2}")
    except ImportError as e:
        print(f"[INFO] Could not import from repository (expected when running "
              f"outside repo): {e}")
        print("[FALLBACK] Running standalone patchify implementation:")
        patches = standalone_patchify(x, patch_size=PATCH_SIZE, stride_size=STRIDE_SIZE)
        print(f"Output patches shape: {patches.shape}")

    return patches


def standalone_patchify(x: torch.Tensor, patch_size: int, stride_size: int) -> torch.Tensor:
    """
    Standalone reimplementation of patchify() for demonstration purposes.
    Mirrors the logic in cnfa_verification/pretrained_conv_nfa.py.

    Args:
        x (torch.Tensor): Input tensor of shape (N, C, H, W).
        patch_size (int): Height and width of each square patch.
        stride_size (int): Stride between consecutive patches.

    Returns:
        torch.Tensor: Tensor of shape (N, num_patches, C * patch_size * patch_size).
    """
    N, C, H, W = x.shape
    patches = x.unfold(2, patch_size, stride_size).unfold(3, patch_size, stride_size)
    # patches shape: (N, C, n_h, n_w, patch_size, patch_size)
    n_h = patches.shape[2]
    n_w = patches.shape[3]
    patches = patches.contiguous().view(N, C, n_h * n_w, patch_size * patch_size)
    # Rearrange to (N, num_patches, C * patch_size^2)
    patches = patches.permute(0, 2, 1, 3).contiguous()
    patches = patches.view(N, n_h * n_w, C * patch_size * patch_size)
    return patches


# ===========================================================================
# Section 2: get_jacobian() -- per-patch Jacobian of network output
# ===========================================================================

def demo_get_jacobian():
    """
    Demonstrate get_jacobian() from cnfa_verification/pretrained_conv_nfa.py.

    get_jacobian(net, data, c_idx) computes the Jacobian of the network output
    for class index c_idx with respect to the input data (patches).

    The Jacobian shape is (num_patches, input_dim) for a single sample or
    batched as (N, num_patches, input_dim).
    """
    print("\n" + "=" * 60)
    print("Section 2: get_jacobian() demonstration")
    print("=" * 60)

    # Build a minimal network for illustration
    # In practice, this would be a pretrained ResNet or VGG layer wrapper
    class ToyConvNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(3 * PATCH_SIZE * PATCH_SIZE, NUM_CLASSES)

        def forward(self, x):
            # x: (N, num_patches, patch_dim) -- flatten for demo
            N, P, D = x.shape
            out = self.fc(x.view(N * P, D))
            return out.view(N, P, NUM_CLASSES)

    net = ToyConvNet().to(DEVICE)
    net.eval()

    # Synthetic patchified data: (N=2, num_patches=36, patch_dim=27)
    data = torch.randn(2, 36, 3 * PATCH_SIZE * PATCH_SIZE, requires_grad=True).to(DEVICE)
    c_idx = 0  # Class index for Jacobian computation

    try:
        from cnfa_verification.pretrained_conv_nfa import get_jacobian
        jac = get_jacobian(net, data, c_idx)
        print(f"Input data shape: {data.shape}")
        print(f"Class index: {c_idx}")
        print(f"Jacobian shape: {jac.shape}")
    except ImportError as e:
        print(f"[INFO] Could not import from repository: {e}")
        print("[FALLBACK] Running standalone Jacobian computation:")
        jac = standalone_get_jacobian(net, data, c_idx)
        print(f"Input data shape: {data.shape}")
        print(f"Class index: {c_idx}")
        print(f"Jacobian shape: {jac.shape}")

    return jac


def standalone_get_jacobian(
    net: nn.Module,
    data: torch.Tensor,
    c_idx: int
) -> torch.Tensor:
    """
    Standalone Jacobian computation mirroring the logic in
    cnfa_verification/pretrained_conv_nfa.py.

    Args:
        net (nn.Module): Network to differentiate through.
        data (torch.Tensor): Patchified input of shape (N, num_patches, patch_dim).
        c_idx (int): Class index to compute gradients for.

    Returns:
        torch.Tensor: Jacobian of shape (N, num_patches, patch_dim).
    """
    data = data.detach().requires_grad_(True)
    output = net(data)  # (N, num_patches, num_classes)
    # Sum over spatial positions for selected class
    scalar = output[:, :, c_idx].sum()
    scalar.backward()
    jac = data.grad.clone()
    return jac


# ===========================================================================
# Section 3: egop() -- Expected Gradient Outer Product computation
# ===========================================================================

def demo_egop():
    """
    Demonstrate egop() from cnfa_verification/pretrained_conv_nfa.py.

    egop(model, X) computes the Expected Gradient Outer Product over dataset X.
    The EGOP is the average of J^T J over all samples, where J is the Jacobian
    of the network output with respect to the input features. This forms the
    basis of the Neural Feature Ansatz.

    Returns:
        np.ndarray: EGOP matrix of shape (patch_dim, patch_dim).
    """
    print("\n" + "=" * 60)
    print("Section 3: egop() demonstration")
    print("=" * 60)

    patch_dim = 3 * PATCH_SIZE * PATCH_SIZE
    num_patches = 16
    N = 8  # Small synthetic dataset

    class ToyNet(nn.Module):
        """Minimal network for EGOP demonstration."""
        def __init__(self, in_dim: int, n_classes: int):
            super().__init__()
            self.proj = nn.Linear(in_dim, n_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (N, num_patches, patch_dim)
            N, P, D = x.shape
            return self.proj(x.view(N * P, D)).view(N, P, -1)

    model = ToyNet(in_dim=patch_dim, n_classes=NUM_CLASSES).to(DEVICE)
    model.eval()

    # Synthetic dataset: (N, num_patches, patch_dim)
    X = torch.randn(N, num_patches, patch_dim).to(DEVICE)

    try:
        from cnfa_verification.pretrained_conv_nfa import egop
        egop_matrix = egop(model, X)
        print(f"Input X shape: {X.shape}")
        print(f"EGOP matrix shape: {egop_matrix.shape}")
        print(f"EGOP matrix dtype: {egop_matrix.dtype}")
    except ImportError as e:
        print(f"[INFO] Could not import from repository: {e}")
        print("[FALLBACK] Running standalone EGOP computation:")
        egop_matrix = standalone_egop(model, X)
        print(f"Input X shape: {X.shape}")
        print(f"EGOP matrix shape: {egop_matrix.shape}")

    return egop_matrix


def standalone_egop(model: nn.Module, X: torch.Tensor) -> np.ndarray:
    """
    Standalone EGOP computation mirroring egop() in
    cnfa_verification/pretrained_conv_nfa.py.

    Computes E[J^T J] where J is the Jacobian of all class outputs
    w.r.t. each patch, averaged over the dataset.

    Args:
        model (nn.Module): Trained neural network.
        X (torch.Tensor): Patchified dataset of shape (N, num_patches, patch_dim).

    Returns:
        np.ndarray: EGOP matrix of shape (patch_dim, patch_dim).
    """
    N, P, D = X.shape
    egop_accum = np.zeros((D, D), dtype=np.float64)

    for i in range(N):
        x_i = X[i:i+1].detach().requires_grad_(True)  # (1, P, D)
        output = model(x_i)  # (1, P, num_classes)
        num_classes = output.shape[-1]

        for c in range(num_classes):
            scalar = output[0, :, c].sum()
            scalar.backward(retain_graph=(c < num_classes - 1))
            if x_i.grad is not None:
                g = x_i.grad[0].detach().cpu().numpy()  # (P, D)
                # Sum outer products over patches
                egop_accum += g.T @ g
                x_i.grad.zero_()

    egop_accum /= N
    return egop_accum


# ===========================================================================
# Section 4: get_imagenet() -- ImageNet DataLoader construction
# ===========================================================================

def demo_get_imagenet():
    """
    Demonstrate get_imagenet() from cnfa_verification/dataset.py.

    get_imagenet(batch_size, path) returns a PyTorch DataLoader for the
    ImageNet validation set. Requires a local copy of ImageNet at `path`.

    This demo shows the expected call signature and what the loader returns.
    It uses a synthetic TensorDataset as fallback when the real path is absent.
    """
    print("\n" + "=" * 60)
    print("Section 4: get_imagenet() demonstration")
    print("=" * 60)

    if os.path.exists(IMAGENET_PATH):
        try:
            from cnfa_verification.dataset import get_imagenet
            loader = get_imagenet(batch_size=BATCH_SIZE, path=IMAGENET_PATH)
            batch = next(iter(loader))
            images, labels = batch
            print(f"ImageNet batch images shape: {images.shape}")
            print(f"ImageNet batch labels shape: {labels.shape}")
            print(f"  batch_size={BATCH_SIZE}, image dtype={images.dtype}")
            return loader
        except ImportError as e:
            print(f"[INFO] Could not import from repository: {e}")
    else:
        print(f"[INFO] ImageNet path not found: '{IMAGENET_PATH}'")
        print("[FALLBACK] Demonstrating expected call signature and output format:")

    # Fallback: synthetic DataLoader with the same interface
    fake_images = torch.randn(64, 3, 224, 224)
    fake_labels = torch.randint(0, 1000, (64,))
    fake_dataset = TensorDataset(fake_images, fake_labels)
    fake_loader = DataLoader(fake_dataset, batch_size=BATCH_SIZE, shuffle=False)

    batch = next(iter(fake_loader))
    images, labels = batch
    print(f"Synthetic batch images shape: {images.shape}  "
          f"(matches ImageNet 224x224 format)")
    print(f"Synthetic batch labels shape: {labels.shape}")
    print(f"  To use real ImageNet: get_imagenet(batch_size={BATCH_SIZE}, "
          f"path='{IMAGENET_PATH}')")
    return fake_loader


# ===========================================================================
# Section 5: get_filter() and get_classes() -- binary classification utilities
# ===========================================================================

def demo_binary_utils():
    """
    Demonstrate get_filter() and get_classes() from conv_nets/binary_main.py.

    get_filter(net, layer): extracts the weight tensor from a named layer
    of network `net`.

    get_classes(X_full, y_full, c1): filters dataset arrays to return only
    samples belonging to class c1, used for binary classification setup.
    """
    print("\n" + "=" * 60)
    print("Section 5: get_filter() and get_classes() demonstration")
    print("=" * 60)

    # --- get_filter() ---
    class SimpleConvNet(nn.Module):
        """Minimal CNN with named layers for filter extraction demo."""
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
            self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
            self.fc = nn.Linear(64 * 4 * 4, 10)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = torch.relu(self.conv1(x))
            x = torch.relu(self.conv2(x))
            x = x.view(x.size(0), -1)
            return self.fc(x)

    net = SimpleConvNet()

    try:
        from conv_nets.binary_main import get_filter
        filters = get_filter(net, layer="conv1")
        print(f"get_filter(net, layer='conv1') shape: {filters.shape}")
    except ImportError as e:
        print(f"[INFO] Could not import from repository: {e}")
        print("[FALLBACK] Running standalone get_filter:")
        filters = standalone_get_filter(net, layer="conv1")
        print(f"get_filter(net, layer='conv1') shape: {filters.shape}")

    # --- get_classes() ---
    # Synthetic full dataset: 100 samples, 5 classes, 32-dim features
    np.random.seed(42)
    X_full = np.random.randn(100, 32).astype(np.float32)
    y_full = np.random.randint(0, 5, size=100)
    c1 = 2  # Extract only class 2 samples

    try:
        from conv_nets.binary_main import get_classes
        X_c1, y_c1 = get_classes(X_full, y_full, c1)
        print(f"\nget_classes(X_full, y_full, c1={c1}):")
        print(f"  Total samples: {len(X_full)}")
        print(f"  Samples in class {c1}: {X_c1.shape[0]}")
        print(f"  X_c1 shape: {X_c1.shape}, y_c1 shape: {y_c1.shape}")
    except ImportError as e:
        print(f"[INFO] Could not import from repository: {e}")
        print("[FALLBACK] Running standalone get_classes:")
        X_c1, y_c1 = standalone_get_classes(X_full, y_full, c1)
        print(f"\nget_classes(X_full, y_full, c1={c1}):")
        print(f"  Total samples: {len(X_full)}")
        print(f"  Samples in class {c1}: {X_c1.shape[0]}")
        print(f"  X_c1 shape: {X_c1.shape}, y_c1 shape: {y_c1.shape}")


def standalone_get_filter(net: nn.Module, layer: str) -> torch.Tensor:
    """
    Standalone implementation of get_filter() from conv_nets/binary_main.py.

    Args:
        net (nn.Module): Trained convolutional network.
        layer (str): Name of the layer to extract filters from.

    Returns:
        torch.Tensor: Weight tensor of the specified layer.
    """
    return getattr(net, layer).weight.data


def standalone_get_classes(
    X_full: np.ndarray,
    y_full: np.ndarray,
    c1: int
) -> tuple:
    """
    Standalone implementation of get_classes() from conv_nets/binary_main.py.

    Args:
        X_full (np.ndarray): Full feature matrix of shape (N, D).
        y_full (np.ndarray): Full label array of shape (N,).
        c1 (int): Target class index to filter.

    Returns:
        tuple: (X_c1, y_c1) -- filtered features and labels for class c1.
    """
    mask = y_full == c1
    return X_full[mask], y_full[mask]


# ===========================================================================
# Section 6: Full mini pipeline -- patchify -> Jacobian -> EGOP
# ===========================================================================

def demo_full_pipeline():
    """
    Demonstrate a complete CNFA-style pipeline:
      1. Load synthetic image batch
      2. Patchify the images
      3. Compute per-class Jacobians
      4. Compute EGOP from Jacobians
      5. Inspect the EGOP eigenspectrum

    This mirrors the workflow in cnfa_verification/pretrained_conv_nfa.py.
    """
    print("\n" + "=" * 60)
    print("Section 6: Full mini pipeline (patchify -> Jacobian -> EGOP)")
    print("=" * 60)

    N, C, H, W = 8, 3, 16, 16
    n_classes = 5
    patch_size = 3
    stride = 1
    patch_dim = C * patch_size * patch_size

    # Step 1: Synthetic image batch
    images = torch.randn(N, C, H, W).to
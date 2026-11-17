---
name: deep-neural-feature-ansatz
description: "Use this skill when working with the Deep Neural Feature Ansatz (DNFA) \u2014 verifying feature learning in neural networks, training fully connected networks on image/tabular datasets, computing Neural Tangent Kernels (NTK) and Neural Network Gaussian Processes (NNGP), or reproducing experiments from the paper \"The Deep Neural Feature Ansatz\" (arXiv:2212.13881)."
---

## Method and use

Investigate DNFA-style relationships between weight-derived neural feature matrices and expected gradient outer products. Align the input coordinates and sampling distribution. The alignment helper is a limited diagnostic, not a complete reproduction or a universal law of learned features.


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


See [`scripts/train_network.py`](scripts/train_network.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/verify_ansatz.py`


See [`scripts/verify_ansatz.py`](scripts/verify_ansatz.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

---
name: recursive-feature-machines
description: "Use this skill when working with Recursive Feature Machines (RFM) for kernel-based machine learning, feature learning, or when implementing backpropagation-free models that learn features similarly to neural networks."
---

## Method and use

Use recursive feature machines to update kernel geometry from gradient outer products and study learned feature directions. Compare kernel choices, bandwidth, memory cost, and diagonal approximations. The synthetic examples demonstrate an algorithm, not a finding about a target language model.


# Recursive Feature Machines (RFM)

## When to Use
Activate this skill when:
- Implementing kernel methods with learned features
- Exploring backpropagation-free machine learning models
- Working with the `rfm` Python package or `LaplaceRFM`
- Studying the mechanism of feature learning in neural networks
- Tasks involve low-rank polynomial learning or image classification (SVHN)
- Keywords: RFM, recursive feature machines, LaplaceRFM, kernel learning, feature learning

## Quick Reference
- **Paper:** [Mechanism for feature learning in neural networks and backpropagation-free machine learning models](https://www.science.org/doi/10.1126/science.adi5639)
- **Repository:** https://github.com/aradha/recursive_feature_machines
- **Branch:** pip_install

## Installation

### Prerequisites
- Python 3.8+
- PyTorch 1.13 (for stable behavior)
- torchvision==0.14.0
- hickle==5.0.2
- tqdm

### Install via pip
```bash
pip install git+https://github.com/aradha/recursive_feature_machines.git@pip_install
```

## Core Features
- **LaplaceRFM:** Recursive Feature Machine using the Laplace kernel
- **Feature learning without backpropagation:** Learns data-adaptive features via iterative kernel updates
- **GPU support:** Automatically uses CUDA if available, with memory management via `mem_gb`
- **Classification and Regression:** Supports both via the `classification` flag in `fit()`
- **Diagonal approximation:** Optional diagonal kernel approximation via `diag=True`

## Usage Examples

### Basic Setup and Training
```python
import torch
from rfm import LaplaceRFM

if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    DEV_MEM_GB = torch.cuda.get_device_properties(DEVICE).total_memory//1024**3 - 1
else:
    DEVICE = torch.device("cpu")
    DEV_MEM_GB = 8

def fstar(X):
    return torch.cat([(X[:,0]>0)[:,None], 
    (X[:,1]<0.5)[:,None]], axis=1).float()

model = LaplaceRFM(bandwidth=1., device=DEVICE, mem_gb=DEV_MEM_GB, diag=False)

n = 1000  # samples
d = 100   # dimension
c = 2     # classes

X_train = torch.randn(n, d, device=DEVICE)
X_test = torch.randn(n, d, device=DEVICE)
y_train = fstar(X_train)
y_test = fstar(X_test)

model.fit(
    (X_train, y_train),
    (X_test, y_test),
    iters=5,
    classification=False
)
```

## Key APIs/Models

### `LaplaceRFM`
- **Constructor params:** `bandwidth`, `device`, `mem_gb`, `diag`
- **Method:** `fit(train_data, test_data, iters, classification)`

## Common Patterns & Best Practices
- Always check for CUDA availability and set `mem_gb` accordingly to avoid OOM errors
- Use `diag=True` for large-scale problems where full kernel matrix is too expensive
- Start with `iters=5` and increase if underfitting
- Use `classification=False` for regression tasks; `classification=True` for discrete label prediction
- Tested stable with PyTorch 1.13 and Python 3.8

## Demo Scripts

### `scripts/rfm_usage_example.py`


See [`scripts/rfm_usage_example.py`](scripts/rfm_usage_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

---
name: fastshap
description: "Use this skill when you need to train amortized Shapley value explainers using FastSHAP, generate real-time local feature importance explanations for machine learning models (tabular or image), train surrogate models for feature masking, or understand how FastSHAP's KernelSHAP-inspired training objective works with PyTorch."
---

## Method and use

Train a FastSHAP-style explainer to amortize local Shapley estimation, often with a surrogate for masked inputs. Validate approximation and background assumptions against the target use. Efficiency normalization enforces a sum constraint but cannot establish explanation correctness on its own.


# FastSHAP Skill

## When to Use

Activate this skill when:
- You need to generate **Shapley value explanations** for a predictive model's outputs
- You want to train an **amortized explainer** (neural network) that produces explanations in a single forward pass rather than running KernelSHAP separately for each sample
- You are working with **tabular data** (census/adult-style datasets) and want feature attribution explanations
- You are working with **image data** (e.g., CIFAR-10, ImageNet) and need pixel/superpixel-level explanations
- You want to train a **surrogate model** that accepts masked/missing features to support the FastSHAP training process
- You need **real-time or batch Shapley value estimates** with lower computational overhead than KernelSHAP
- Keywords: `shapley values`, `SHAP`, `model explainability`, `feature importance`, `amortized inference`, `KernelSHAP`, `surrogate model`, `FastSHAP`, `local explanations`, `XAI`, `interpretability`

## Quick Reference

| Resource | URL |
|----------|-----|
| Paper (arXiv) | https://arxiv.org/abs/2107.07436 |
| GitHub Repository | https://github.com/iancovert/fastshap |
| TensorFlow implementation | https://github.com/neiljethani/fastshap |
| Census notebook | https://github.com/iancovert/fastshap/blob/main/notebooks/census.ipynb |
| CIFAR-10 notebook | https://github.com/iancovert/fastshap/blob/main/notebooks/cifar.ipynb |
| CIFAR-10 single model notebook | https://github.com/iancovert/fastshap/blob/main/notebooks/cifar%20single%20model.ipynb |
| Blog: Understanding SHAP/SAGE | https://iancovert.com/blog/understanding-shap-sage/ |

## Installation / Setup

### Prerequisites
- Python 3.7+
- PyTorch (install separately per your CUDA version)
- A machine learning model to explain (e.g., LightGBM, XGBoost, sklearn, PyTorch CNN)

### Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/iancovert/fastshap.git
cd fastshap

# Install the package
pip install .
```

### Install Dependencies for Notebooks

```bash
pip install torch torchvision lightgbm scikit-learn numpy pandas matplotlib
```

### Verify Installation

```python
import fastshap
from fastshap import FastSHAP, Surrogate
from fastshap.tabular_imputers import MarginalImputer, BaselineImputer
from fastshap.image_imputers import BaselineImageImputer
print("FastSHAP installed successfully")
```

## Core Features

- **FastSHAP Explainer Training**: Train a neural network to produce Shapley value estimates in a single forward pass using a KernelSHAP-inspired objective function.
- **Tabular Data Support**: Full pipeline for tabular models including surrogate training, MLP explainer training, and marginal/baseline imputation strategies.
- **Image Data Support**: Full pipeline for image models (e.g., ResNet, UNet explainer) with superpixel-based masking and image surrogate training.
- **Surrogate Model Wrapper (`Surrogate`)**: Train a surrogate (e.g., MLP) to replicate a black-box model's predictions when features are marginalized out.
- **Image Surrogate Wrapper (`ImageSurrogate`)**: Train a surrogate specifically designed for image models with superpixel masking support.
- **Multiple Imputation Strategies**:
  - `MarginalImputer`: Replace held-out features with samples from the marginal distribution.
  - `BaselineImputer`: Replace held-out features with fixed baseline values (e.g., zeros or means).
  - `BaselineImageImputer`: Replace held-out image superpixels with a baseline (e.g., gray).
- **Efficient Normalization**: `additive_efficient_normalization` and `multiplicative_efficient_normalization` ensure Shapley value estimates satisfy the efficiency axiom (sum to model output).
- **Flexible Explainer Architectures**: Any `torch.nn.Module` can serve as the explainer (MLP for tabular, UNet for images).
- **Single-Model FastSHAP**: Option to use a model that natively handles missing features, eliminating the need for a separate surrogate.

## Usage Examples

### Overview of the FastSHAP Pipeline

The FastSHAP pipeline has three stages:

1. **Train or load a predictive model** (any black-box model).
2. **Train a surrogate model** to handle masked/missing features.
3. **Train the FastSHAP explainer** to output Shapley value estimates.

After training, generate explanations with a single forward pass.

### Tabular Data Pipeline (Census/Adult Dataset)

```python
import numpy as np
import torch
import torch.nn as nn
from fastshap import FastSHAP, Surrogate
from fastshap.tabular_imputers import MarginalImputer

# --- Step 1: Prepare data and original model ---
# (Assume X_train, X_val, X_test are numpy arrays, model is a trained LightGBM/XGBoost)
# model.predict_proba(X_train)  ->  shape (N, num_classes)

# --- Step 2: Set up imputer (surrogate or marginal) ---
# MarginalImputer replaces masked features with samples from training data
imputer = MarginalImputer(model, X_train)

# --- Step 3: Train surrogate model ---
# The surrogate is an MLP that takes (x, mask) as input and replicates model predictions
surrogate_model = nn.Sequential(
    nn.Linear(num_features * 2, 128),  # input: [features | mask]
    nn.ReLU(),
    nn.Linear(128, 128),
    nn.ReLU(),
    nn.Linear(128, num_outputs),
    nn.Softmax(dim=1)
)
surr = Surrogate(surrogate_model, num_features)
surr.train(
    train_data=X_train,
    val_data=X_val,
    original_model=model,
    batch_size=64,
    max_epochs=10,
    loss_fn=nn.MSELoss(),
    imputer=imputer,
)

# --- Step 4: Train FastSHAP explainer ---
explainer_model = nn.Sequential(
    nn.Linear(num_features, 128),
    nn.ReLU(),
    nn.Linear(128, 128),
    nn.ReLU(),
    nn.Linear(128, num_features * num_outputs)  # output: shapley values
)
fastshap = FastSHAP(
    explainer=explainer_model,
    imputer=surr,
    normalization='additive',
    link=nn.Softmax(dim=1)
)
fastshap.train(
    train_data=X_train,
    val_data=X_val,
    batch_size=64,
    num_samples=8,
    max_epochs=10,
    validation_samples=128,
    loss_fn='mse',
)

# --- Step 5: Generate explanations ---
shap_values = fastshap.shap_values(X_test)
# shap_values shape: (N, num_features, num_outputs)
print("SHAP values shape:", shap_values.shape)
```

### Image Data Pipeline (CIFAR-10)

```python
import torch
import torch.nn as nn
from torchvision import models
from fastshap import FastSHAP, ImageSurrogate
from fastshap.image_imputers import BaselineImageImputer

# Image dimensions and superpixel settings
width, height = 32, 32
superpixel_size = 4  # 4x4 superpixels -> 8x8 = 64 superpixels

# --- Step 1: Load original ResNet18 model ---
original_model = models.resnet18(pretrained=True)
original_model.eval()

# --- Step 2: Set up image imputer ---
imputer = BaselineImageImputer(
    width=width,
    height=height,
    superpixel_size=superpixel_size,
    baseline=0.5  # gray baseline value
)

# --- Step 3: Train image surrogate (another ResNet18) ---
surrogate_model = models.resnet18(pretrained=False)
image_surr = ImageSurrogate(
    surrogate=surrogate_model,
    width=width,
    height=height,
    superpixel_size=superpixel_size
)
# image_surr.train(train_data, val_data, original_model, ...)

# --- Step 4: Set up UNet explainer and train FastSHAP ---
# (UNet architecture is defined in notebooks/unet.py)
# fastshap = FastSHAP(explainer=unet_model, imputer=image_surr, ...)
# fastshap.train(...)

# --- Step 5: Generate image explanations ---
# shap_values = fastshap.shap_values(image_batch)
# shap_values shape: (N, num_superpixels, num_classes)
```

### Generating Shapley Values After Training

```python
# Single sample
sample = X_test[0:1]
shap_vals = fastshap.shap_values(sample)

# Batch of samples
shap_vals = fastshap.shap_values(X_test[:100])

# shap_vals[i, j, k] = contribution of feature j to class k for sample i
```

### Using Normalization Functions Directly

```python
from fastshap.fastshap import (
    additive_efficient_normalization,
    multiplicative_efficient_normalization
)
import torch

# pred: raw explainer output (batch, num_features, num_outputs)
# grand: model output with all features (batch, num_outputs)
# null: model output with no features (num_outputs,)

pred = torch.randn(16, 10, 2)
grand = torch.randn(16, 2)
null = torch.zeros(2)

normalized = additive_efficient_normalization(pred, grand, null)
# normalized.sum(dim=1) ~= grand - null  (efficiency property)
```

## Key APIs / Models

### Classes

| Class | Module | Description |
|-------|--------|-------------|
| `FastSHAP` | `fastshap.fastshap` | Main explainer wrapper; trains explainer model and generates SHAP values |
| `Surrogate` | `fastshap.surrogate` | Trains/wraps surrogate model for tabular data |
| `ImageSurrogate` | `fastshap.image_surrogate` | Trains/wraps surrogate model for image data |
| `MarginalImputer` | `fastshap.tabular_imputers` | Replaces masked features with marginal distribution samples |
| `BaselineImputer` | `fastshap.tabular_imputers` | Replaces masked features with fixed baseline values |
| `ImageImputer` | `fastshap.image_imputers` | Base class for image imputers |
| `BaselineImageImputer` | `fastshap.image_imputers` | Replaces masked image superpixels with baseline values |

### Key Functions

| Function | Module | Description |
|----------|--------|-------------|
| `additive_efficient_normalization(pred, grand, null)` | `fastshap.fastshap` | Normalizes SHAP predictions to satisfy efficiency axiom (additive) |
| `multiplicative_efficient_normalization(pred, grand, null)` | `fastshap.fastshap` | Normalizes SHAP predictions to satisfy efficiency axiom (multiplicative) |
| `evaluate_explainer(explainer, normalization, x)` | `fastshap.fastshap` | Runs explainer forward pass with normalization applied |
| `validate(surrogate, loss_fn, data_loader)` | `fastshap.surrogate` | Validates surrogate model on a data loader |
| `generate_labels(dataset, model, batch_size)` | `fastshap.surrogate` | Generates soft labels from original model for surrogate training |

### Architectures Used in Experiments

| Architecture | Role | Dataset |
|--------------|------|---------|
| LightGBM / LGBM | Original predictive model | Census/Adult tabular |
| MLP (PyTorch) | Surrogate model | Census/Adult tabular |
| MLP (PyTorch) | Explainer model | Census/Adult tabular |
| ResNet18 | Original predictive model | CIFAR-10 images |
| ResNet18 | Surrogate model | CIFAR-10 images |
| UNet | Explainer model (image-sized output) | CIFAR-10 images |

### Normalization Options

| Option | String Key | Description |
|--------|-----------|-------------|
| Additive | `'additive'` | Subtracts/adds residual to sum term |
| Multiplicative | `'multiplicative'` | Scales predictions to match efficiency |
| None | `None` | No normalization applied |

## Common Patterns & Best Practices

### Choosing an Imputer

- **`MarginalImputer`**: Best for tabular data when you want to marginalize over the training distribution. More faithful to the original model's behavior.
- **`BaselineImputer`**: Faster but less statistically principled; uses a fixed reference value (e.g., feature mean or zero).
- **`BaselineImageImputer`**: Standard choice for image tasks; uses a constant pixel value (gray/black) as the baseline.

### Choosing Normalization

- Always use `normalization='additive'` unless you have a specific reason to use multiplicative. The additive normalization enforces the efficiency axiom (SHAP values sum to model output minus baseline).

### Surrogate vs. Single Model

- **Surrogate approach** (two models): More general; works for any black-box model. Train a surrogate that accepts `(x, mask)` pairs and replicates original model outputs.
- **Single model approach**: The predictive model itself is trained to handle missing features. Fewer parameters to manage, but requires retraining the original model. See the [single model notebook](https://github.com/iancovert/fastshap/blob/main/notebooks/cifar%20single%20model.ipynb).

### Number of Samples During Training

- The `num_samples` argument in `FastSHAP.train()` controls how many random coalition samples are drawn per training example per batch. Higher values → more stable gradient estimates but slower training. Start with 8–16 for tabular, 4–8 for image data.

### Explainer Architecture for Images

- The explainer output must be the same spatial size as the input (e.g., a UNet). The explainer output has shape `(batch, height, width, num_classes)` reshaped appropriately.

### Validation During Training

- Use `validation_samples` (number of coalitions to average over during validation) to get stable validation loss estimates. A value of 64–128 works well.

### Link Functions

- Pass a link function (e.g., `nn.Softmax(dim=1)` for classification) to `FastSHAP` if you want SHAP values to be defined on the probability scale rather than the logit scale.

## Demo Scripts

### `scripts/01_tabular_fastshap_demo.py`


See [`scripts/01_tabular_fastshap_demo.py`](scripts/01_tabular_fastshap_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/02_normalization_and_utils_demo.py`


See [`scripts/02_normalization_and_utils_demo.py`](scripts/02_normalization_and_utils_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

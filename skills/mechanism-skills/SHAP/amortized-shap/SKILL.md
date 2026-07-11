---
name: fastshap
description: Use this skill when you need to train amortized Shapley value explainers using FastSHAP, generate real-time local feature importance explanations for machine learning models (tabular or image), train surrogate models for feature masking, or understand how FastSHAP's KernelSHAP-inspired training objective works with PyTorch.
---

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

```python
#!/usr/bin/env python3
"""
FastSHAP Tabular Data Demo
==========================
Demonstrates the complete FastSHAP pipeline for a tabular classification task
using synthetic data. The pipeline covers:

  1. Training a simple "black-box" predictive model (logistic regression via PyTorch)
  2. Training a surrogate model using MarginalImputer
  3. Training the FastSHAP explainer model
  4. Generating Shapley value estimates for test samples

Requirements:
    pip install . (from fastshap repo root)
    pip install torch numpy scikit-learn

Usage:
    python 01_tabular_fastshap_demo.py
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# FastSHAP imports
from fastshap import FastSHAP, Surrogate
from fastshap.tabular_imputers import MarginalImputer


# ─── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

# ─── Configuration ────────────────────────────────────────────────────────────
NUM_FEATURES = 20
NUM_CLASSES = 2
NUM_SAMPLES = 2000
BATCH_SIZE = 64
SURROGATE_EPOCHS = 5
EXPLAINER_EPOCHS = 5
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ─── Helper: Simple MLP builder ───────────────────────────────────────────────

def build_mlp(
    input_dim: int,
    hidden_dim: int,
    output_dim: int,
    hidden_layers: int = 2,
    activation: nn.Module = nn.ReLU(),
    output_activation: nn.Module = None,
) -> nn.Sequential:
    """
    Build a simple fully-connected MLP.

    Args:
        input_dim: Number of input features.
        hidden_dim: Width of each hidden layer.
        output_dim: Number of output units.
        hidden_layers: Number of hidden layers.
        activation: Activation function between layers.
        output_activation: Optional activation after the final layer.

    Returns:
        A torch.nn.Sequential MLP module.
    """
    layers = [nn.Linear(input_dim, hidden_dim), nn.ReLU()]
    for _ in range(hidden_layers - 1):
        layers += [nn.Linear(hidden_dim, hidden_dim), nn.ReLU()]
    layers.append(nn.Linear(hidden_dim, output_dim))
    if output_activation is not None:
        layers.append(output_activation)
    return nn.Sequential(*layers)


# ─── Step 1: Generate Synthetic Data & Train Original Model ───────────────────

def prepare_data():
    """Generate synthetic tabular classification data and split into splits."""
    X, y = make_classification(
        n_samples=NUM_SAMPLES,
        n_features=NUM_FEATURES,
        n_informative=10,
        n_redundant=5,
        random_state=SEED,
    )
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=SEED
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=SEED
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val = scaler.transform(X_val).astype(np.float32)
    X_test = scaler.transform(X_test).astype(np.float32)

    return X_train, X_val, X_test, y_train, y_val, y_test


def train_original_model(X_train: np.ndarray, y_train: np.ndarray) -> nn.Module:
    """
    Train a simple logistic regression model as the 'black-box' model to explain.

    Args:
        X_train: Training features, shape (N, num_features).
        y_train: Training labels, shape (N,).

    Returns:
        Trained PyTorch model that outputs class probabilities.
    """
    model = build_mlp(
        input_dim=NUM_FEATURES,
        hidden_dim=64,
        output_dim=NUM_CLASSES,
        output_activation=nn.Softmax(dim=1),
    ).to(DEVICE)

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    X_t = torch.tensor(X_train, device=DEVICE)
    y_t = torch.tensor(y_train, dtype=torch.long, device=DEVICE)
    dataset = TensorDataset(X_t, y_t)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model.train()
    for epoch in range(5):
        total_loss = 0.0
        for xb, yb in loader:
            optimizer.zero_grad()
            preds = model(xb)
            loss = loss_fn(preds, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  [OriginalModel] Epoch {epoch+1}/5 | Loss: {total_loss/len(loader):.4f}")

    model.eval()
    return model


# ─── Wrapper: make original model callable on numpy arrays ────────────────────

class NumpyModelWrapper:
    """
    Wraps a PyTorch model to accept numpy arrays and return numpy arrays.
    Required by FastSHAP's MarginalImputer.
    """

    def __init__(self, model: nn.Module, device: torch.device):
        self.model = model
        self.device = device

    def __call__(self, X: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            X_t = torch.tensor(X, dtype=torch.float32, device=self.device)
            out = self.model(X_t)
        return out.cpu().numpy()


# ─── Step 2: Build & Train Surrogate Model ────────────────────────────────────

def train_surrogate(
    original_model_wrapper,
    X_train: np.ndarray,
    X_val: np.ndarray,
) -> Surrogate:
    """
    Train a surrogate model that accepts masked feature vectors.

    The surrogate is an MLP with input dimension `num_features * 2`
    (concatenated features + binary mask) and output dimension `num_classes`.

    Args:
        original_model_wrapper: Callable that takes numpy X and returns numpy probs.
        X_train: Training features.
        X_val: Validation features.

    Returns:
        Trained Surrogate wrapper object.
    """
    # Surrogate input = [x_masked | mask], so input_dim = num_features * 2
    surrogate_net = build_mlp(
        input_dim=NUM_FEATURES * 2,
        hidden_dim=128,
        output_dim=NUM_CLASSES,
        hidden_layers=2,
        output_activation=nn.Softmax(dim=1),
    ).to(DEVICE)

    surr = Surrogate(surrogate=surrogate_net, num_features=NUM_FEATURES)

    print("\n[Surrogate] Training surrogate model...")
    surr.train(
        train_data=X_train,
        val_data=X_val,
        original_model=original_model_wrapper,
        batch_size=BATCH_SIZE,
        max_epochs=SURROGATE_EPOCHS,
        loss_fn=nn.MSELoss(),
        imputer=MarginalImputer(original_model_wrapper, X_train),
        lookback=5,
        verbose=True,
    )
    print("[Surrogate] Training complete.")
    return surr


# ─── Step 3: Build & Train FastSHAP Explainer ────────────────────────────────

def train_fastshap_explainer(
    surr: Surrogate,
    X_train: np.ndarray,
    X_val: np.ndarray,
    original_model_wrapper,
) -> FastSHAP:
    """
    Train the FastSHAP explainer model.

    The explainer takes x (num_features,) as input and outputs Shapley value
    estimates of shape (num_features * num_classes,), which are then reshaped
    to (num_features, num_classes).

    Args:
        surr: Trained Surrogate object (used as imputer for FastSHAP training).
        X_train: Training features.
        X_val: Validation features.
        original_model_wrapper: Callable original model (for grand/null computation).

    Returns:
        Trained FastSHAP object.
    """
    # Explainer: x (num_features,) -> shap values (num_features * num_classes,)
    explainer_net = build_mlp(
        input_dim=NUM_FEATURES,
        hidden_dim=128,
        output_dim=NUM_FEATURES * NUM_CLASSES,
        hidden_layers=2,
    ).to(DEVICE)

    fastshap = FastSHAP(
        explainer=explainer_net,
        imputer=surr,
        normalization="additive",
        link=nn.Softmax(dim=1),
    )

    print("\n[FastSHAP] Training explainer model...")
    fastshap.train(
        train_data=X_train,
        val_data=X_val,
        batch_size=BATCH_SIZE,
        num_samples=8,           # coalitions sampled per example per batch
        max_epochs=EXPLAINER_EPOCHS,
        validation_samples=64,   # coalitions averaged during validation
        loss_fn="mse",
        verbose=True,
        lookback=5,
    )
    print("[FastSHAP] Training complete.")
    return fastshap


# ─── Step 4: Generate & Inspect Shapley Values ────────────────────────────────

def generate_and_inspect_shap_values(
    fastshap: FastSHAP,
    X_test: np.ndarray,
) -> np.ndarray:
    """
    Use the trained FastSHAP model to generate Shapley value explanations.

    Args:
        fastshap: Trained FastSHAP object.
        X_test: Test feature matrix, shape (N, num_features).

    Returns:
        SHAP values array of shape (N, num_features, num_classes).
    """
    print("\n[FastSHAP] Generating Shapley value estimates...")
    shap_values = fastshap.shap_values(X_test)

    print(f"  Input shape:      {X_test.shape}")
    print(f"  SHAP values shape: {shap_values.shape}")
    # shap_values[i, j, k] = contribution of feature j to class k for sample i

    # Inspect top features for first test sample (class 1 = positive class)
    sample_idx = 0
    class_idx = 1
    sv = shap_values[sample_idx, :, class_idx]
    feature_names = [f"feature_{i}" for i in range(NUM_FEATURES)]

    sorted_idx = np.argsort(np.abs(sv))[::-1]
    print(f"\n  Top-5 features for test sample {sample_idx} (class={class_idx}):")
    for rank, fi in enumerate(sorted_idx[:5]):
        print(f"    {rank+1}. {feature_names[fi]:12s}  SHAP={sv[fi]:+.4f}")

    return shap_values


# ─── Utility: Efficiency Check ────────────────────────────────────────────────

def check_efficiency(
    fastshap: FastSHAP,
    original_model_wrapper,
    X_test: np.ndarray,
    shap_values: np.ndarray,
    n_samples: int = 10,
) -> None:
    """
    Verify the efficiency axiom: sum of SHAP values ≈ f(x) - f(null).

    Args:
        fastshap: Trained FastSHAP object.
        original_model_wrapper: Callable original model.
        X_test: Test features.
        shap_values: SHAP values array (N, num_features, num_classes).
        n_samples: Number of samples to check.
    """
    print("\n[Efficiency Check] SHAP sum vs (f(x) - f(null)):")
    # Null prediction (empty input)
    null_input = np.zeros((1, NUM_FEATURES), dtype=np.float32)
    f_null = original_model_wrapper(null_input)[0]  # (num_classes,)

    for i in range(min(n_samples, len(X_test))):
        xi = X_test[i : i + 1]
        f_xi = original_model_wrapper(xi)[0]           # (num_classes,)
        shap_sum = shap_values[i].sum(axis=0)          # (num_classes,)
        target = f_xi - f_null
        print(
            f"  Sample {i:2d} | SHAP sum: {shap_sum} "
            f"| f(x)-f(null): {target} "
            f"| diff: {np.abs(shap_sum - target).max():.4f}"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("FastSHAP Tabular Pipeline Demo")
    print("=" * 60)

    # 1. Prepare data
    print("\n[Data] Generating synthetic classification dataset...")
    X_train, X_val, X_test, y_train, y_val, y_test = prepare_data()
    print(f"  Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # 2. Train original model
    print("\n[OriginalModel] Training black-box model...")
    original_model = train_original_model(X_train, y_train)
    wrapper = NumpyModelWrapper(original_model, DEVICE)

    # Sanity-check original model
    test_preds = wrapper(X_test[:5])
    print(f"  Sample predictions (probabilities): {test_preds}")

    # 3. Train surrogate
    surr = train_surrogate(wrapper, X_train, X_val)

    # 4. Train FastSHAP explainer
    fastshap = train_fastshap_explainer(surr, X_train, X_val, wrapper)

    # 5. Generate explanations
    shap_values = generate_and_inspect_shap_values(fastshap, X_test)

    # 6. Efficiency check
    check_efficiency(fastshap, wrapper, X_test, shap_values, n_samples=5)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

### `scripts/02_normalization_and_utils_demo.py`

```python
#!/usr/bin/env python3
"""
FastSHAP Normalization & Utilities Demo
========================================
Demonstrates the low-level normalization functions and utility helpers
provided by FastSHAP:

  - additive_efficient_normalization
  - multiplicative_efficient_normalization
  - evaluate_explainer
  - MarginalImputer and BaselineImputer usage
  - Surrogate.generate_labels helper

These are the building blocks used internally by FastSHAP.train() and
can be useful when building custom
```

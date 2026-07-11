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

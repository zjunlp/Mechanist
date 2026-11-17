#!/usr/bin/env python3
"""
SHAP Usage Examples: Explaining Machine Learning Model Predictions

Demonstrates the core SHAP API including TreeExplainer, KernelExplainer,
the unified Explainer, and various visualization helpers.

Requires:
    pip install shap xgboost scikit-learn matplotlib
"""

import numpy as np
import shap
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
import sklearn.svm


# ---------------------------------------------------------------------------
# 1. Tree Ensemble with the Unified Explainer (recommended)
# ---------------------------------------------------------------------------

def tree_explainer_xgboost_example():
    """
    Demonstrates the unified shap.Explainer on an XGBoost regression model
    using the built-in California housing dataset.
    """
    try:
        import xgboost
    except ImportError:
        print("xgboost not installed. Skipping XGBoost example.")
        return

    print("=== Tree Explainer (XGBoost) ===")

    # Load built-in dataset
    X, y = shap.datasets.california()
    print(f"Dataset shape: {X.shape}")

    # Train model
    model = xgboost.XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Create explainer and compute SHAP values
    explainer = shap.Explainer(model)
    shap_values = explainer(X[:100])  # Explain first 100 samples for speed

    print(f"SHAP values shape: {shap_values.values.shape}")
    print(f"Base value (expected output): {shap_values.base_values[0]:.4f}")
    print(f"SHAP values for first instance:\n{shap_values[0].values}")

    # --- Waterfall plot for a single prediction ---
    print("\nGenerating waterfall plot for instance 0...")
    shap.plots.waterfall(shap_values[0], show=False)

    # --- Beeswarm plot (global feature importance) ---
    print("Generating beeswarm plot...")
    shap.plots.beeswarm(shap_values, show=False)

    # --- Bar plot (mean absolute SHAP) ---
    print("Generating bar plot...")
    shap.plots.bar(shap_values, show=False)

    # --- Scatter plot for a single feature ---
    print("Generating scatter plot for 'MedInc'...")
    shap.plots.scatter(shap_values[:, "MedInc"], color=shap_values, show=False)

    print("Tree (XGBoost) example complete.\n")


# ---------------------------------------------------------------------------
# 2. TreeExplainer directly (scikit-learn Random Forest)
# ---------------------------------------------------------------------------

def tree_explainer_sklearn_example():
    """
    Demonstrates shap.TreeExplainer on a scikit-learn RandomForestClassifier
    and computes SHAP interaction values.
    """
    print("=== TreeExplainer (scikit-learn RandomForest) ===")

    X, y = shap.datasets.iris()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)

    # Direct TreeExplainer usage
    explainer = shap.TreeExplainer(model)

    # shap_values returns a list of arrays (one per class) for classifiers
    shap_values = explainer.shap_values(X_test)
    print(f"Number of output classes: {len(shap_values)}")
    print(f"SHAP values shape per class: {shap_values[0].shape}")
    print(f"Expected value per class: {explainer.expected_value}")

    # SHAP interaction values (pairwise)
    print("Computing SHAP interaction values...")
    interaction_values = explainer.shap_interaction_values(X_test[:10])
    print(f"Interaction values shape: {interaction_values[0].shape}")
    # Shape is (n_samples, n_features, n_features) per class

    print("TreeExplainer (sklearn) example complete.\n")


# ---------------------------------------------------------------------------
# 3. KernelExplainer (model-agnostic)
# ---------------------------------------------------------------------------

def kernel_explainer_example():
    """
    Demonstrates shap.KernelExplainer on a scikit-learn SVM.
    KernelExplainer works with any model that exposes a predict function.
    """
    print("=== KernelExplainer (SVM, model-agnostic) ===")

    X, y = shap.datasets.iris()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=0
    )

    # Train an SVM with probability estimates
    svm = sklearn.svm.SVC(kernel='rbf', probability=True)
    svm.fit(X_train, y_train)

    # KernelExplainer requires a predict function and background data
    # Use a small summary of training data as background for efficiency
    background = shap.sample(X_train, 50)  # 50 background samples
    explainer = shap.KernelExplainer(svm.predict_proba, background, link="logit")

    # Compute SHAP values for test set (use few nsamples for speed)
    shap_values = explainer.shap_values(X_test, nsamples=100)

    print(f"Number of output classes: {len(shap_values)}")
    print(f"SHAP values shape (class 0): {shap_values[0].shape}")
    print(f"Expected value (class 0): {explainer.expected_value[0]:.4f}")
    print(f"SHAP values for first test instance (class 0): {shap_values[0][0]}")

    # Force plot for first instance, first class (Setosa)
    print("\nGenerating force plot for test instance 0, class Setosa...")
    shap.force_plot(
        explainer.expected_value[0],
        shap_values[0][0, :],
        X_test.iloc[0, :],
        link="logit",
        show=False,
        matplotlib=True
    )

    print("KernelExplainer example complete.\n")


# ---------------------------------------------------------------------------
# 4. Explanation object: slicing and introspection
# ---------------------------------------------------------------------------

def explanation_object_example():
    """
    Demonstrates how to work with the shap.Explanation object,
    including slicing by instance and feature.
    """
    print("=== Explanation Object Introspection ===")

    X, y = shap.datasets.california()
    X_small = X[:200]

    try:
        import xgboost
        model = xgboost.XGBRegressor(n_estimators=50, random_state=42).fit(X_small, y[:200])
    except ImportError:
        model = GradientBoostingRegressor(n_estimators=50, random_state=42).fit(X_small, y[:200])

    explainer = shap.Explainer(model)
    shap_values = explainer(X_small)

    # The Explanation object supports numpy-style indexing
    first_instance = shap_values[0]
    print(f"Type: {type(shap_values)}")
    print(f"Full values shape: {shap_values.values.shape}")
    print(f"Base values shape: {shap_values.base_values.shape}")
    print(f"Data (feature values) shape: {shap_values.data.shape}")
    print(f"Feature names: {shap_values.feature_names}")

    # Slice by feature name
    medinc_shap = shap_values[:, "MedInc"]
    print(f"\nSHAP values for 'MedInc' feature only, shape: {medinc_shap.values.shape}")

    # Absolute mean importance
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    feature_importance = sorted(
        zip(shap_values.feature_names, mean_abs),
        key=lambda x: x[1],
        reverse=True
    )
    print("\nFeature importances (mean |SHAP|):")
    for feat, imp in feature_importance:
        print(f"  {feat:20s}: {imp:.4f}")

    print("Explanation object example complete.\n")


# ---------------------------------------------------------------------------
# 5. Using built-in datasets
# ---------------------------------------------------------------------------

def datasets_example():
    """
    Demonstrates the built-in datasets available in shap.datasets.
    """
    print("=== Built-in Datasets ===")

    X_cal, y_cal = shap.datasets.california()
    print(f"California housing: X={X_cal.shape}, y={y_cal.shape}")

    X_iris, y_iris = shap.datasets.iris()
    print(f"Iris: X={X_iris.shape}, y={y_iris.shape}")

    X_adult, y_adult = shap.datasets.adult()
    print(f"Adult census: X={X_adult.shape}, y={y_adult.shape}")

    print("Datasets example complete.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SHAP Library Usage Examples\n" + "=" * 40)

    datasets_example()
    tree_explainer_sklearn_example()
    kernel_explainer_example()
    explanation_object_example()

    # XGBoost example last (optional dependency)
    tree_explainer_xgboost_example()

    print("All examples complete.")

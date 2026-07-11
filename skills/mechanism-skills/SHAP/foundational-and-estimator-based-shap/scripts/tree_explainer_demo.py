#!/usr/bin/env python3
"""
SHAP TreeExplainer Demo: Explaining XGBoost Regression Predictions

This script demonstrates how to use SHAP's TreeExplainer (via the unified
shap.Explainer interface) to explain an XGBoost regression model trained on
the California housing dataset.

Covers:
    - Training an XGBoost model
    - Computing SHAP values with shap.Explainer (auto TreeExplainer)
    - Waterfall plot for a single prediction
    - Beeswarm plot for global feature importance
    - Bar plot of mean |SHAP| values
    - Scatter/dependence plot for a single feature
    - SHAP interaction values

Requirements:
    pip install shap xgboost matplotlib
"""

import numpy as np
import shap
import xgboost


def load_data():
    """
    Load the California housing dataset provided by SHAP.

    Returns:
        tuple: (X, y) where X is a pandas DataFrame of features and
               y is a pandas Series of target values (median house prices).
    """
    X, y = shap.datasets.california()
    print(f"Dataset shape: X={X.shape}, y={y.shape}")
    print(f"Features: {list(X.columns)}")
    return X, y


def train_model(X: "pd.DataFrame", y: "pd.Series") -> xgboost.XGBRegressor:
    """
    Train an XGBoost regression model on the provided data.

    Args:
        X: Feature DataFrame.
        y: Target Series.

    Returns:
        Trained XGBRegressor model.
    """
    model = xgboost.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    print(f"Model trained. Training RMSE approx: "
          f"{np.sqrt(np.mean((model.predict(X) - y) ** 2)):.4f}")
    return model


def compute_shap_values(model: xgboost.XGBRegressor, X: "pd.DataFrame") -> shap.Explanation:
    """
    Compute SHAP values for all samples using the unified Explainer interface,
    which automatically selects TreeExplainer for XGBoost models.

    Args:
        model: Trained XGBRegressor.
        X: Feature DataFrame to explain.

    Returns:
        shap.Explanation object with .values, .base_values, and .data attributes.
    """
    explainer = shap.Explainer(model)
    print(f"Explainer type selected: {type(explainer).__name__}")
    shap_values = explainer(X)
    print(f"SHAP values shape: {shap_values.values.shape}")
    print(f"Base value (expected model output): {shap_values.base_values[0]:.4f}")
    return shap_values


def demonstrate_waterfall(shap_values: shap.Explanation, sample_index: int = 0) -> None:
    """
    Display a waterfall plot explaining a single prediction.

    The waterfall plot shows how each feature pushes the model output
    from the base value (average prediction) to the final prediction.

    Args:
        shap_values: SHAP Explanation object.
        sample_index: Index of the sample to visualize.
    """
    print(f"\n--- Waterfall Plot (Sample {sample_index}) ---")
    print(f"  Prediction: {shap_values.base_values[sample_index] + shap_values.values[sample_index].sum():.4f}")
    print(f"  Base value: {shap_values.base_values[sample_index]:.4f}")
    print(f"  Top contributing features:")
    feature_names = shap_values.feature_names
    sv = shap_values.values[sample_index]
    sorted_idx = np.argsort(np.abs(sv))[::-1]
    for i in sorted_idx[:5]:
        print(f"    {feature_names[i]:<20} SHAP={sv[i]:+.4f}  value={shap_values.data[sample_index, i]:.4f}")

    # Render the plot (requires matplotlib display or saves to file)
    try:
        import matplotlib.pyplot as plt
        shap.plots.waterfall(shap_values[sample_index], show=False)
        plt.tight_layout()
        plt.savefig("waterfall_plot.png", dpi=120, bbox_inches="tight")
        plt.close()
        print("  Saved waterfall_plot.png")
    except Exception as e:
        print(f"  Could not save waterfall plot: {e}")


def demonstrate_beeswarm(shap_values: shap.Explanation) -> None:
    """
    Display a beeswarm plot summarizing global feature importance.

    Each dot represents one sample. The x-axis is the SHAP value (impact),
    color encodes the actual feature value (red=high, blue=low).

    Args:
        shap_values: SHAP Explanation object for all samples.
    """
    print("\n--- Beeswarm Plot (Global Feature Importance) ---")
    # Compute mean |SHAP| per feature
    mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
    feature_names = shap_values.feature_names
    sorted_idx = np.argsort(mean_abs_shap)[::-1]
    print("  Feature ranking by mean |SHAP|:")
    for rank, i in enumerate(sorted_idx):
        print(f"  {rank + 1:2d}. {feature_names[i]:<20} mean|SHAP|={mean_abs_shap[i]:.4f}")

    try:
        import matplotlib.pyplot as plt
        shap.plots.beeswarm(shap_values, show=False)
        plt.tight_layout()
        plt.savefig("beeswarm_plot.png", dpi=120, bbox_inches="tight")
        plt.close()
        print("  Saved beeswarm_plot.png")
    except Exception as e:
        print(f"  Could not save beeswarm plot: {e}")


def demonstrate_bar_plot(shap_values: shap.Explanation) -> None:
    """
    Display a bar chart of mean absolute SHAP values (global importance).

    Args:
        shap_values: SHAP Explanation object for all samples.
    """
    print("\n--- Bar Plot (Mean |SHAP| Values) ---")
    try:
        import matplotlib.pyplot as plt
        shap.plots.bar(shap_values, show=False)
        plt.tight_layout()
        plt.savefig("bar_plot.png", dpi=120, bbox_inches="tight")
        plt.close()
        print("  Saved bar_plot.png")
    except Exception as e:
        print(f"  Could not save bar plot: {e}")


def demonstrate_scatter(shap_values: shap.Explanation, feature: str = "Latitude") -> None:
    """
    Display a dependence scatter plot for a single feature.

    Shows how SHAP values for `feature` change with its actual value.
    Color is automatically selected to reveal interaction effects.

    Args:
        shap_values: SHAP Explanation object.
        feature: Name of the feature to plot.
    """
    print(f"\n--- Scatter/Dependence Plot (Feature: {feature}) ---")
    try:
        import matplotlib.pyplot as plt
        shap.plots.scatter(shap_values[:, feature], color=shap_values, show=False)
        plt.tight_layout()
        plt.savefig(f"scatter_{feature.lower()}.png", dpi=120, bbox_inches="tight")
        plt.close()
        print(f"  Saved scatter_{feature.lower()}.png")
    except Exception as e:
        print(f"  Could not save scatter plot: {e}")


def demonstrate_interaction_values(
    model: xgboost.XGBRegressor,
    X: "pd.DataFrame",
    n_samples: int = 200,
) -> None:
    """
    Compute and summarize SHAP interaction values using TreeExplainer directly.

    Interaction values are a matrix per prediction:
      - Diagonal entries: main effects
      - Off-diagonal entries: pairwise interaction effects

    Args:
        model: Trained XGBRegressor.
        X: Feature DataFrame.
        n_samples: Number of samples to use (interaction values are slower to compute).
    """
    print(f"\n--- SHAP Interaction Values (first {n_samples} samples) ---")
    X_sub = X.iloc[:n_samples]
    explainer = shap.TreeExplainer(model)
    interaction_values = explainer.shap_interaction_values(X_sub)
    # Shape: (n_samples, n_features, n_features)
    print(f"  Interaction values shape: {interaction_values.shape}")

    # Mean absolute interaction matrix
    mean_abs_interaction = np.abs(interaction_values).mean(axis=0)
    feature_names = list(X.columns)
    n_features = len(feature_names)

    # Find top-5 off-diagonal interactions
    interactions = []
    for i in range(n_features):
        for j in range(i + 1, n_features):
            interactions.append((mean_abs_interaction[i, j], feature_names[i], feature_names[j]))
    interactions.sort(reverse=True)

    print("  Top 5 feature interaction pairs (mean |interaction SHAP|):")
    for val, feat_i, feat_j in interactions[:5]:
        print(f"    {feat_i} × {feat_j}: {val:.4f}")


def demonstrate_force_plot(
    shap_values: shap.Explanation,
    sample_index: int = 0,
) -> None:
    """
    Demonstrate the force plot for a single prediction.

    Note: Interactive JS force plots require shap.initjs() in a Jupyter notebook.
    This function prints a text summary of the explanation instead.

    Args:
        shap_values: SHAP Explanation object.
        sample_index: Index of the sample to explain.
    """
    print(f"\n--- Force Plot Summary (Sample {sample_index}) ---")
    feature_names = shap_values.feature_names
    sv = shap_values.values[sample_index]
    base = shap_values.base_values[sample_index]
    prediction = base + sv.sum()

    positive_features = [(sv[i], feature_names[i], shap_values.data[sample_index, i])
                         for i in range(len(sv)) if sv[i] > 0]
    negative_features = [(sv[i], feature_names[i], shap_values.data[sample_index, i])
                         for i in range(len(sv)) if sv[i] < 0]
    positive_features.sort(reverse=True)
    negative_features.sort()

    print(f"  Base value:  {base:.4f}")
    print(f"  Prediction:  {prediction:.4f}")
    print(f"  Features pushing prediction HIGHER (positive SHAP):")
    for val, name, feat_val in positive_features[:3]:
        print(f"    {name:<20} = {feat_val:.4f}  → SHAP={val:+.4f}")
    print(f"  Features pushing prediction LOWER (negative SHAP):")
    for val, name, feat_val in negative_features[:3]:
        print(f"    {name:<20} = {feat_val:.4f}  → SHAP={val:+.4f}")


def main():
    """
    Main entry point: runs all TreeExplainer demonstrations end-to-end.
    """
    print("=" * 60)
    print("SHAP TreeExplainer Demo: XGBoost on California Housing")
    print("=" * 60)

    # 1. Load data
    X, y = load_data()

    # 2. Train model
    model = train_model(X, y)

    # 3. Compute SHAP values (uses TreeExplainer automatically)
    shap_values = compute_shap_values(model, X)

    # 4. Single prediction: waterfall
    demonstrate_waterfall(shap_values, sample_index=0)

    # 5. Single prediction: force plot text summary
    demonstrate_force_plot(shap_values, sample_index=0)

    # 6. Global: beeswarm
    demonstrate_beeswarm(shap_values)

    # 7. Global: bar chart
    demonstrate_bar_plot(shap_values)

    # 8. Dependence: scatter
    demonstrate_scatter(shap_values, feature="Latitude")

    # 9. Interaction values
    demonstrate_interaction_values(model, X, n_samples=200)

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

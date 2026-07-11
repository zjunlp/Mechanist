---
name: shap
description: Use this skill when working with SHAP (SHapley Additive exPlanations) to explain machine learning model predictions, compute feature importance, generate SHAP values for tree ensembles (XGBoost, LightGBM, CatBoost, scikit-learn), deep learning models (TensorFlow, Keras, PyTorch), NLP transformers, or any model-agnostic function. Activate when tasks involve model interpretability, explainability, feature attribution, visualization of SHAP values, or understanding why a model made a specific prediction.
---

# SHAP – SHapley Additive exPlanations

## When to Use

Activate this skill when any of the following apply:

- **Model Explainability**: A user wants to understand why a model made a specific prediction
- **Feature Importance**: Computing global or local feature importance for any ML model
- **Tree Ensembles**: Explaining XGBoost, LightGBM, CatBoost, scikit-learn, or PySpark tree models with the fast TreeExplainer
- **Deep Learning**: Explaining TensorFlow, Keras, or PyTorch neural networks with DeepExplainer or GradientExplainer
- **NLP Models**: Explaining Hugging Face Transformers text classification or other NLP pipelines
- **Model-Agnostic Explanations**: Using KernelExplainer for any black-box model (SVMs, random forests, custom functions)
- **Visualization**: Generating waterfall plots, force plots, beeswarm plots, bar charts, scatter/dependence plots, or text explanations
- **SHAP Interaction Values**: Computing pairwise interaction effects between features
- **Audit / Fairness**: Investigating which features drive predictions for regulatory or fairness purposes

**Keywords that trigger this skill**: shap, shapley, explainability, interpretability, feature importance, model explanation, waterfall plot, beeswarm, force plot, TreeExplainer, KernelExplainer, DeepExplainer, GradientExplainer, SHAP values, model attribution, local explanation, global explanation.

---

## Quick Reference

| Resource | URL |
|---|---|
| PyPI Package | https://pypi.org/project/shap/ |
| Conda-Forge | https://anaconda.org/conda-forge/shap |
| Documentation | https://shap.readthedocs.io/en/latest/ |
| GitHub Repository | https://github.com/shap/shap |
| Binder (Interactive Notebooks) | https://mybinder.org/v2/gh/shap/shap/master |
| Nature MI Paper (Tree SHAP) | https://rdcu.be/b0z70 |
| Nature BME Paper (Force Plots) | https://rdcu.be/baVbR |
| Sample Notebooks | https://github.com/shap/shap/tree/master/notebooks |

---

## Installation / Setup

### Standard Installation

```bash
pip install shap
```

or via conda:

```bash
conda install -c conda-forge shap
```

### GPU-Accelerated Tree SHAP (CUDA)

To enable GPU-accelerated Tree SHAP, install from source with the CUDA toolkit available:

```bash
SHAP_ENABLE_CUDA=1 pip install .
```

**Requirements:**
- [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit) must be installed on the system
- Build from source (clone the repository first)

### Python Version Support

SHAP follows [SPEC 0](https://scientific-python.org/specs/spec-0000/) for minimum supported dependency versions. Check the current supported Python and NumPy/Pandas versions on the SPEC 0 page.

### Optional Dependencies by Use Case

| Use Case | Additional Packages |
|---|---|
| XGBoost models | `pip install xgboost` |
| LightGBM models | `pip install lightgbm` |
| CatBoost models | `pip install catboost` |
| TensorFlow/Keras (DeepExplainer) | `pip install tensorflow` |
| PyTorch (GradientExplainer) | `pip install torch` |
| Hugging Face Transformers | `pip install transformers` |
| PySpark models | Apache Spark environment |
| Visualization (notebooks) | `pip install matplotlib jupyter` |

---

## Core Features

- **TreeExplainer**: Fast, exact SHAP values for tree-based models (XGBoost, LightGBM, CatBoost, scikit-learn ensembles, PySpark). Uses the Tree SHAP algorithm (O(TLD²) complexity). Supports SHAP interaction values.
- **KernelExplainer**: Model-agnostic explainer using a specially-weighted local linear regression. Works with any function that accepts a numpy array and returns predictions.
- **DeepExplainer**: High-speed approximation for deep learning models (TensorFlow/Keras). Based on DeepLIFT with Shapley equations to linearize activations.
- **GradientExplainer**: Expected gradients explainer for TensorFlow, Keras, and PyTorch models. Combines Integrated Gradients, SHAP, and SmoothGrad.
- **Explainer (Auto)**: Unified entry point that automatically selects the best explainer for the provided model type.
- **SHAP Interaction Values**: Generalization of SHAP values to pairwise interactions via `shap_interaction_values()` on TreeExplainer.
- **Visualization Suite**:
  - `shap.plots.waterfall` – single prediction explanation
  - `shap.plots.force` – force plot for one or many predictions
  - `shap.plots.beeswarm` – global feature importance distribution
  - `shap.plots.bar` – mean absolute SHAP value bar chart
  - `shap.plots.scatter` – dependence/scatter plot for a single feature
  - `shap.plots.text` – NLP text highlight visualization
  - `shap.image_plot` – image pixel attribution visualization
- **Datasets**: Built-in sample datasets (`california`, `iris`, `imagenet50`, `adult`, `nhanes`) for quick experimentation.
- **Serialization**: Save and load Explanation objects and Explainers via the `Serializable` base class.

---

## Usage Examples

### 1. Tree Ensemble Example (XGBoost / LightGBM / CatBoost / scikit-learn)

```python
import xgboost
import shap

# Train an XGBoost model
X, y = shap.datasets.california()
model = xgboost.XGBRegressor().fit(X, y)

# Explain the model's predictions using SHAP
# (same syntax works for LightGBM, CatBoost, scikit-learn, transformers, Spark, etc.)
explainer = shap.Explainer(model)
shap_values = explainer(X)

# Visualize the first prediction's explanation
shap.plots.waterfall(shap_values[0])
```

```python
# Visualize the first prediction's explanation with a force plot
shap.plots.force(shap_values[0])
```

```python
# Visualize all the training set predictions (first 500)
shap.plots.force(shap_values[:500])
```

```python
# Create a dependence scatter plot to show the effect of a single feature across the whole dataset
shap.plots.scatter(shap_values[:, "Latitude"], color=shap_values)
```

```python
# Summarize the effects of all the features (beeswarm plot)
shap.plots.beeswarm(shap_values)
```

```python
# Bar chart of mean absolute SHAP values (stacked bars for multi-class)
shap.plots.bar(shap_values)
```

### 2. Natural Language (Hugging Face Transformers)

```python
import transformers
import shap

# Load a transformers pipeline model
model = transformers.pipeline('sentiment-analysis', top_k=None)

# Explain the model on two sample inputs
explainer = shap.Explainer(model)
shap_values = explainer(["What a great movie! ...if you have no taste."])

# Visualize the first prediction's explanation for the POSITIVE output class
shap.plots.text(shap_values[0, :, "POSITIVE"])
```

### 3. Deep Learning with DeepExplainer (TensorFlow/Keras)

```python
import shap
import numpy as np

# Select a set of background examples to take an expectation over
background = x_train[np.random.choice(x_train.shape[0], 100, replace=False)]

# Explain predictions of the model on four images
e = shap.DeepExplainer(model, background)
# ...or pass tensors directly
# e = shap.DeepExplainer((model.layers[0].input, model.layers[-1].output), background)
shap_values = e.shap_values(x_test[1:5])

# Plot the feature attributions
shap.image_plot(shap_values, -x_test[1:5])
```

### 4. Deep Learning with GradientExplainer (TensorFlow/Keras/PyTorch)

```python
from keras.applications.vgg16 import VGG16
from keras.applications.vgg16 import preprocess_input
import keras.backend as K
import numpy as np
import json
import shap

# Load pre-trained model and choose two images to explain
model = VGG16(weights='imagenet', include_top=True)
X, y = shap.datasets.imagenet50()
to_explain = X[[39, 41]]

# Load the ImageNet class names
url = "https://s3.amazonaws.com/deep-learning-models/image-models/imagenet_class_index.json"
fname = shap.datasets.cache(url)
with open(fname) as f:
    class_names = json.load(f)

# Explain how the input to the 7th layer of the model explains the top two classes
def map2layer(x, layer):
    feed_dict = dict(zip([model.layers[0].input], [preprocess_input(x.copy())]))
    return K.get_session().run(model.layers[layer].input, feed_dict)

e = shap.GradientExplainer(
    (model.layers[7].input, model.layers[-1].output),
    map2layer(X, 7),
    local_smoothing=0  # std dev of smoothing noise
)
shap_values, indexes = e.shap_values(map2layer(to_explain, 7), ranked_outputs=2)

# Get the names for the classes
index_names = np.vectorize(lambda x: class_names[str(x)][1])(indexes)

# Plot the explanations
shap.image_plot(shap_values, to_explain, index_names)
```

### 5. Model-Agnostic with KernelExplainer (Any Function)

```python
import sklearn
import shap
from sklearn.model_selection import train_test_split

# Print the JS visualization code to the notebook
shap.initjs()

# Train a SVM classifier
X_train, X_test, Y_train, Y_test = train_test_split(
    *shap.datasets.iris(), test_size=0.2, random_state=0
)
svm = sklearn.svm.SVC(kernel='rbf', probability=True)
svm.fit(X_train, Y_train)

# Use Kernel SHAP to explain test set predictions
explainer = shap.KernelExplainer(svm.predict_proba, X_train, link="logit")
shap_values = explainer.shap_values(X_test, nsamples=100)

# Plot the SHAP values for the Setosa output of the first instance
shap.force_plot(
    explainer.expected_value[0],
    shap_values[0][0, :],
    X_test.iloc[0, :],
    link="logit"
)
```

```python
# Plot the SHAP values for the Setosa output of all instances
shap.force_plot(
    explainer.expected_value[0],
    shap_values[0],
    X_test,
    link="logit"
)
```

### 6. SHAP Interaction Values (TreeExplainer)

```python
import shap
import xgboost

X, y = shap.datasets.california()
model = xgboost.XGBRegressor().fit(X, y)

# Compute SHAP interaction values
explainer = shap.TreeExplainer(model)
shap_interaction_values = explainer.shap_interaction_values(X)
# Returns shape: (n_samples, n_features, n_features)
# Diagonal = main effects, off-diagonal = interaction effects
```

---

## Key APIs / Models

### Explainer Classes

| Class | Best For | Algorithm |
|---|---|---|
| `shap.Explainer` | Auto-selects best explainer | Automatic dispatch |
| `shap.TreeExplainer` | XGBoost, LightGBM, CatBoost, sklearn trees | Tree SHAP (exact, O(TLD²)) |
| `shap.KernelExplainer` | Any model / black-box function | Weighted linear regression |
| `shap.DeepExplainer` | TensorFlow, Keras neural nets | DeepLIFT + Shapley equations |
| `shap.GradientExplainer` | TF, Keras, PyTorch | Expected Gradients |
| `shap.LinearExplainer` | Linear models | Exact for linear models |
| `shap.PermutationExplainer` | Any model, slower but unbiased | Permutation-based |
| `shap.SamplingExplainer` | Large datasets, any model | Sampling approximation |

### Visualization Functions

| Function | Description |
|---|---|
| `shap.plots.waterfall(shap_values[i])` | Single prediction breakdown |
| `shap.plots.force(shap_values)` | Force plot (one or many samples) |
| `shap.plots.beeswarm(shap_values)` | Global feature impact distribution |
| `shap.plots.bar(shap_values)` | Mean absolute SHAP bar chart |
| `shap.plots.scatter(shap_values[:, feature])` | Dependence scatter plot |
| `shap.plots.text(shap_values)` | NLP token-level attribution |
| `shap.image_plot(shap_values, X)` | Image pixel attribution |
| `shap.plots.heatmap(shap_values)` | Heatmap of SHAP values |
| `shap.force_plot(...)` | Legacy force plot (JS-interactive) |
| `shap.summary_plot(shap_values, X)` | Legacy summary/beeswarm |
| `shap.dependence_plot(feature, shap_values, X)` | Legacy dependence plot |

### Built-in Datasets

| Function | Description |
|---|---|
| `shap.datasets.california()` | California housing dataset `(X, y)` |
| `shap.datasets.iris()` | Iris classification dataset `(X, y)` |
| `shap.datasets.imagenet50()` | 50 ImageNet images `(X, y)` |
| `shap.datasets.adult()` | Adult income dataset `(X, y)` |
| `shap.datasets.nhanes()` | NHANES survival dataset |
| `shap.datasets.cache(url)` | Download and cache a file by URL |

### Core Data Structure

| Class | Description |
|---|---|
| `shap.Explanation` | Primary output object holding `.values`, `.base_values`, `.data`, `.feature_names` |

---

## Common Patterns & Best Practices

### Choosing the Right Explainer

1. **Use `shap.Explainer(model)` first** – it auto-detects the model type and selects the optimal algorithm. Override only if you need fine-grained control.
2. **Tree models**: Always prefer `TreeExplainer` for speed. It is exact and runs in polynomial time.
3. **Neural networks with image/tabular data**: Use `DeepExplainer` for speed or `GradientExplainer` for intermediate-layer explanations.
4. **Arbitrary functions**: Use `KernelExplainer` but expect it to be slow for many samples. Reduce with `nsamples` parameter.

### Background Data Selection

- `TreeExplainer`: Pass training data summary (`shap.kmeans(X_train, 100)`) or the full training set.
- `KernelExplainer`: Pass a representative background sample (e.g., `X_train.sample(100)`).
- `DeepExplainer`: Use 100-200 random background samples from training data.

```python
# Summarize background data efficiently
background = shap.kmeans(X_train, 50)
explainer = shap.KernelExplainer(model.predict, background)
```

### Slicing Explanation Objects

`shap.Explanation` supports NumPy-style slicing:

```python
# First 100 samples
shap_values[:100]

# Specific feature by name
shap_values[:, "Latitude"]

# Specific output class (multi-output)
shap_values[:, :, "POSITIVE"]

# Single prediction
shap_values[0]
```

### Saving / Loading Explanations

```python
# Save
import pickle
with open("shap_values.pkl", "wb") as f:
    pickle.dump(shap_values, f)

# Load
with open("shap_values.pkl", "rb") as f:
    shap_values = pickle.load(f)
```

### Notebook Initialization (Legacy JS Plots)

```python
shap.initjs()  # Required before using shap.force_plot() in Jupyter notebooks
```

### Multi-Class Models

```python
# shap_values.values has shape (n_samples, n_features, n_classes) for multi-class
# Use index into last dimension for class-specific plots
shap.plots.beeswarm(shap_values[:, :, 0])   # Class 0
shap.plots.bar(shap_values[:, :, "label"])  # By name if feature_names set
```

### Interaction Values Interpretation

```python
# shap_interaction_values[i, j, k]:
# - j == k: main effect of feature j on sample i
# - j != k: interaction effect between features j and k on sample i
# Sum over axis 1 or 2 recovers regular SHAP values (minus duplicates on diagonal)
```

## Demo Scripts

### `scripts/kernel_explainer_demo.py`

```python
#!/usr/bin/env python3
"""
SHAP KernelExplainer Demo: Model-Agnostic Explanations for Any Classifier

This script demonstrates how to use SHAP's KernelExplainer to explain
predictions of any model — in this case, a Support Vector Machine (SVM)
trained on the classic Iris dataset. KernelExplainer works with any function
that maps input features to predictions, making it fully model-agnostic.

Covers:
    - Training an S
```

### `scripts/shap_usage_example.py`

```python
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
```

### `scripts/tree_explainer_demo.py`

```python
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
```

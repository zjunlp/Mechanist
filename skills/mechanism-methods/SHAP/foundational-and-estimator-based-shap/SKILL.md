---
name: shap
description: "Use this skill when working with SHAP (SHapley Additive exPlanations) to explain machine learning model predictions, compute feature importance, generate SHAP values for tree ensembles (XGBoost, LightGBM, CatBoost, scikit-learn), deep learning models (TensorFlow, Keras, PyTorch), NLP transformers, or any model-agnostic function. Activate when tasks involve model interpretability, explainability, feature attribution, visualization of SHAP values, or understanding why a model made a specific prediction."
---

## Method and use

Choose TreeSHAP, model-agnostic KernelSHAP, or a suitable estimator for input-feature attribution. Define the background and feature-removal semantics; dependent features complicate interpretation. Local additive accounting is not automatically a causal explanation of internal computation.


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


See [`scripts/kernel_explainer_demo.py`](scripts/kernel_explainer_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/shap_usage_example.py`


See [`scripts/shap_usage_example.py`](scripts/shap_usage_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/tree_explainer_demo.py`


See [`scripts/tree_explainer_demo.py`](scripts/tree_explainer_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

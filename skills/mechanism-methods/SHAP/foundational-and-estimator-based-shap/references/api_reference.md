# SHAP API Reference

## Module: `shap`

---

## Top-Level Explainers

### `shap.Explainer`

Unified explainer that automatically selects the best algorithm for the given model.

**Constructor:**
```python
shap.Explainer(
    model,
    masker=None,
    link=identity,
    algorithm="auto",
    output_names=None,
    feature_names=None,
    **kwargs
)
```

**Parameters:**
- `model`: The ML model or prediction function to explain.
- `masker`: A masker object or data array used to mask out features (background dataset).
- `link`: A monotonic transform applied to the model output (e.g., `shap.links.logit`).
- `algorithm` (str): `"auto"`, `"permutation"`, `"partition"`, `"tree"`, `"kernel"`, `"sampling"`, `"linear"`, `"deep"`, `"gradient"`.
- `output_names` (list, optional): Names for model output classes.
- `feature_names` (list, optional): Feature names.

**Returns:** An `Explainer` instance callable as `explainer(X)`.

**Call signature:**
```python
explainer(X, max_evals=None, main_effects=False, error_bounds=False, batch_size="auto", **kwargs) -> Explanation
```

**Example:**
```python
explainer = shap.Explainer(model)
shap_values = explainer(X)
```

---

### `shap.TreeExplainer`

Exact and fast SHAP values for tree-based models using the TreeSHAP algorithm.

**Constructor:**
```python
shap.TreeExplainer(
    model,
    data=None,
    model_output="raw",
    feature_perturbation="interventional",
    **kwargs
)
```

**Parameters:**
- `model`: A tree ensemble model. Supported: XGBoost, LightGBM, CatBoost, scikit-learn trees/ensembles, pyspark.
- `data` (array-like, optional): Background dataset for interventional feature perturbation.
- `model_output` (str): `"raw"`, `"probability"`, `"log_loss"`.
- `feature_perturbation` (str): `"interventional"` (default) or `"tree_path_dependent"`.

**Key Methods:**

#### `shap_values(X, y=None, tree_limit=None, approximate=False, check_additivity=True) -> np.ndarray`
Compute SHAP values for input X.
- `X`: Input data (array-like or DataFrame).
- Returns: ndarray of shape `(n_samples, n_features)` for regression; list of such arrays for multi-class.

#### `shap_interaction_values(X, y=None, tree_limit=None) -> np.ndarray`
Compute SHAP interaction values (pairwise).
- Returns: ndarray of shape `(n_samples, n_features, n_features)` for regression; list for multi-class.
- Diagonal entries are main effects; off-diagonal are interaction effects.

**Attributes:**
- `expected_value`: Scalar or array. The base value(s) (E[f(x)]).

**Example:**
```python
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
interaction = explainer.shap_interaction_values(X)
print(explainer.expected_value)
```

---

### `shap.KernelExplainer`

Model-agnostic SHAP values via specially-weighted local linear regression (Kernel SHAP).

**Constructor:**
```python
shap.KernelExplainer(
    model,
    data,
    link="identity",
    **kwargs
)
```

**Parameters:**
- `model`: Any callable that takes input data and returns predictions (e.g., `predict_proba`).
- `data`: Background dataset used to integrate out features. Use `shap.sample(X, k)` to limit size.
- `link` (str): `"identity"` (default) or `"logit"`. Logit link is useful for probability outputs.

**Key Methods:**

#### `shap_values(X, nsamples="auto", l1_reg="auto", **kwargs) -> np.ndarray`
Compute SHAP values.
- `X`: Inputs to explain.
- `nsamples` (int or "auto"): Number of coalition samples per explanation. More = more accurate, slower.
- `l1_reg` (str/float): Regularization for sparse explanations (`"auto"`, `"aic"`, `"bic"`, float).
- Returns: ndarray or list of ndarrays for multi-output.

**Attributes:**
- `expected_value`: Scalar or array. The base value(s).

**Example:**
```python
background = shap.sample(X_train, 100)
explainer = shap.KernelExplainer(model.predict_proba, background, link="logit")
shap_values = explainer.shap_values(X_test, nsamples=200)
```

---

### `shap.DeepExplainer`

High-speed approximation of SHAP values for deep learning models, based on DeepLIFT + Shapley equations.

**Constructor:**
```python
shap.DeepExplainer(
    model,
    data,
    **kwargs
)
```

**Parameters:**
- `model`: A TensorFlow/Keras model, or a `(input_tensor, output_tensor)` tuple. Preliminary PyTorch support available.
- `data` (array-like): Background samples (50–200 recommended) to take expectation over.

**Key Methods:**

#### `shap_values(X, ranked_outputs=None, output_rank_order="max", check_additivity=True) -> list`
Compute approximate SHAP values.
- `X`: Input data to explain.
- `ranked_outputs` (int, optional): If set, only explain the top-k outputs.
- Returns: List of ndarrays (one per output).

**Example:**
```python
background = x_train[np.random.choice(x_train.shape[0], 100, replace=False)]
e = shap.DeepExplainer(model, background)
shap_values = e.shap_values(x_test[1:5])
shap.image_plot(shap_values, -x_test[1:5])
```

---

### `shap.GradientExplainer`

Expected gradients approach combining Integrated Gradients, SHAP, and SmoothGrad.

**Constructor:**
```python
shap.GradientExplainer(
    model,
    data,
    local_smoothing=0,
    **kwargs
)
```

**Parameters:**
- `model`: TF/Keras model or `(input_tensor, output_tensor)` tuple. PyTorch models also supported.
- `data`: Background dataset (can be entire training set, unlike DeepExplainer).
- `local_smoothing` (float): Std dev of Gaussian smoothing noise (0 = no smoothing).

**Key Methods:**

#### `shap_values(X, ranked_outputs=None, output_rank_order="max", rseed=None) -> tuple`
Compute approximate SHAP values via expected gradients.
- Returns: `(shap_values, indexes)` where `indexes` are the output indices explained.

**Example:**
```python
e = shap.GradientExplainer(
    (model.layers[7].input, model.layers[-1].output),
    map2layer(X, 7),
    local_smoothing=0
)
shap_values, indexes = e.shap_values(map2layer(to_explain, 7), ranked_outputs=2)
```

---

### `shap.LinearExplainer`

Exact SHAP values for linear models.

**Constructor:**
```python
shap.LinearExplainer(
    model,
    masker,
    link=identity,
    **kwargs
)
```

**Parameters:**
- `model`: A linear model (e.g., `sklearn.linear_model.LinearRegression`).
- `masker`: Background data or a `shap.maskers.Independent` masker.

---

## Core Data Structure

### `shap.Explanation`

A sliceable set of parallel arrays representing SHAP explanations.

**Attributes:**
- `values` (np.ndarray): SHAP values. Shape: `(n_samples, n_features)` or `(n_samples, n_features, n_outputs)`.
- `base_values` (np.ndarray): Base/expected model output. Shape: `(n_samples,)`.
- `data` (np.ndarray): Input feature values. Shape: `(n_samples, n_features)`.
- `feature_names` (list): Feature names.
- `output_names` (list): Output/class names.
- `display_data`: Optional human-readable feature values for display.

**Indexing:**
```python
shap_values[i]               # Explanation for instance i
shap_values[:, "feature"]    # Explanation for all instances, one feature
shap_values[:100]            # First 100 instances
shap_values[i, j]            # Instance i, feature j
```

**Source:** `shap/_explanation.py`

---

## Plot Functions

### `shap.plots.waterfall(shap_values, max_display=10, show=True)`
Waterfall chart for a single prediction explanation.
- `shap_values`: A single `Explanation` instance (e.g., `shap_values[0]`).
- `max_display` (int): Maximum number of features to show.

### `shap.plots.force(base_value_or_explanation, shap_values=None, features=None, feature_names=None, link="identity", matplotlib=False, show=True)`
Force plot for one or many predictions.
- Can accept a single `Explanation` or legacy `(base_value, shap_values, features)` signature.
- `matplotlib` (bool): Use matplotlib backend (required outside Jupyter).

### `shap.plots.beeswarm(shap_values, max_display=10, order=Explanation.abs.mean(0), show=True)`
Beeswarm plot showing distribution of SHAP impacts for all features.
- `shap_values`: Full `Explanation` object.
- `max_display` (int): Maximum features to display.

### `shap.plots.bar(shap_values, max_display=10, order=Explanation.abs.mean(0), show=True)`
Bar chart of mean absolute SHAP values.
- Produces stacked bars for multi-class outputs.

### `shap.plots.scatter(shap_values, color=None, hist=True, axis_color="#333333", show=True)`
Scatter/dependence plot for a single feature across all samples.
- `shap_values`: Feature-sliced `Explanation`, e.g., `shap_values[:, "MedInc"]`.
- `color`: Another `Explanation` or array for coloring points.

### `shap.plots.text(shap_values, num_starting_labels=0, group_threshold=1, separator="", xmin=None, xmax=None, cmax=None, display=True)`
Text visualization for NLP model explanations.
- `shap_values`: Sliced `Explanation` for a single output class.

### `shap.image_plot(shap_values, pixel_values=None, labels=None, true_labels=None, width=20, aspect=0.2, hspace=0.2, labelpad=None, show=True)`
Image plot for vision model explanations.
- `shap_values`: List of ndarrays from `DeepExplainer.shap_values`.
- `pixel_values`: Input images to display as background.

### `shap.force_plot(base_value, shap_values, features=None, feature_names=None, out_names=None, link="identity", plot_cmap="RdBu", matplotlib=False, show=True, **kwargs)`
Legacy force plot function (wraps `shap.plots.force`).

---

## Utility Functions

### `shap.sample(X, nsamples=100, random_state=0) -> np.ndarray`
Randomly sample rows from X for use as background data.
- `X`: Input data array or DataFrame.
- `nsamples` (int): Number of rows to sample.
- Returns sampled data as numpy array.

### `shap.initjs()`
Load JavaScript visualization code in a Jupyter notebook (required for interactive force plots).

### `shap.datasets.california() -> (DataFrame, Series)`
Load the California housing dataset.

### `shap.datasets.iris() -> (DataFrame, Series)`
Load the Iris classification dataset.

### `shap.datasets.adult() -> (DataFrame, Series)`
Load the Adult census income dataset.

### `shap.datasets.imagenet50() -> (np.ndarray, np.ndarray)`
Load 50 ImageNet sample images.

### `shap.datasets.cache(url) -> str`
Download and cache a file, returning the local path.

---

## Maskers

### `shap.maskers.Independent(data, max_samples=100)`
Masker for independent (uncorrelated) features. Used with `KernelExplainer` and `LinearExplainer`.

### `shap.maskers.Partition(data, max_samples=100, clustering="correlation")`
Masker using hierarchical partitioning of features. Used internally by `Explainer` for NLP/text.

### `shap.maskers.Text(tokenizer=None, mask_token=None, collapse_mask_token="auto")`
Masker for text/NLP models (Hugging Face tokenizer).

### `shap.maskers.Image(mask_value, shape=None)`
Masker for image models.

---

## Serialization

### `shap.Serializable` (base class)
Base class for serializable SHAP objects.

### `shap.Serializer(out_stream, model_id, version)`
Save SHAP objects to a stream.

### `shap.Deserializer(in_stream, model_id, version)`
Load SHAP objects from a stream.

---

## Links

### `shap.links.identity`
Identity link function (default). `f(x) = x`

### `shap.links.logit`
Logit link function. `f(x) = log(x / (1 - x))`. Use with probability outputs.

---

## Supported Model Types by Explainer

| Model/Framework | Recommended Explainer |
|---|---|
| XGBoost | `TreeExplainer` / `Explainer` |
| LightGBM | `TreeExplainer` / `Explainer` |
| CatBoost | `TreeExplainer` / `Explainer` |
| scikit-learn trees/forests/boosting | `TreeExplainer` / `Explainer` |
| PySpark ML trees | `TreeExplainer` |
| TensorFlow / Keras | `DeepExplainer` / `GradientExplainer` |
| PyTorch | `GradientExplainer` (preliminary `DeepExplainer`) |
| Hugging Face Transformers | `Explainer` (Partition-based) |
| Linear models (sklearn) | `LinearExplainer` / `Explainer` |
| Any callable model | `KernelExplainer` |

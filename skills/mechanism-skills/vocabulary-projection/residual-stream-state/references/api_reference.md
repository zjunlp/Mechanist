# Tuned Lens API Reference

## Core Module: `tuned_lens`

### Class: `TunedLens`

Main class for creating and managing tuned lenses for transformer models.

**Constructor:**
```python
TunedLens(
    model: torch.nn.Module,
    layers: Optional[List[int]] = None,
    device: str = "cuda"
)
```

**Parameters:**
- `model` (torch.nn.Module): The transformer model to create a lens for
- `layers` (List[int], optional): Specific layers to create translators for. If None, creates for all layers
- `device` (str): Device to place the lens on ("cuda" or "cpu")

**Methods:**

#### `train(dataset: Dataset, **kwargs) -> Dict[str, float]`
Train the tuned lens on a dataset.

**Parameters:**
- `dataset` (Dataset): Training dataset
- `learning_rate` (float): Learning rate for optimization
- `batch_size` (int): Batch size for training
- `n_epochs` (int): Number of training epochs
- `temperature` (float): Temperature for KL divergence

**Returns:**
- `Dict[str, float]`: Training metrics including loss values

#### `forward(hidden_states: torch.Tensor, layer_idx: int) -> torch.Tensor`
Apply the tuned lens at a specific layer.

**Parameters:**
- `hidden_states` (torch.Tensor): Hidden states from the model
- `layer_idx` (int): Index of the layer to apply lens at

**Returns:**
- `torch.Tensor`: Predicted logits

#### `save(path: str) -> None`
Save the tuned lens to disk.

**Parameters:**
- `path` (str): Path to save the lens

#### `load(path: str, model: torch.nn.Module) -> TunedLens`
Load a saved tuned lens.

**Parameters:**
- `path` (str): Path to load the lens from
- `model` (torch.nn.Module): Model to attach the lens to

**Returns:**
- `TunedLens`: Loaded lens object

---

### Class: `PredictionTrajectory`

Represents the evolution of predictions through transformer layers.

**Constructor:**
```python
PredictionTrajectory(
    model: torch.nn.Module,
    lens: TunedLens,
    input_ids: torch.Tensor
)
```

**Parameters:**
- `model` (torch.nn.Module): The transformer model
- `lens` (TunedLens): The tuned lens to use
- `input_ids` (torch.Tensor): Input token IDs

**Attributes:**
- `layer_predictions` (List[torch.Tensor]): Predictions at each layer
- `final_prediction` (torch.Tensor): Final model prediction
- `tokens` (List[str]): Decoded input tokens

**Methods:**

#### `get_top_k_at_layer(layer_idx: int, k: int = 5) -> List[Tuple[str, float]]`
Get top-k predictions at a specific layer.

**Parameters:**
- `layer_idx` (int): Layer index
- `k` (int): Number of top predictions

**Returns:**
- `List[Tuple[str, float]]`: List of (token, probability) pairs

#### `compute_entropy(layer_idx: int) -> float`
Compute entropy of predictions at a layer.

**Parameters:**
- `layer_idx` (int): Layer index

**Returns:**
- `float`: Entropy value

#### `plot(tokens_to_track: Optional[List[str]] = None) -> matplotlib.figure.Figure`
Create a visualization of the prediction trajectory.

**Parameters:**
- `tokens_to_track` (List[str], optional): Specific tokens to highlight

**Returns:**
- `matplotlib.figure.Figure`: The plot figure

---

### Class: `AffineTranslator`

Implements an affine transformation for mapping hidden states to logits.

**Constructor:**
```python
AffineTranslator(
    input_dim: int,
    output_dim: int,
    bias: bool = True
)
```

**Parameters:**
- `input_dim` (int): Dimension of input hidden states
- `output_dim` (int): Dimension of output (vocabulary size)
- `bias` (bool): Whether to include bias term

**Methods:**

#### `forward(x: torch.Tensor) -> torch.Tensor`
Apply the affine transformation.

**Parameters:**
- `x` (torch.Tensor): Input hidden states

**Returns:**
- `torch.Tensor`: Output logits

---

## Module: `tuned_lens.data`

### Function: `load_text_dataset`
```python
load_text_dataset(
    name: str,
    split: str = "train",
    tokenizer: Optional[Tokenizer] = None,
    max_length: int = 512
) -> Dataset
```

Load and prepare a text dataset for lens training.

**Parameters:**
- `name` (str): Dataset name or path
- `split` (str): Dataset split to load
- `tokenizer` (Tokenizer, optional): Tokenizer to use
- `max_length` (int): Maximum sequence length

**Returns:**
- `Dataset`: Prepared dataset

---

## Module: `tuned_lens.evaluation`

### Function: `evaluate_lens`
```python
evaluate_lens(
    lens: TunedLens,
    dataset: Dataset,
    metrics: List[str] = ["kl_divergence", "accuracy"]
) -> Dict[str, float]
```

Evaluate a tuned lens on a dataset.

**Parameters:**
- `lens` (TunedLens): The lens to evaluate
- `dataset` (Dataset): Evaluation dataset
- `metrics` (List[str]): Metrics to compute

**Returns:**
- `Dict[str, float]`: Computed metric values

### Function: `compute_kl_divergence`
```python
compute_kl_divergence(
    pred_logits: torch.Tensor,
    target_logits: torch.Tensor,
    temperature: float = 1.0
) -> torch.Tensor
```

Compute KL divergence between predicted and target distributions.

**Parameters:**
- `pred_logits` (torch.Tensor): Predicted logits
- `target_logits` (torch.Tensor): Target logits
- `temperature` (float): Temperature for softmax

**Returns:**
- `torch.Tensor`: KL divergence value

---

## Module: `tuned_lens.visualization`

### Function: `plot_prediction_heatmap`
```python
plot_prediction_heatmap(
    trajectory: PredictionTrajectory,
    vocab_subset: Optional[List[str]] = None
) -> matplotlib.figure.Figure
```

Create a heatmap showing prediction probabilities across layers.

**Parameters:**
- `trajectory` (PredictionTrajectory): Prediction trajectory
- `vocab_subset` (List[str], optional): Subset of vocabulary to display

**Returns:**
- `matplotlib.figure.Figure`: Heatmap figure

### Function: `plot_entropy_evolution`
```python
plot_entropy_evolution(
    trajectories: List[PredictionTrajectory],
    labels: Optional[List[str]] = None
) -> matplotlib.figure.Figure
```

Plot how prediction entropy evolves through layers.

**Parameters:**
- `trajectories` (List[PredictionTrajectory]): List of trajectories
- `labels` (List[str], optional): Labels for each trajectory

**Returns:**
- `matplotlib.figure.Figure`: Entropy plot

---

## Module: `tuned_lens.stats`

### Class: `LayerStats`

Statistics for predictions at a specific layer.

**Attributes:**
- `layer_idx` (int): Layer index
- `mean_entropy` (float): Mean entropy across tokens
- `mean_confidence` (float): Mean top-1 probability
- `perplexity` (float): Perplexity of predictions

**Methods:**

#### `compute_from_logits(logits: torch.Tensor) -> LayerStats`
Compute statistics from logits.

**Parameters:**
- `logits` (torch.Tensor): Logits to compute stats from

**Returns:**
- `LayerStats`: Computed statistics

---

## Module: `tuned_lens.model_surgery`

### Function: `extract_hidden_states`
```python
extract_hidden_states(
    model: torch.nn.Module,
    input_ids: torch.Tensor,
    layers: Optional[List[int]] = None
) -> Dict[int, torch.Tensor]
```

Extract hidden states from specified layers of a model.

**Parameters:**
- `model` (torch.nn.Module): The model to extract from
- `input_ids` (torch.Tensor): Input token IDs
- `layers` (List[int], optional): Layers to extract from

**Returns:**
- `Dict[int, torch.Tensor]`: Mapping from layer index to hidden states

### Function: `get_unembedding_matrix`
```python
get_unembedding_matrix(
    model: torch.nn.Module
) -> torch.Tensor
```

Extract the unembedding matrix from a model.

**Parameters:**
- `model` (torch.nn.Module): The model

**Returns:**
- `torch.Tensor`: Unembedding weight matrix

---

## CLI Commands

### `tuned-lens train`
Train a tuned lens for a model.

**Usage:**
```bash
tuned-lens train \
    --model MODEL_NAME \
    --dataset DATASET_NAME \
    --output OUTPUT_PATH \
    --batch-size BATCH_SIZE \
    --learning-rate LR \
    --n-epochs EPOCHS
```

**Arguments:**
- `--model`: HuggingFace model name or path
- `--dataset`: Dataset name or path
- `--output`: Path to save trained lens
- `--batch-size`: Training batch size (default: 8)
- `--learning-rate`: Learning rate (default: 1e-3)
- `--n-epochs`: Number of training epochs (default: 10)

### `tuned-lens eval`
Evaluate a trained lens.

**Usage:**
```bash
tuned-lens eval \
    --model MODEL_NAME \
    --lens LENS_PATH \
    --dataset DATASET_NAME \
    --metrics METRICS
```

**Arguments:**
- `--model`: Model name or path
- `--lens`: Path to trained lens
- `--dataset`: Evaluation dataset
- `--metrics`: Comma-separated list of metrics

### `tuned-lens analyze`
Analyze text using a tuned lens.

**Usage:**
```bash
tuned-lens analyze \
    --model MODEL_NAME \
    --lens LENS_PATH \
    --text "INPUT TEXT" \
    --output OUTPUT_PATH
```

**Arguments:**
- `--model`: Model name or path
- `--lens`: Path to trained lens
- `--text`: Text to analyze
- `--output`: Path to save analysis results

---

## Integration with TransformerLens

The tuned lens library provides integration with TransformerLens for advanced mechanistic interpretability research.

### Function: `to_transformer_lens`
```python
to_transformer_lens(
    lens: TunedLens,
    model: HookedTransformer
) -> HookedTunedLens
```

Convert a tuned lens to work with TransformerLens models.

**Parameters:**
- `lens` (TunedLens): The tuned lens
- `model` (HookedTransformer): TransformerLens model

**Returns:**
- `HookedTunedLens`: Lens compatible with TransformerLens

---

## Utilities

### Function: `load_pretrained_lens`
```python
load_pretrained_lens(
    model_name: str,
    revision: str = "main"
) -> TunedLens
```

Load a pre-trained lens from the Hugging Face Hub.

**Parameters:**
- `model_name` (str): Model name
- `revision` (str): Model revision

**Returns:**
- `TunedLens`: Loaded lens

### Function: `batch_process`
```python
batch_process(
    lens: TunedLens,
    texts: List[str],
    batch_size: int = 32
) -> List[PredictionTrajectory]
```

Process multiple texts in batches.

**Parameters:**
- `lens` (TunedLens): The lens to use
- `texts` (List[str]): List of texts
- `batch_size` (int): Batch size for processing

**Returns:**
- `List[PredictionTrajectory]`: Trajectories for all texts

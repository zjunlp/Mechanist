# Transcoder Circuits API Reference

## Overview

The repository is organized into two main library packages:
- `sae_training/` — Training and model code for transcoders and SAEs
- `transcoder_circuits/` — Circuit analysis, dashboards, and replacement context tools

---

## Module: `sae_training`

### Class: `ActivationsStore`
**File:** `sae_training/activations_store.py`

Streams tokens from a dataset and generates/stores LLM activations for use during SAE/transcoder training.

**Constructor:**
```python
ActivationsStore(cfg: LanguageModelSAERunnerConfig, model: HookedTransformer)
```

**Parameters:**
- `cfg` (`LanguageModelSAERunnerConfig`): Training configuration specifying model, hook point, batch size, etc.
- `model` (`HookedTransformer`): The loaded TransformerLens model to extract activations from.

**Key Methods:**

#### `get_batch_tokens() -> torch.Tensor`
Returns a batch of tokenized text from the dataset.

**Returns:** `torch.Tensor` of shape `(batch_size, context_size)`

#### `get_activations(batch_tokens: torch.Tensor) -> torch.Tensor`
Run the model on a batch of tokens and extract activations at the configured hook point.

**Parameters:**
- `batch_tokens` (`torch.Tensor`): Token IDs of shape `(batch, seq)`

**Returns:** `torch.Tensor` of shape `(batch, seq, d_in)`

#### `get_buffer(n_batches_in_buffer: int) -> torch.Tensor`
Fill and return an activation buffer of size `n_batches_in_buffer * batch_size`.

**Parameters:**
- `n_batches_in_buffer` (`int`): Number of batches to buffer

**Returns:** `torch.Tensor` of shape `(buffer_size, d_in)`

---

### Class: `RunnerConfig`
**File:** `sae_training/config.py`

Base configuration dataclass shared across all training runners.

```python
@dataclass
class RunnerConfig:
    device: str = "cpu"
    seed: int = 42
    dtype: str = "float32"
    checkpoint_path: str = "checkpoints"
```

**Fields:**
- `device` (`str`): PyTorch device string (`"cpu"`, `"cuda"`, `"cuda:0"`)
- `seed` (`int`): Random seed for reproducibility
- `dtype` (`str`): Floating point dtype (`"float32"`, `"float16"`, `"bfloat16"`)
- `checkpoint_path` (`str`): Directory to save model checkpoints

---

### Class: `LanguageModelSAERunnerConfig`
**File:** `sae_training/config.py`

Full configuration for training a transcoder or SAE on a language model. Extends `RunnerConfig`.

```python
@dataclass
class LanguageModelSAERunnerConfig(RunnerConfig):
    # Model
    model_name: str = "gpt2"
    hook_point: str = "blocks.0.hook_mlp_out"
    hook_point_layer: int = 0
    d_in: int = 768

    # Architecture
    expansion_factor: int = 4

    # Training
    lr: float = 2e-4
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    l1_coefficient: float = 8e-4
    lr_scheduler_name: str = "constant"
    train_batch_size: int = 4096
    context_size: int = 128
    total_training_tokens: int = 1_000_000

    # Data
    dataset_path: str = "NeelNanda/pile-10k"

    # Checkpointing
    n_checkpoints: int = 10

    # Logging
    log_to_wandb: bool = True
    wandb_project: str = "mats_sae_training"
    wandb_entity: Optional[str] = None
    wandb_log_frequency: int = 10
```

**Key Fields:**
- `model_name` (`str`): HuggingFace model identifier (e.g., `"gpt2"`, `"EleutherAI/pythia-410m"`)
- `hook_point` (`str`): TransformerLens hook name to extract activations from (e.g., `"blocks.0.hook_mlp_out"`)
- `hook_point_layer` (`int`): Integer layer index corresponding to `hook_point`
- `d_in` (`int`): Dimensionality of input activations (= model's d_model for MLP output hooks)
- `expansion_factor` (`int`): `d_hidden = d_in * expansion_factor`
- `l1_coefficient` (`float`): Sparsity penalty weight; higher = sparser features
- `total_training_tokens` (`int`): Total token budget for training

---

### Class: `CacheActivationsRunnerConfig`
**File:** `sae_training/config.py`

Configuration for pre-caching LLM activations to disk before training.

```python
@dataclass
class CacheActivationsRunnerConfig(RunnerConfig):
    model_name: str = "gpt2"
    hook_point: str = "blocks.0.hook_mlp_out"
    hook_point_layer: int = 0
    d_in: int = 768
    dataset_path: str = "NeelNanda/pile-10k"
    total_training_tokens: int = 1_000_000
    context_size: int = 128
    train_batch_size: int = 4096
    cache_every_n_tokens: int = 100_000
    cache_path: str = "activations_cache"
```

**Fields:**
- `cache_path` (`str`): Directory to write cached activation `.pt` files
- `cache_every_n_tokens` (`int`): How frequently to flush the cache buffer to disk

---

### Class: `SparseAutoencoder` (Transcoder)
**File:** `sae_training/sparse_autoencoder.py`

The main transcoder/SAE model class. Implements an encoder-decoder with a ReLU sparsity bottleneck.

**Constructor:**
```python
SparseAutoencoder(cfg: LanguageModelSAERunnerConfig)
```

**Forward method:**
```python
def forward(x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]
```

**Parameters:**
- `x` (`torch.Tensor`): Input activations of shape `(batch, d_in)`

**Returns:** Tuple of:
1. `feature_activations` (`torch.Tensor`): Sparse feature activations, shape `(batch, d_hidden)`
2. `reconstruction` (`torch.Tensor`): Reconstructed output, shape `(batch, d_in)` (or `d_out` for transcoders)
3. `loss` (`torch.Tensor`): Total loss (reconstruction + L1)
4. `reconstruction_loss` (`torch.Tensor`): MSE reconstruction loss
5. `l1_loss` (`torch.Tensor`): L1 sparsity loss

**Key Attributes:**
- `cfg`: The `LanguageModelSAERunnerConfig` used to create this model
- `W_enc` (`nn.Parameter`): Encoder weight matrix, shape `(d_in, d_hidden)`
- `W_dec` (`nn.Parameter`): Decoder weight matrix, shape `(d_hidden, d_in)`
- `b_enc` (`nn.Parameter`): Encoder bias, shape `(d_hidden,)`
- `b_dec` (`nn.Parameter`): Decoder bias, shape `(d_in,)` or `(d_out,)`

---

### Function: `language_model_sae_runner`
**File:** `sae_training/train_sae_on_language_model.py`

Main entry point for training a transcoder or SAE.

```python
def language_model_sae_runner(cfg: LanguageModelSAERunnerConfig) -> SparseAutoencoder
```

**Parameters:**
- `cfg` (`LanguageModelSAERunnerConfig`): Full training configuration

**Returns:**
- `SparseAutoencoder`: Trained transcoder model

**Example:**
```python
from sae_training.config import LanguageModelSAERunnerConfig
from sae_training.train_sae_on_language_model import language_model_sae_runner

cfg = LanguageModelSAERunnerConfig(
    model_name="gpt2",
    hook_point="blocks.0.hook_mlp_out",
    hook_point_layer=0,
    d_in=768,
)
transcoder = language_model_sae_runner(cfg)
```

---

## Module: `transcoder_circuits`

### Module: `transcoder_circuits.replacement_ctx`
**File:** `transcoder_circuits/replacement_ctx.py`

Provides a context manager for replacing model MLP sublayers with transcoder reconstructions during inference.

#### Class: `TranscoderReplacementContext`

```python
TranscoderReplacementContext(
    model: HookedTransformer,
    transcoders: Dict[int, SparseAutoencoder],
    use_error_term: bool = True
)
```

**Parameters:**
- `model` (`HookedTransformer`): The TransformerLens model to patch
- `transcoders` (`Dict[int, SparseAutoencoder]`): Mapping from layer index to transcoder
- `use_error_term` (`bool`): If True, add reconstruction error back to preserve fidelity

**Usage (context manager):**
```python
from transcoder_circuits.replacement_ctx import TranscoderReplacementContext

with TranscoderReplacementContext(model, {0: tc_0, 1: tc_1}):
    logits = model(tokens)
# Model hooks are automatically removed after the context exits
```

---

### Module: `transcoder_circuits.circuit_analysis`
**File:** `transcoder_circuits/circuit_analysis.py`

Tools for computing feature-level circuit attributions and scores.

#### Function: `get_circuit_scores`

```python
def get_circuit_scores(
    model: HookedTransformer,
    transcoders: Dict[int, SparseAutoencoder],
    tokens: torch.Tensor,
    metric_fn: Callable,
    layers: Optional[List[int]] = None,
) -> Dict
```

**Parameters:**
- `model` (`HookedTransformer`): Loaded language model
- `transcoders` (`Dict[int, SparseAutoencoder]`): Layer → transcoder mapping
- `tokens` (`torch.Tensor`): Input token IDs, shape `(batch, seq)`
- `metric_fn` (`Callable`): Function mapping logits → scalar score to differentiate
- `layers` (`List[int]`, optional): Which layers to analyze; defaults to all transcoder layers

**Returns:**
- `dict`: Maps layer indices to feature attribution score tensors

**Example:**
```python
from transcoder_circuits.circuit_analysis import get_circuit_scores

def logit_diff_metric(logits):
    return logits[0, -1, correct_token] - logits[0, -1, incorrect_token]

scores = get_circuit_scores(model, transcoders, tokens, logit_diff_metric)
```

---

### Module: `transcoder_circuits.feature_dashboards`
**File:** `transcoder_circuits/feature_dashboards.py`

Generate rich feature dashboards for exploring transcoder features.

#### Function: `make_feature_dashboard`

```python
def make_feature_dashboard(
    transcoder: SparseAutoencoder,
    model: HookedTransformer,
    feature_idx: int,
    dataset,
    n_examples: int = 20,
    context_size: int = 128,
) -> dict
```

**Parameters:**
- `transcoder` (`SparseAutoencoder`): Trained transcoder to analyze
- `model` (`HookedTransformer`): Corresponding language model
- `feature_idx` (`int`): Which feature (0-indexed) to visualize
- `dataset`: HuggingFace dataset or iterable of text strings
- `n_examples` (`int`): Number of max-activating examples to show
- `context_size` (`int`): Token context window size

**Returns:**
- `dict`: Dashboard data including:
  - `"max_activating_examples"`: List of tokenized contexts with highlighted activations
  - `"feature_direction"`: The decoder weight vector for the feature
  - `"top_logits"`: Tokens most promoted/suppressed by this feature
  - `"activation_histogram"`: Distribution of feature activation magnitudes

**Example:**
```python
from transcoder_circuits.feature_dashboards import make_feature_dashboard
from datasets import load_dataset

dataset = load_dataset("NeelNanda/pile-10k", split="train")
dashboard = make_feature_dashboard(
    transcoder=transcoder,
    model=model,
    feature_idx=42,
    dataset=dataset,
    n_examples=30,
)
```

---

## Module: `sae_training.geom_median`

### Function: `compute_geometric_median`
**File:** `sae_training/geom_median/src/geom_median/numpy/main.py`

Compute the geometric median of a set of points using the Weiszfeld algorithm.

```python
def compute_geometric_median(
    points: np.ndarray,
    weights: Optional[np.ndarray] = None,
    per_component: bool = False,
    eps: float = 1e-5,
    maxiter: int = 100,
    ftol: float = 1e-20,
) -> GeometricMedianOutput
```

**Parameters:**
- `points` (`np.ndarray`): Array of shape `(n, d)` — the input points
- `weights` (`np.ndarray`, optional): Non-negative weights of shape `(n,)`; defaults to uniform
- `per_component` (`bool`): If True, compute median per coordinate independently
- `eps` (`float`): Small value to avoid division by zero in Weiszfeld iterations
- `maxiter` (`int`): Maximum number of Weiszfeld iterations
- `ftol` (`float`): Convergence tolerance on function value

**Returns:**
- `GeometricMedianOutput`: Named tuple with fields:
  - `median` (`np.ndarray`): The geometric median point, shape `(d,)`
  - `new_weights` (`np.ndarray`): Final Weiszfeld weights
  - `termination` (`str`): Reason for stopping (`"convergence"` or `"maximum_iterations"`)

**Example:**
```python
import numpy as np
from sae_training.geom_median.src.geom_median.numpy.main import compute_geometric_median

points = np.random.randn(100, 768)  # 100 d_model-dimensional points
result = compute_geometric_median(points)
print(result.median.shape)  # (768,)
print(result.termination)   # "convergence"
```

---

## Supported Models

| Model | d_model | Hook Point Pattern |
|---|---|---|
| `gpt2` | 768 | `blocks.{layer}.hook_mlp_out` |
| `gpt2-medium` | 1024 | `blocks.{layer}.hook_mlp_out` |
| `gpt2-large` | 1280 | `blocks.{layer}.hook_mlp_out` |
| `EleutherAI/pythia-410m` | 1024 | `blocks.{layer}.hook_mlp_out` |

## Pretrained Weights

| Source | Location |
|---|---|
| HuggingFace Hub | `pchlenski/gpt2-transcoders` |
| Local (after setup.sh) | `./transcoder_weights/` |

Each file corresponds to one layer: `gpt2-small_layer{N}_transcoder.pt`

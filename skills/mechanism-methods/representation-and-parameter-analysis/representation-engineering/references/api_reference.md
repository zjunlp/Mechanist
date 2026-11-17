# Representation Engineering (RepE) API Reference

## Package: `repe`

Source: `repe/` (installed via `pip install -e .`)

---

## Function: `repe_pipeline_registry`

```python
from repe import repe_pipeline_registry
repe_pipeline_registry()
```

Registers the `"rep-reading"` and `"rep-control"` task names into the HuggingFace pipeline registry. Must be called before using `pipeline("rep-reading", ...)` or `pipeline("rep-control", ...)`.

**Parameters:** None

**Returns:** None (side effect: registers pipelines globally)

**Example:**
```python
from repe import repe_pipeline_registry
repe_pipeline_registry()
from transformers import pipeline
rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)
```

---

## Pipeline: `"rep-reading"`

Inherits from HuggingFace `Pipeline`. Extracts and classifies internal representations of a language model using linear probes.

### Initialization

```python
rep_reading_pipeline = pipeline(
    "rep-reading",
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
)
```

**Parameters:**
- `model` (PreTrainedModel): A HuggingFace causal language model.
- `tokenizer` (PreTrainedTokenizer): Corresponding tokenizer.

---

### Method: `get_directions`

```python
rep_reader = rep_reading_pipeline.get_directions(
    train_inputs: List[str],
    rep_token: int = -1,
    hidden_layers: List[int] = None,
    n_difference: int = 1,
    train_labels: List[int] = None,
    direction_method: str = "pca",
    direction_kwargs: dict = {},
)
```

Trains a RepReader by finding the principal direction of variation between positive/negative representation pairs.

**Parameters:**
- `train_inputs` (List[str]): Flattened list of prompts. Contrastive pairs should be interleaved or paired as expected by `n_difference`.
- `rep_token` (int): Token index to extract representation from. `-1` = last token. Default: `-1`.
- `hidden_layers` (List[int]): List of layer indices (can be negative). E.g., `[-1, -3, -5, ...]`. Default: all layers.
- `n_difference` (int): Number of contrastive differences per direction. Default: `1`.
- `train_labels` (List[int]): Integer labels (e.g., `1` for positive, `0` for negative concept). Length must match `train_inputs`.
- `direction_method` (str): Method for direction finding. Options: `"pca"`, `"cluster_mean"`. Default: `"pca"`.
- `direction_kwargs` (dict): Additional keyword arguments passed to the direction method.

**Returns:**
- `RepReader`: Object containing `directions` (dict mapping layer → direction vector), `direction_signs`, and scoring methods.

---

### Method: `__call__` (scoring)

```python
scores = rep_reading_pipeline(
    inputs: List[str],
    rep_token: int = -1,
    hidden_layers: List[int] = None,
    rep_reader: RepReader = None,
    batch_size: int = 8,
)
```

Scores input texts using a trained RepReader.

**Parameters:**
- `inputs` (List[str]): Input prompts to score.
- `rep_token` (int): Token index to extract from. Default: `-1`.
- `hidden_layers` (List[int]): Layers to score. Must match layers used during training.
- `rep_reader` (RepReader): Trained reader from `get_directions`.
- `batch_size` (int): Batch size for inference. Default: `8`.

**Returns:**
- `List[Dict[int, float]]`: List of dicts mapping layer index → score for each input.

---

## Pipeline: `"rep-control"`

Inherits from HuggingFace `Pipeline`. Steers language model generation by injecting learned representation directions into hidden states.

### Initialization

```python
rep_control_pipeline = pipeline(
    "rep-control",
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    layers: List[int] = None,
    block_name: str = "decoder_block",
    control_method: str = "reading_vec",
    **kwargs,
)
```

**Parameters:**
- `model` (PreTrainedModel): HuggingFace causal LM.
- `tokenizer` (PreTrainedTokenizer): Corresponding tokenizer.
- `layers` (List[int]): Layer indices at which to inject the control vector.
- `block_name` (str): Name of the transformer block to hook into. Default: `"decoder_block"`.
- `control_method` (str): Control injection method. Default: `"reading_vec"`.
- `**kwargs`: Additional pipeline arguments.

---

### Method: `__call__` (controlled generation)

```python
output = rep_control_pipeline(
    inputs: str | List[str],
    activations: Dict[int, torch.Tensor] = None,
    max_new_tokens: int = 100,
    do_sample: bool = False,
    **generate_kwargs,
)
```

Generates text with representation-level control applied.

**Parameters:**
- `inputs` (str | List[str]): Input prompt(s).
- `activations` (Dict[int, torch.Tensor]): Dict mapping layer index → control vector tensor. The vector is added to the hidden state at the specified layer during forward passes.
- `max_new_tokens` (int): Maximum tokens to generate. Default: `100`.
- `do_sample` (bool): Whether to use sampling. Default: `False` (greedy).
- `**generate_kwargs`: Any additional keyword arguments passed to `model.generate()`.

**Returns:**
- `List[Dict]`: List of dicts with key `"generated_text"`.

**Control Coefficient:** Scale the direction vector before passing as `activations` value:
```python
activations = {layer: direction_vector * control_coeff for layer in layers}
```
Positive coefficient steers toward the concept; negative steers away.

---

## Class: `RepReader`

Source: `repe/rep_reading/` (internal class returned by `get_directions`)

Stores representation directions and provides scoring utilities.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `directions` | `Dict[int, np.ndarray]` | Maps layer index → direction vector (shape: `[hidden_size]`) |
| `direction_signs` | `Dict[int, int]` | Sign correction for each layer's direction (`+1` or `-1`) |
| `H_train_means` | `Dict[int, np.ndarray]` | Mean representations per layer used for normalization |

---

## Utility Functions

### `examples/honesty/utils.py`

#### `honesty_function_dataset`

```python
honesty_function_dataset(
    data_path: str,
    tokenizer: PreTrainedTokenizer,
    user_tag: str,
    assistant_tag: str,
    seed: int = 0,
) -> Tuple[Dict, Dict]
```

Builds train/test split of contrastive honest/dishonest statement pairs.

**Parameters:**
- `data_path` (str): Path to `data/facts/facts_true_false.csv`.
- `tokenizer` (PreTrainedTokenizer): Model tokenizer.
- `user_tag` (str): Chat template user prefix (e.g., `"[INST]"`).
- `assistant_tag` (str): Chat template assistant prefix (e.g., `"[/INST]"`).
- `seed` (int): Random seed. Default: `0`.

**Returns:** `Tuple[Dict, Dict]` — each dict has keys `"data"` (List of paired prompts) and `"labels"` (List of paired labels).

---

#### `plot_detection_results`

```python
plot_detection_results(
    input_ids: List,
    rep_reader_scores_dict: Dict[str, List],
    THRESHOLD: float,
) -> None
```

Plots RepReader detection scores per token/layer with a threshold line.

**Parameters:**
- `input_ids` (List): Tokenized input IDs for x-axis labels.
- `rep_reader_scores_dict` (Dict[str, List]): Scores per concept name.
- `THRESHOLD` (float): Decision threshold for visualization.

---

#### `plot_lat_scans`

```python
plot_lat_scans(
    input_ids: List,
    rep_reader_scores_dict: Dict[str, List],
    layer_slice: slice,
) -> None
```

Visualizes LAT (Linear Artificial Tomography) scan heatmaps across layers and token positions.

**Parameters:**
- `input_ids` (List): Token IDs for axis labels.
- `rep_reader_scores_dict` (Dict[str, List]): Scores keyed by concept.
- `layer_slice` (slice): Layer range to visualize.

---

### `examples/primary_emotions/utils.py`

#### `primary_emotions_concept_dataset`

```python
primary_emotions_concept_dataset(
    data_dir: str,
    user_tag: str,
    assistant_tag: str,
) -> Dict[str, List]
```

Loads emotion data and formats as concept-level RepE dataset.

**Parameters:**
- `data_dir` (str): Path to `data/emotions/` directory.
- `user_tag` (str): Chat template user prefix.
- `assistant_tag` (str): Chat template assistant prefix.

**Returns:** Dict mapping emotion name → list of formatted prompt strings.

---

#### `primary_emotions_function_dataset`

```python
primary_emotions_function_dataset(
    data_dir: str,
    user_tag: str,
    assistant_tag: str,
) -> Dict
```

Loads and formats emotion data for function-level RepE (classification/steering).

**Parameters:**
- `data_dir` (str): Path to `data/emotions/` directory.
- `user_tag` (str): Chat template user prefix.
- `assistant_tag` (str): Chat template assistant prefix.

**Returns:** Dict with `"data"` and `"labels"` keys for pipeline consumption.

---

### `examples/memorization/utils.py`

#### `literary_openings_dataset`

```python
literary_openings_dataset(
    data_dir: str,
    ntrain: int,
    seed: int = 0,
) -> Tuple[Dict, Dict]
```

Loads real vs. fake literary opening sentences for memorization RepE experiments.

**Parameters:**
- `data_dir` (str): Path to `data/memorization/literary_openings/`.
- `ntrain` (int): Number of training samples per class.
- `seed` (int): Random seed.

**Returns:** `Tuple[Dict, Dict]` — train and test dicts.

---

#### `quotes_dataset`

```python
quotes_dataset(
    data_dir: str,
    ntrain: int,
    seed: int = 0,
) -> Tuple[Dict, Dict]
```

Loads popular vs. unseen quotes for memorization analysis.

**Parameters:**
- `data_dir` (str): Path to `data/memorization/quotes/`.
- `ntrain` (int): Number of training samples.
- `seed` (int): Random seed.

**Returns:** `Tuple[Dict, Dict]` — train and test dicts.

---

#### `extract_quote_completion`

```python
extract_quote_completion(s: str) -> str
```

Parses model output to extract the completed portion of a quote.

**Parameters:**
- `s` (str): Raw model generation string.

**Returns:** Extracted completion substring.

---

### `examples/fairness/utils.py`

#### `bias_dataset`

```python
bias_dataset(
    ntrain: int,
    user_tag: str,
    assistant_tag: str,
) -> Tuple[Dict, Dict]
```

Builds a dataset of biased vs. unbiased prompts for fairness RepE experiments.

**Parameters:**
- `ntrain` (int): Number of training examples.
- `user_tag` (str): Chat template user prefix.
- `assistant_tag` (str): Chat template assistant prefix.

**Returns:** `Tuple[Dict, Dict]` — train and test dicts.

---

## Class: `LorraArguments` (LoRRA Finetuning)

Source: `lorra_finetune/src/args.py`

Dataclass for LoRRA (representation-aware LoRA) finetuning arguments.

```python
@dataclass
class LorraArguments:
    target_layers: List[int]          # Layers to apply representation loss
    control_template: str             # Template for control prompts
    pos_type: str                     # Positive concept label
    neg_type: str                     # Negative concept label
    rep_loss_coeff: float = 1.0       # Coefficient for representation loss term
    direction_method: str = "pca"     # Direction method for rep loss
```

---

## Class: `LoraArguments`

Source: `lorra_finetune/src/args.py`

Standard LoRA configuration arguments.

```python
@dataclass
class LoraArguments:
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    lora_weight_path: str = ""
    lora_bias: str = "none"
```

---

## Class: `ModelArguments`

Source: `lorra_finetune/src/args.py`

Model path and configuration arguments for finetuning.

```python
@dataclass
class ModelArguments:
    model_name_or_path: str           # HuggingFace model ID or local path
    trust_remote_code: bool = False   # Whether to trust remote code
    padding_side: str = "right"       # Tokenizer padding side
```

---

## Data Files Reference

| Path | Format | Description |
|------|--------|-------------|
| `data/facts/facts_true_false.csv` | CSV | True/false factual statements for honesty experiments |
| `data/emotions/{emotion}.json` | JSON | Emotion-labeled prompt-completion pairs |
| `data/emotions/all_truncated_outputs.json` | JSON | All emotion outputs truncated |
| `data/memorization/quotes/popular_quotes.json` | JSON | Well-known memorized quotes |
| `data/memorization/quotes/unseen_quotes.json` | JSON | Novel/unseen quotes |
| `data/memorization/quotes/quote_completions.json` | JSON | Model completions for quotes |
| `data/memorization/literary_openings/real.json` | JSON | Real literary opening lines |
| `data/memorization/literary_openings/fake.json` | JSON | Fake/synthetic opening lines |

---

## Supported Chat Templates

| Model Family | `user_tag` | `assistant_tag` |
|-------------|------------|-----------------|
| LLaMA-2-chat | `"[INST]"` | `"[/INST]"` |
| Mistral Instruct | `"[INST]"` | `"[/INST]"` |
| LLaMA-3 Instruct | `"<\|start_header_id\|>user<\|end_header_id\|>"` | `"<\|start_header_id\|>assistant<\|end_header_id\|>"` |
| Generic | `"### Human:"` | `"### Assistant:"` |

# ROME Model Editing API Reference

## Module: rome

### Class: ROMEHyperParams

Hyperparameter configuration for Rank-One Model Editing.

**Location:** `rome/rome_hparams.py`

**Constructor:**
```python
ROMEHyperParams(
    layers: List[int],
    fact_token: str = "subject_last",
    v_num_grad_steps: int = 20,
    v_lr: float = 5e-1,
    v_loss_layer: int = 31,
    v_weight_decay: float = 1e-3,
    clamp_norm_factor: float = 4,
    kl_factor: float = 0.0625,
    mom2_adjustment: bool = True,
    mom2_update_weight: int = 5000,
    **kwargs
)
```

**Parameters:**
- `layers` (List[int]): Layer indices to edit
- `fact_token` (str): Token selection strategy ("subject_first", "subject_last", "subject_last_after_last")
- `v_num_grad_steps` (int): Number of optimization steps for v* computation
- `v_lr` (float): Learning rate for v* optimization
- `v_loss_layer` (int): Layer to compute loss at
- `v_weight_decay` (float): Weight decay for v* optimization
- `clamp_norm_factor` (float): Factor for clamping update norm
- `kl_factor` (float): KL divergence penalty weight
- `mom2_adjustment` (bool): Whether to adjust second moment statistics
- `mom2_update_weight` (int): Weight for moment updates

---

### Function: apply_rome_to_model

Apply ROME edits to a model.

**Location:** `rome/rome_main.py`

**Signature:**
```python
def apply_rome_to_model(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    requests: List[Dict],
    hparams: ROMEHyperParams,
    copy: bool = False,
    return_orig_weights: bool = False
) -> Tuple[AutoModelForCausalLM, Dict[str, torch.Tensor]]
```

**Parameters:**
- `model` (AutoModelForCausalLM): Model to edit
- `tok` (AutoTokenizer): Tokenizer for the model
- `requests` (List[Dict]): List of edit requests
- `hparams` (ROMEHyperParams): Hyperparameters for ROME
- `copy` (bool): Whether to copy model before editing
- `return_orig_weights` (bool): Whether to return original weights

**Returns:**
- `Tuple[AutoModelForCausalLM, Dict]`: Edited model and original weights

**Edit Request Format:**
```python
{
    "prompt": str,  # Template with {} for subject
    "subject": str,  # Subject to edit
    "target_new": {
        "str": str  # New target string
    }
}
```

---

## Module: rome.layer_stats

### Function: layer_stats

Compute and cache second-moment statistics for model layers.

**Signature:**
```python
def layer_stats(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    layer_num: int,
    dataset: str = "wikipedia",
    sample_size: int = 100000,
    batch_size: int = 32
) -> Dict[str, torch.Tensor]
```

**Parameters:**
- `model` (AutoModelForCausalLM): Model to analyze
- `tok` (AutoTokenizer): Tokenizer
- `layer_num` (int): Layer index to compute stats for
- `dataset` (str): Dataset for statistics ("wikipedia", "wikitext")
- `sample_size` (int): Number of samples to use
- `batch_size` (int): Batch size for computation

**Returns:**
- `Dict[str, torch.Tensor]`: Statistics including covariance matrices

---

## Module: baselines.ft

### Class: FTHyperParams

Hyperparameters for fine-tuning baseline.

**Location:** `baselines/ft/ft_hparams.py`

**Constructor:**
```python
FTHyperParams(
    layers: List[int],
    num_steps: int = 20,
    lr: float = 5e-5,
    weight_decay: float = 1e-4,
    kl_factor: float = 1.0,
    norm_constraint: float = 1e-4,
    **kwargs
)
```

---

### Function: apply_ft_to_model

Apply fine-tuning edits to a model.

**Location:** `baselines/ft/ft_main.py`

**Signature:**
```python
def apply_ft_to_model(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    requests: List[Dict],
    hparams: FTHyperParams,
    copy: bool = False,
    return_orig_weights: bool = False
) -> Tuple[AutoModelForCausalLM, Dict[str, torch.Tensor]]
```

**Parameters:**
- `model` (AutoModelForCausalLM): Model to fine-tune
- `tok` (AutoTokenizer): Tokenizer
- `requests` (List[Dict]): Edit requests
- `hparams` (FTHyperParams): Fine-tuning hyperparameters
- `copy` (bool): Whether to copy model
- `return_orig_weights` (bool): Return original weights

**Returns:**
- `Tuple[AutoModelForCausalLM, Dict]`: Fine-tuned model and original weights

---

### Function: execute_ft

Execute fine-tuning on model.

**Location:** `baselines/ft/ft_main.py`

**Signature:**
```python
def execute_ft(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    requests: List[Dict],
    hparams: FTHyperParams
) -> AutoModelForCausalLM
```

---

### Class: AverageMeter

Utility class for computing running averages.

**Location:** `baselines/ft/ft_main.py`

**Methods:**
```python
class AverageMeter:
    def __init__(self)
    def reset(self)
    def update(self, val: float, n: int = 1)
    @property
    def avg(self) -> float
```

---

## Module: baselines.kn

### Class: KNHyperParams

Hyperparameters for Knowledge Neurons baseline.

**Location:** `baselines/kn/kn_hparams.py`

**Constructor:**
```python
KNHyperParams(
    layers: List[int],
    fact_token: str = "subject_last",
    suppress_ratio: float = 0.5,
    enhance_ratio: float = 5.0,
    **kwargs
)
```

---

### Function: apply_kn_to_model

Apply Knowledge Neurons edits to a model.

**Location:** `baselines/kn/kn_main.py`

**Signature:**
```python
def apply_kn_to_model(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    request: Dict,
    hparams: KNHyperParams,
    copy: bool = False,
    return_orig_weights: bool = False
) -> Tuple[AutoModelForCausalLM, Dict[str, torch.Tensor]]
```

**Parameters:**
- `model` (AutoModelForCausalLM): Model to edit
- `tok` (AutoTokenizer): Tokenizer
- `request` (Dict): Single edit request
- `hparams` (KNHyperParams): Knowledge Neurons hyperparameters
- `copy` (bool): Whether to copy model
- `return_orig_weights` (bool): Return original weights

**Returns:**
- `Tuple[AutoModelForCausalLM, Dict]`: Edited model and original weights

---

## Module: experiments

### Function: compute_rewrite_quality

Evaluate the quality of model edits.

**Location:** `experiments/eval_utils.py`

**Signature:**
```python
def compute_rewrite_quality(
    model: AutoModelForCausalLM,
    tok: AutoTokenizer,
    record: Dict,
    epsilon: float = 1e-5
) -> Dict[str, float]
```

**Parameters:**
- `model` (AutoModelForCausalLM): Model to evaluate
- `tok` (AutoTokenizer): Tokenizer
- `record` (Dict): Evaluation record from CounterFact
- `epsilon` (float): Small value for numerical stability

**Returns:**
- `Dict[str, float]`: Metrics including efficacy, generalization, specificity

---

### Function: evaluate

Main evaluation function for running experiments.

**Location:** `experiments/evaluate.py`

**Signature:**
```python
def evaluate(
    alg_name: str,
    model_name: str,
    hparams_fname: str,
    dataset_name: str = "counterfact",
    num_records: int = None,
    skip_generation: bool = False,
    save_results: bool = True
) -> Dict
```

**Parameters:**
- `alg_name` (str): Algorithm name (ROME, FT, KN, etc.)
- `model_name` (str): Model identifier
- `hparams_fname` (str): Hyperparameter file name
- `dataset_name` (str): Dataset to evaluate on
- `num_records` (int): Number of records to evaluate
- `skip_generation` (bool): Skip generation metrics
- `save_results` (bool): Save results to disk

**Returns:**
- `Dict`: Evaluation results

---

### Function: summarize

Summarize evaluation results.

**Location:** `experiments/summarize.py`

**Signature:**
```python
def summarize(
    dir_name: str,
    runs: List[str],
    output_path: str = None
) -> Dict[str, Dict[str, float]]
```

**Parameters:**
- `dir_name` (str): Directory containing results
- `runs` (List[str]): Run identifiers to summarize
- `output_path` (str): Optional output path for summary

**Returns:**
- `Dict`: Summary statistics for each metric

---

## Module: util

### Class: HyperParams

Base class for hyperparameter configurations.

**Location:** `util/hparams.py`

**Methods:**
```python
class HyperParams:
    @classmethod
    def from_json(cls, json_path: str) -> HyperParams
    
    def to_json(self, json_path: str) -> None
    
    @classmethod
    def from_dict(cls, d: Dict) -> HyperParams
    
    def to_dict(self) -> Dict
```

---

### Function: chunks

Split an array into chunks.

**Location:** `baselines/ft/ft_main.py`

**Signature:**
```python
def chunks(arr: List, n: int) -> Iterator[List]
```

**Parameters:**
- `arr` (List): Array to split
- `n` (int): Chunk size

**Yields:**
- `List`: Chunks of size n

---

### Function: initialize_model_and_tokenizer

Initialize a model and tokenizer.

**Location:** `baselines/kn/knowledge_neurons/knowledge_neurons/__init__.py`

**Signature:**
```python
def initialize_model_and_tokenizer(
    model_name: str
) -> Tuple[AutoModelForCausalLM, AutoTokenizer]
```

**Parameters:**
- `model_name` (str): Model identifier

**Returns:**
- `Tuple[AutoModelForCausalLM, AutoTokenizer]`: Initialized model and tokenizer

---

### Function: model_type

Determine model architecture type.

**Location:** `baselines/kn/knowledge_neurons/knowledge_neurons/__init__.py`

**Signature:**
```python
def model_type(model_name: str) -> str
```

**Parameters:**
- `model_name` (str): Model identifier

**Returns:**
- `str`: Model type ("gpt2", "gptj", "gptneo", etc.)

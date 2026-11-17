# SAE Spelling API Reference

## Module: sae_spelling.feature_attribution

### Function: calculate_feature_attribution

Calculate attribution scores for SAE features to understand their contribution to model outputs.

**Signature:**
```python
calculate_feature_attribution(
    model: PreTrainedModel,
    sae: SAE,
    prompt: str,
    target_token: str,
    layer_name: str = None,
    num_steps: int = 50,
    device: str = "cuda"
) -> Dict[int, float]
```

**Parameters:**
- `model` (PreTrainedModel): The base language model
- `sae` (SAE): Sparse Autoencoder to analyze
- `prompt` (str): Input prompt text
- `target_token` (str): Target token to predict/analyze
- `layer_name` (str, optional): Specific layer to analyze
- `num_steps` (int): Number of integration steps for gradient calculation
- `device` (str): Device to run computations on

**Returns:**
- `Dict[int, float]`: Mapping of feature indices to attribution scores

---

### Function: calculate_integrated_gradient_attribution_patching

Perform integrated gradient attribution with patching for more accurate feature importance.

**Signature:**
```python
calculate_integrated_gradient_attribution_patching(
    model: PreTrainedModel,
    sae: SAE,
    input_ids: torch.Tensor,
    target_idx: int,
    baseline_ids: torch.Tensor = None,
    num_steps: int = 50
) -> torch.Tensor
```

**Parameters:**
- `model` (PreTrainedModel): The language model
- `sae` (SAE): Sparse Autoencoder
- `input_ids` (torch.Tensor): Input token IDs
- `target_idx` (int): Target token index in vocabulary
- `baseline_ids` (torch.Tensor, optional): Baseline for integration
- `num_steps` (int): Integration steps

**Returns:**
- `torch.Tensor`: Attribution scores for each SAE feature

---

## Module: sae_spelling.feature_ablation

### Function: calculate_individual_feature_ablations

Ablate individual SAE features and measure impact on model outputs.

**Signature:**
```python
calculate_individual_feature_ablations(
    model: PreTrainedModel,
    sae: SAE,
    prompt: str,
    metric_fn: Callable = None,
    hook_point: str = None,
    device: str = "cuda"
) -> Dict[int, Dict[str, float]]
```

**Parameters:**
- `model` (PreTrainedModel): The language model
- `sae` (SAE): Sparse Autoencoder
- `prompt` (str): Evaluation prompt
- `metric_fn` (Callable, optional): Function to evaluate output quality
- `hook_point` (str, optional): Model hook point for SAE application
- `device` (str): Computation device

**Returns:**
- `Dict[int, Dict[str, float]]`: Per-feature ablation effects including effect size, firing rate, and importance

---

## Module: sae_spelling.probing

### Function: train_multi_probe

Train a multi-class logistic regression probe on activations.

**Signature:**
```python
train_multi_probe(
    x_train: torch.Tensor,
    y_train: torch.Tensor,
    num_classes: int,
    learning_rate: float = 0.01,
    num_epochs: int = 100,
    l2_penalty: float = 0.001
) -> LinearProbe
```

**Parameters:**
- `x_train` (torch.Tensor): Training activations of shape (n_samples, n_features)
- `y_train` (torch.Tensor): Training labels of shape (n_samples,)
- `num_classes` (int): Number of output classes
- `learning_rate` (float): Learning rate for optimization
- `num_epochs` (int): Number of training epochs
- `l2_penalty` (float): L2 regularization strength

**Returns:**
- `LinearProbe`: Trained probe model

---

### Function: train_binary_probe

Train a binary classification probe.

**Signature:**
```python
train_binary_probe(
    x_train: torch.Tensor,
    y_train: torch.Tensor,
    learning_rate: float = 0.01,
    num_epochs: int = 100
) -> LinearProbe
```

**Parameters:**
- `x_train` (torch.Tensor): Training activations
- `y_train` (torch.Tensor): Binary labels (0 or 1)
- `learning_rate` (float): Learning rate
- `num_epochs` (int): Training epochs

**Returns:**
- `LinearProbe`: Trained binary probe

---

## Module: sae_spelling.experiments.k_sparse_probing

### Class: KSparseProbe

A probe that uses only the top-k most important features for classification.

**Constructor:**
```python
KSparseProbe(
    input_dim: int,
    output_dim: int,
    k: int,
    bias: bool = True
)
```

**Parameters:**
- `input_dim` (int): Number of input features
- `output_dim` (int): Number of output classes
- `k` (int): Number of features to use
- `bias` (bool): Whether to include bias term

**Methods:**

#### forward(x: torch.Tensor) -> torch.Tensor
Perform forward pass with k-sparse feature selection.

---

### Function: train_k_sparse_probes

Train multiple k-sparse probes with different sparsity levels.

**Signature:**
```python
train_k_sparse_probes(
    sae: SAE,
    train_labels: List[Tuple[str, int]],
    train_activations: torch.Tensor,
    k_values: List[int] = None,
    l1_decay: float = 0.001
) -> Dict[int, KSparseProbe]
```

**Parameters:**
- `sae` (SAE): Sparse Autoencoder
- `train_labels` (List[Tuple[str, int]]): Training labels
- `train_activations` (torch.Tensor): Training activations
- `k_values` (List[int], optional): List of k values to test
- `l1_decay` (float): L1 regularization strength

**Returns:**
- `Dict[int, KSparseProbe]`: Mapping of k values to trained probes

---

## Module: sae_spelling.prompting

### Function: create_icl_prompt

Create in-context learning prompts for evaluation.

**Signature:**
```python
create_icl_prompt(
    tokens: List[str],
    formatter: Callable,
    num_shots: int = 5,
    separator: str = "\n"
) -> str
```

**Parameters:**
- `tokens` (List[str]): List of tokens to include
- `formatter` (Callable): Function to format each token
- `num_shots` (int): Number of examples to include
- `separator` (str): String to separate examples

**Returns:**
- `str`: Formatted ICL prompt

---

### Function: spelling_formatter

Create a formatter that outputs token spelling.

**Signature:**
```python
spelling_formatter() -> Callable[[str], str]
```

**Returns:**
- `Callable`: Formatter function that spells out tokens

---

### Function: first_letter_formatter

Create a formatter that outputs the first letter of tokens.

**Signature:**
```python
first_letter_formatter() -> Callable[[str], str]
```

**Returns:**
- `Callable`: Formatter function that extracts first letters

---

## Module: sae_spelling.sae_utils

### Function: apply_saes_and_run

Apply SAEs to a model and run on given inputs with optional gradient tracking.

**Signature:**
```python
apply_saes_and_run(
    model: HookedTransformer,
    saes: Dict[str, SAE],
    input_ids: torch.Tensor,
    hooks: List[Callable] = None,
    track_gradients: bool = False
) -> ModelOutput
```

**Parameters:**
- `model` (HookedTransformer): Model with hook support
- `saes` (Dict[str, SAE]): Mapping of hook points to SAEs
- `input_ids` (torch.Tensor): Input token IDs
- `hooks` (List[Callable], optional): Additional hooks to apply
- `track_gradients` (bool): Whether to track activation gradients

**Returns:**
- `ModelOutput`: Model output with SAEs applied

---

## Module: sae_spelling.vocab

### Function: get_alpha_tokens

Filter alphabetic tokens from tokenizer vocabulary.

**Signature:**
```python
get_alpha_tokens(
    tokenizer: PreTrainedTokenizerFast,
    min_length: int = 2,
    max_length: int = 10
) -> List[str]
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizerFast): Tokenizer with vocabulary
- `min_length` (int): Minimum token length
- `max_length` (int): Maximum token length

**Returns:**
- `List[str]`: List of alphabetic tokens

---

## Module: sae_spelling.spelling_grader

### Class: SpellingGrader

Evaluate model performance on spelling tasks.

**Constructor:**
```python
SpellingGrader(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase
)
```

**Parameters:**
- `model` (PreTrainedModel): Language model to evaluate
- `tokenizer` (PreTrainedTokenizerBase): Model tokenizer

**Methods:**

#### grade_spelling(prompt: str, expected: str) -> Dict[str, Any]
Grade model's spelling performance on a single prompt.

**Parameters:**
- `prompt` (str): Input prompt
- `expected` (str): Expected output

**Returns:**
- `Dict[str, Any]`: Grading results including accuracy and confidence

---

## Module: sae_spelling.feature_absorption_calculator

### Class: FeatureAbsorptionCalculator

Calculate feature absorption metrics for SAEs.

**Constructor:**
```python
FeatureAbsorptionCalculator(
    sae: SAE,
    probe: LinearProbe,
    device: str = "cuda"
)
```

**Parameters:**
- `sae` (SAE): Sparse Autoencoder
- `probe` (LinearProbe): Trained probe for comparison
- `device` (str): Computation device

**Methods:**

#### calculate_absorption(activations: torch.Tensor) -> Dict[str, float]
Calculate absorption metrics for given activations.

**Parameters:**
- `activations` (torch.Tensor): Input activations

**Returns:**
- `Dict[str, float]`: Absorption metrics including overlap and redundancy scores

---

## Module: sae_spelling.experiments.common

### Class: SaeInfo

Information container for SAE configuration.

**Attributes:**
- `layer` (int): Transformer layer index
- `width` (int): SAE width (number of features)
- `l0` (int): L0 sparsity target
- `name` (str): SAE identifier

---

### Function: load_gemma2_model

Load a Gemma-2 model with specified configuration.

**Signature:**
```python
load_gemma2_model(
    dtype: torch.dtype | str = "float32",
    device: str = "cuda"
) -> Tuple[HookedTransformer, PreTrainedTokenizerFast]
```

**Parameters:**
- `dtype` (torch.dtype | str): Model data type
- `device` (str): Device to load model on

**Returns:**
- `Tuple[HookedTransformer, PreTrainedTokenizerFast]`: Model and tokenizer

---

### Function: load_gemmascope_sae

Load a pre-trained GemmaScope SAE.

**Signature:**
```python
load_gemmascope_sae(
    layer: int,
    width: str | int,
    l0: str | int
) -> SAE
```

**Parameters:**
- `layer` (int): Layer index
- `width` (str | int): SAE width identifier
- `l0` (str | int): L0 sparsity identifier

**Returns:**
- `SAE`: Loaded Sparse Autoencoder

---

## Module: sae_spelling.experiments.latent_evaluation

### Function: eval_probe_and_top_sae_raw_scores

Evaluate probe performance and top SAE features on a task.

**Signature:**
```python
eval_probe_and_top_sae_raw_scores(
    sae: SAE,
    probe: LinearProbe,
    eval_labels: List[Tuple[str, int]],
    eval_activations: torch.Tensor,
    topk: int = 5
) -> pd.DataFrame
```

**Parameters:**
- `sae` (SAE): Sparse Autoencoder
- `probe` (LinearProbe): Trained probe
- `eval_labels` (List[Tuple[str, int]]): Evaluation labels
- `eval_activations` (torch.Tensor): Evaluation activations
- `topk` (int): Number of top features to evaluate

**Returns:**
- `pd.DataFrame`: Evaluation results dataframe

---

### Function: build_evaluation_df

Build comprehensive evaluation dataframe from results.

**Signature:**
```python
build_evaluation_df(
    results_df: pd.DataFrame,
    sae_info: SaeInfo,
    topk: int = 10
) -> pd.DataFrame
```

**Parameters:**
- `results_df` (pd.DataFrame): Raw results
- `sae_info` (SaeInfo): SAE configuration
- `topk` (int): Number of top features to analyze

**Returns:**
- `pd.DataFrame`: Processed evaluation dataframe

---

## Module: sae_spelling.experiments.feature_absorption

### Class: StatsAndLikelyFalseNegativeResults

Container for feature absorption statistics and analysis results.

**Attributes:**
- `stats` (pd.DataFrame): Statistical summary
- `likely_false_negatives` (List[str]): Tokens with potential false negatives
- `absorption_scores` (Dict[str, float]): Feature absorption metrics

---

### Function: calculate_ig_ablation_and_cos_sims

Calculate integrated gradient ablation and cosine similarities for absorption analysis.

**Signature:**
```python
calculate_ig_ablation_and_cos_sims(
    calculator: FeatureAbsorptionCalculator,
    sae: SAE,
    probe: LinearProbe,
    eval_data: Dict[str, torch.Tensor]
) -> Dict[str, Any]
```

**Parameters:**
- `calculator` (FeatureAbsorptionCalculator): Absorption calculator
- `sae` (SAE): Sparse Autoencoder
- `probe` (LinearProbe): Trained probe
- `eval_data` (Dict[str, torch.Tensor]): Evaluation data

**Returns:**
- `Dict[str, Any]`: Ablation and similarity results

---

### Function: letter_delta_metric

Create a metric function for letter-based evaluation tasks.

**Signature:**
```python
letter_delta_metric(
    tokenizer: PreTrainedTokenizerBase,
    pos_letter: str
) -> Callable[[torch.Tensor], float]
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizerBase): Model tokenizer
- `pos_letter` (str): Target letter

**Returns:**
- `Callable`: Metric function for evaluation

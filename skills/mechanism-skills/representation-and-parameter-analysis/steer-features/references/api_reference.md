# SAE Steering API Reference

## Module: src.output_score

### Function: get_output_score
Calculate the output score for a specific SAE feature based on its effect on model outputs.

**Location:** `src/output_score.py`

**Signature:**
```python
def get_output_score(
    layer: int, 
    feature: int, 
    logit_lens_indices: List[int]
) -> float
```

**Parameters:**
- `layer` (int): The model layer index where the feature is located
- `feature` (int): The index of the SAE feature to score
- `logit_lens_indices` (List[int]): Token indices to focus on for scoring

**Returns:**
- `float`: Output score value (higher indicates stronger effect on model output)

**Description:**
Computes how much a specific SAE feature affects the model's output distribution when activated. This metric helps identify features that have meaningful causal effects on generation.

---

### Function: parse_args
Parse command-line arguments for output score computation.

**Location:** `src/output_score.py`

**Signature:**
```python
def parse_args() -> argparse.Namespace
```

**Returns:**
- `argparse.Namespace`: Parsed command-line arguments including model_type, features_file, and cache_path

---

### Function: main
Main execution function for output score computation.

**Location:** `src/output_score.py`

**Signature:**
```python
def main() -> None
```

**Description:**
Orchestrates the output score computation process:
1. Loads feature definitions from JSON
2. Computes output scores for each feature
3. Saves results to cache file

---

## Module: src.input_score

### Function: parse_args
Parse command-line arguments for input score computation.

**Location:** `src/input_score.py`

**Signature:**
```python
def parse_args() -> argparse.Namespace
```

**Returns:**
- `argparse.Namespace`: Parsed arguments including model_type, features_file, cache_path, and feature_data_path

---

### Function: main
Main execution function for input score computation.

**Location:** `src/input_score.py`

**Signature:**
```python
def main() -> None
```

**Description:**
Manages the input score computation workflow:
1. Loads feature data from Neuronpedia or local files
2. Analyzes activation patterns for each feature
3. Computes input scores based on token consistency
4. Caches results for future use

---

## Module: src.sae_utils

### Class: AmlifySAEHook
Hook class for amplifying specific SAE features during model inference.

**Location:** `src/sae_utils.py`

**Constructor:**
```python
def __init__(
    self,
    layer: int,
    feature_idx: int,
    amplification_factor: float,
    sae: Optional[SAE] = None
)
```

**Parameters:**
- `layer` (int): Target model layer for hook attachment
- `feature_idx` (int): Index of the SAE feature to amplify
- `amplification_factor` (float): Multiplication factor for feature amplification (typically 0.2 to 20.0)
- `sae` (Optional[SAE]): Pre-loaded SAE model, if available

**Methods:**

#### forward_hook
```python
def forward_hook(
    self,
    module: torch.nn.Module,
    input: Tuple[torch.Tensor],
    output: Tuple[torch.Tensor]
) -> Tuple[torch.Tensor]
```

**Description:**
Hook function that intercepts model forward pass to amplify the specified SAE feature.

**Parameters:**
- `module`: The hooked model layer
- `input`: Input tensors to the layer
- `output`: Output tensors from the layer

**Returns:**
- Modified output with amplified feature activation

---

### Function: _disable_hooks
Disable gradient-related hooks in SAE for inference efficiency.

**Location:** `src/sae_utils.py`

**Signature:**
```python
def _disable_hooks(sae: SAE) -> None
```

**Parameters:**
- `sae` (SAE): The SAE model whose hooks should be disabled

**Description:**
Removes gradient computation hooks from SAE to improve inference speed when gradients are not needed.

---

### Function: init_hook
Initialize and register a steering hook with the model pipeline.

**Location:** `src/sae_utils.py`

**Signature:**
```python
def init_hook(
    pipeline: Any,
    sae: SAE,
    layer: int
) -> AmlifySAEHook
```

**Parameters:**
- `pipeline`: The model or pipeline to attach the hook to
- `sae` (SAE): The SAE model for feature extraction
- `layer` (int): Target layer index

**Returns:**
- `AmlifySAEHook`: Initialized and registered hook instance

---

## Module: src.plot

### Function: get_generation_success
Evaluate the success rate of steering based on generated sentences.

**Location:** `src/plot.py`

**Signature:**
```python
def get_generation_success(
    sentences: List[str],
    logit_lens_indices: List[int],
    tokenizer: AutoTokenizer
) -> float
```

**Parameters:**
- `sentences` (List[str]): Generated text outputs from steering
- `logit_lens_indices` (List[int]): Target token indices for evaluation
- `tokenizer` (AutoTokenizer): Tokenizer for text processing

**Returns:**
- `float`: Success rate (0.0 to 1.0) of steering effectiveness

**Description:**
Analyzes generated text to determine if steering successfully influenced the model to produce desired tokens or patterns.

---

### Function: get_axbench_generation_success
Specialized evaluation for Axbench instruction-following tasks.

**Location:** `src/plot.py`

**Signature:**
```python
def get_axbench_generation_success(
    sentences: List[str],
    logit_lens_indices: List[int],
    tokenizer: AutoTokenizer
) -> float
```

**Parameters:**
- `sentences` (List[str]): Generated instruction responses
- `logit_lens_indices` (List[int]): Expected response patterns
- `tokenizer` (AutoTokenizer): Tokenizer for text processing

**Returns:**
- `float`: Success rate for instruction-following with steering

**Description:**
Evaluates steering effectiveness specifically for instruction-following tasks, considering both concept adherence and instruction compliance.

---

### Function: parse_args
Parse command-line arguments for plotting and analysis.

**Location:** `src/plot.py`

**Signature:**
```python
def parse_args() -> argparse.Namespace
```

**Returns:**
- `argparse.Namespace`: Parsed arguments for visualization and analysis

---

## Module: src.steer

### Function: parse_args
Parse command-line arguments for steering experiments.

**Location:** `src/steer.py`

**Signature:**
```python
def parse_args() -> argparse.Namespace
```

**Returns:**
- `argparse.Namespace`: Configuration for steering including model, features, and factors

---

### Function: main
Main execution function for model steering.

**Location:** `src/steer.py`

**Signature:**
```python
def main() -> None
```

**Description:**
Orchestrates the complete steering pipeline:
1. Loads model and SAE
2. Selects features based on scores
3. Applies steering hooks
4. Generates text with various steering factors
5. Evaluates and saves results

---

## Configuration File Formats

### Feature Definition JSON
```json
{
  "feature_id": {
    "layer": 10,
    "index": 1234,
    "description": "Feature description",
    "output_score": 0.85,
    "input_score": 0.45
  }
}
```

### Generation Cache JSON
```json
{
  "config": {
    "model": "gemma-2b",
    "steering_factor": 2.0,
    "layer": 10,
    "feature": 1234
  },
  "generations": [
    {
      "prompt": "Input text",
      "output": "Generated text",
      "success": true
    }
  ]
}
```

### Score Cache JSON
```json
{
  "output_scores": {
    "1234": 0.85,
    "5678": 0.72
  },
  "input_scores": {
    "1234": 0.45,
    "5678": 0.89
  },
  "metadata": {
    "model": "gemma-2b",
    "timestamp": "2024-01-01T00:00:00"
  }
}
```

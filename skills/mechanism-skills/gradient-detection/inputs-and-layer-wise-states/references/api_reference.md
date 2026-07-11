# Layer Gradient Analysis API Reference

## Module: code_gradient.get_gradient_values

### Core Functions

#### parse_args() -> argparse.Namespace
Parse command-line arguments for gradient calculation.

**Returns:**
- `Namespace`: Parsed arguments containing:
  - `data_path` (str): Path to input data file
  - `save_path` (str): Path to save gradient results
  - `model_name_or_path` (str): Model identifier or path
  - `max_length` (int): Maximum sequence length
  - `run_instruct_version` (bool): Whether to run instruction-tuned version

**Example:**
```python
args = parse_args()
# Access arguments
print(args.data_path)
print(args.model_name_or_path)
```

---

#### cal_svd_vector_part_text(tokenizer, model, text) -> Dict
Calculate SVD vectors for gradient analysis on partial text.

**Parameters:**
- `tokenizer`: Hugging Face tokenizer instance
- `model`: Hugging Face model instance
- `text` (str): Input text for gradient calculation

**Returns:**
- `Dict`: Dictionary containing:
  - Layer-wise SVD components
  - Singular values
  - Top component variance ratios

**Example:**
```python
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3.1-8B")
model = AutoModelForCausalLM.from_pretrained("meta-llama/Meta-Llama-3.1-8B")

svd_results = cal_svd_vector_part_text(tokenizer, model, "Example text")
```

---

#### filter_dicts(list1: List[Dict], list2: List[Dict]) -> Tuple[List[Dict], List[Dict]]
Filter and align dictionaries from two lists based on common keys.

**Parameters:**
- `list1` (List[Dict]): First list of dictionaries
- `list2` (List[Dict]): Second list of dictionaries

**Returns:**
- `Tuple[List[Dict], List[Dict]]`: Filtered and aligned lists

**Example:**
```python
list1 = [{"layer_1": 0.5}, {"layer_2": 0.3}]
list2 = [{"layer_1": 0.4}, {"layer_3": 0.2}]
filtered_1, filtered_2 = filter_dicts(list1, list2)
```

---

## Module: code_vis.exp_utils

### Statistical Functions

#### relative_difference(list1: List[float], list2: List[float]) -> List[float]
Calculate relative differences between two lists of values.

**Parameters:**
- `list1` (List[float]): First list of numerical values
- `list2` (List[float]): Second list of numerical values

**Returns:**
- `List[float]`: List of relative differences

**Formula:**

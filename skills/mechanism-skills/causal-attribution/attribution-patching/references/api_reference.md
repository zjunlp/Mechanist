# Edge Attribution Patching API Reference

## Module: ACDCPPExperiment

### Class: ACDCPPExperiment

Main experimental framework for running Attribution Patching experiments on transformer models.

**Source:** `ACDCPPExperiment.py`

**Constructor:**
```python
ACDCPPExperiment(
    model: TransformerModel,
    dataset: Dataset,
    task: str,
    config: Optional[Dict] = None
)
```

**Parameters:**
- `model` (TransformerModel): The transformer model to analyze (from TransformerLens)
- `dataset` (Dataset): Task-specific dataset for experiments
- `task` (str): Task identifier ('ioi', 'greaterthan', 'docstring')
- `config` (Dict, optional): Additional configuration parameters

**Methods:**

#### run_attribution_patching(threshold: float, use_abs_value: bool = True) -> Dict
Run the attribution patching algorithm to discover important circuits.

**Parameters:**
- `threshold` (float): Pruning threshold for edge importance
- `use_abs_value` (bool): Whether to use absolute values of attributions

**Returns:**
- `Dict`: Results containing pruned edges, convergence info, and performance metrics

---

## Module: ioi_task.ioi_dataset

### Class: IOIDataset

Handles data generation and manipulation for Indirect Object Identification tasks.

**Source:** `ioi_task/ioi_dataset.py`

**Constructor:**
```python
IOIDataset(
    templates: List[str],
    names: List[List[str]],
    nouns_dict: Dict[str, List[str]],
    seed: int = 0
)
```

**Parameters:**
- `templates` (List[str]): Sentence templates with placeholders
- `names` (List[List[str]]): Lists of name pairs for IO and S positions
- `nouns_dict` (Dict[str, List[str]]): Dictionary mapping placeholder types to noun options
- `seed` (int): Random seed for reproducibility

### Functions:

#### gen_prompt_uniform(templates: List[str], names: List[List[str]], nouns_dict: Dict) -> List[Dict]
Generate prompts with uniform distribution across templates and names.

**Source:** `ioi_task/ioi_dataset.py`

**Parameters:**
- `templates` (List[str]): List of sentence templates
- `names` (List[List[str]]): List of name pairs
- `nouns_dict` (Dict): Dictionary of nouns by category

**Returns:**
- `List[Dict]`: List of prompt dictionaries with metadata

**Example:**
```python
prompts = gen_prompt_uniform(
    templates=["[A] and [B] went to the [PLACE]"],
    names=[["Alice", "Bob"], ["Charlie", "David"]],
    nouns_dict={"PLACE": ["store", "park"]}
)
```

#### flip_words_in_prompt(prompt: str, word1: str, word2: str) -> str
Swap occurrences of two words in a prompt string.

**Source:** `ioi_task/ioi_dataset.py`

**Parameters:**
- `prompt` (str): Original prompt text
- `word1` (str): First word to swap
- `word2` (str): Second word to swap

**Returns:**
- `str`: Prompt with words flipped

**Example:**
```python
flipped = flip_words_in_prompt(
    "Alice gave the book to Bob",
    "Alice",
    "Bob"
)
# Result: "Bob gave the book to Alice"
```

#### gen_flipped_prompts(prompts: List[Dict], templates_by_prompt: List[str], flip: str) -> List[Dict]
Generate flipped versions of prompts for causal intervention analysis.

**Source:** `ioi_task/ioi_dataset.py`

**Parameters:**
- `prompts` (List[Dict]): Original prompt dictionaries
- `templates_by_prompt` (List[str]): Template for each prompt
- `flip` (str): Type of flip - 'IO' for indirect object, 'S' for subject

**Returns:**
- `List[Dict]`: Flipped prompt dictionaries with metadata

---

## Module: utils.prune_utils

Utility functions for pruning redundant nodes and edges in neural circuits.

### Functions:

#### remove_redundant_node(exp: ACDCPPExperiment, node: Tuple[int, int], safe: bool = True) -> bool
Safely remove a redundant node from the circuit if it doesn't affect performance.

**Source:** `utils/prune_utils.py`

**Parameters:**
- `exp` (ACDCPPExperiment): Experiment object containing the circuit
- `node` (Tuple[int, int]): Node identifier (layer, position)
- `safe` (bool): Whether to check performance impact before removal

**Returns:**
- `bool`: True if node was successfully removed

#### remove_node(exp: ACDCPPExperiment, node: Tuple[int, int]) -> None
Directly remove a node from the experimental circuit.

**Source:** `utils/prune_utils.py`

**Parameters:**
- `exp` (ACDCPPExperiment): Experiment object
- `node` (Tuple[int, int]): Node to remove (layer, position)

**Returns:**
- `None`

#### find_attn_node(exp: ACDCPPExperiment, layer: int, head: int) -> Optional[Tuple[int, int]]
Locate an attention node by its layer and head indices.

**Source:** `utils/prune_utils.py`

**Parameters:**
- `exp` (ACDCPPExperiment): Experiment object
- `layer` (int): Layer index (0-indexed)
- `head` (int): Head index within the layer

**Returns:**
- `Optional[Tuple[int, int]]`: Node identifier if found, None otherwise

**Example:**
```python
node = find_attn_node(exp, layer=5, head=8)
if node:
    remove_redundant_node(exp, node, safe=True)
```

---

## Module: greaterthan_task.minimal_acdc_node_roc

Functions for ROC analysis and Pareto optimization in circuit discovery.

### Functions:

#### pareto_optimal_sublist(xs: List[float], ys: List[float]) -> List[Tuple[float, float]]
Find the Pareto optimal points from two lists of values.

**Source:** `greaterthan_task/minimal_acdc_node_roc.py`

**Parameters:**
- `xs` (List[float]): First objective values (e.g., sparsity)
- `ys` (List[float]): Second objective values (e.g., accuracy)

**Returns:**
- `List[Tuple[float, float]]`: List of Pareto optimal (x, y) pairs

**Example:**
```python
# Find optimal trade-offs between sparsity and accuracy
sparsity_values = [0.1, 0.3, 0.5, 0.7, 0.9]
accuracy_values = [0.95, 0.92, 0.88, 0.85, 0.80]
optimal_points = pareto_optimal_sublist(sparsity_values, accuracy_values)
```

---

## Module: utils.graphics_utils

Utilities for visualizing circuits and attribution results.

### Functions:

Note: Specific function signatures not available from code analysis. Common visualization functions include:

- Circuit graph rendering
- Attribution heatmap generation
- Attention pattern visualization
- Pruning progress plots

---

## Data Structures

### Prompt Dictionary Format
Used throughout the IOI task:
```python
{
    "text": str,           # The prompt text
    "IO": str,            # Indirect object name
    "S": str,             # Subject name
    "template_idx": int,  # Index of template used
    "answer": str,        # Expected model output
    "flip_type": str      # Type of flip applied (optional)
}
```

### Attribution Results Format
Standard output from attribution patching:
```python
{
    "pruned_heads": List[Tuple[int, int]],  # (layer, head) pairs
    "pruned_attrs": List[float],            # Attribution values
    "num_passes": int,                      # Convergence iterations
    "final_score": float,                   # Circuit performance
    "threshold": float                      # Final threshold used
}
```

### Experiment Configuration Format
```python
{
    "task": str,              # Task identifier
    "model_name": str,        # Model identifier
    "use_abs_value": bool,    # Absolute value flag
    "threshold": float,       # Initial threshold
    "batch_size": int,        # Batch size for processing
    "device": str            # Computing device
}
```

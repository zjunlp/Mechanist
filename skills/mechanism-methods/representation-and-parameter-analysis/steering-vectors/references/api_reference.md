# Llama 2 CAA API Reference

## Core Modules

### generate_vectors.py

Module for generating steering vectors from contrastive behavioral datasets.

#### Class: ComparisonDataset

PyTorch dataset for loading contrastive behavior examples.

**Constructor:**
```python
ComparisonDataset(
    file_path: str,
    tokenizer: transformers.PreTrainedTokenizer,
    max_length: int = 512,
    model: str = "llama"
)
```

**Parameters:**
- `file_path` (str): Path to JSON dataset file
- `tokenizer` (PreTrainedTokenizer): Tokenizer for the model
- `max_length` (int): Maximum sequence length for tokenization
- `model` (str): Model type identifier

**Methods:**

##### __getitem__(idx: int) -> Dict[str, torch.Tensor]
Returns tokenized positive and negative examples for the given index.

##### __len__() -> int
Returns the total number of examples in the dataset.

---

#### Function: generate_save_vectors_for_behavior

Generate and save steering vectors for a specific behavior.

```python
generate_save_vectors_for_behavior(
    layers: List[int],
    save_activations: bool,
    behavior: str,
    model_size: str = "7b",
    use_base_model: bool = False
)
```

**Parameters:**
- `layers` (List[int]): Layer indices to generate vectors for
- `save_activations` (bool): Whether to save raw activations
- `behavior` (str): Behavior name (e.g., 'sycophancy', 'hallucination')
- `model_size` (str): Model size ('7b' or '13b')
- `use_base_model` (bool): Use base model instead of chat model

**Returns:**
- None (saves vectors to disk)

---

#### Function: generate_save_vectors

Generate steering vectors for multiple behaviors.

```python
generate_save_vectors(
    layers: List[int],
    save_activations: bool,
    use_base_model: bool = False,
    model_size: str = "7b"
)
```

**Parameters:**
- `layers` (List[int]): Layer indices to process
- `save_activations` (bool): Save raw activations
- `use_base_model` (bool): Use base model
- `model_size` (str): Model size identifier

---

### prompting_with_steering.py

Module for applying steering vectors during model inference.

#### Function: get_a_b_probs

Calculate probabilities for A/B answer choices.

```python
get_a_b_probs(
    model: transformers.PreTrainedModel,
    tokenizer: transformers.PreTrainedTokenizer,
    prompt: str,
    answer_A: str,
    answer_B: str,
    device: str = "cuda"
) -> Tuple[float, float]
```

**Parameters:**
- `model` (PreTrainedModel): Language model
- `tokenizer` (PreTrainedTokenizer): Tokenizer
- `prompt` (str): Question prompt
- `answer_A` (str): First answer choice
- `answer_B` (str): Second answer choice
- `device` (str): Computation device

**Returns:**
- Tuple[float, float]: Probabilities for answer A and B

---

#### Function: run_open_ended_generation

Generate open-ended responses with steering.

```python
run_open_ended_generation(
    model: transformers.PreTrainedModel,
    tokenizer: transformers.PreTrainedTokenizer,
    question: str,
    max_new_tokens: int = 100,
    temperature: float = 0.7
) -> str
```

**Parameters:**
- `model` (PreTrainedModel): Language model
- `tokenizer` (PreTrainedTokenizer): Tokenizer
- `question` (str): Input question
- `max_new_tokens` (int): Maximum tokens to generate
- `temperature` (float): Sampling temperature

**Returns:**
- str: Generated response

---

### analyze_vectors.py

Module for analyzing and visualizing steering vectors.

#### Function: get_caa_info

Get configuration information for CAA experiments.

```python
get_caa_info(
    behavior: str,
    model_size: str,
    is_base: bool
) -> Dict[str, Any]
```

**Parameters:**
- `behavior` (str): Behavior name
- `model_size` (str): Model size ('7b' or '13b')
- `is_base` (bool): Whether using base model

**Returns:**
- Dict containing optimal layer and multiplier configuration

---

#### Function: plot_per_layer_similarities

Plot cosine similarities between steering vectors across layers.

```python
plot_per_layer_similarities(
    model_size: str,
    is_base: bool,
    behavior: str,
    save_path: Optional[str] = None
)
```

**Parameters:**
- `model_size` (str): Model size
- `is_base` (bool): Base model flag
- `behavior` (str): Behavior to analyze
- `save_path` (str, optional): Path to save figure

---

#### Function: plot_base_chat_similarities

Compare steering vectors between base and chat models.

```python
plot_base_chat_similarities(
    behaviors: List[str] = None,
    layers: List[int] = None,
    model_size: str = "7b"
)
```

**Parameters:**
- `behaviors` (List[str]): Behaviors to compare
- `layers` (List[int]): Layers to analyze
- `model_size` (str): Model size

---

### finetune_llama.py

Module for fine-tuning Llama models on behavioral datasets.

#### Class: FinetuneDataset

Dataset for supervised fine-tuning on A/B behavioral choices.

**Constructor:**
```python
FinetuneDataset(
    data_path: str,
    tokenizer: transformers.PreTrainedTokenizer,
    max_length: int = 512,
    maximize_positive: bool = True
)
```

**Parameters:**
- `data_path` (str): Path to training data
- `tokenizer` (PreTrainedTokenizer): Model tokenizer
- `max_length` (int): Maximum sequence length
- `maximize_positive` (bool): Whether to maximize positive behavior

**Methods:**

##### __getitem__(idx: int) -> Dict[str, torch.Tensor]
Returns tokenized example with labels.

##### __len__() -> int
Returns dataset size.

---

#### Function: get_finetune_dataloader

Create DataLoader for fine-tuning.

```python
get_finetune_dataloader(
    batch_size: int,
    tokenizer: transformers.PreTrainedTokenizer,
    behavior: str,
    direction: str = "pos"
) -> DataLoader
```

**Parameters:**
- `batch_size` (int): Batch size for training
- `tokenizer` (PreTrainedTokenizer): Tokenizer
- `behavior` (str): Target behavior
- `direction` (str): 'pos' or 'neg' for behavior direction

**Returns:**
- DataLoader: PyTorch DataLoader for training

---

#### Function: eval_model

Evaluate fine-tuned model performance.

```python
eval_model(
    model: transformers.PreTrainedModel,
    dataloader: DataLoader,
    maximize_positive: bool = True
) -> Dict[str, float]
```

**Parameters:**
- `model` (PreTrainedModel): Model to evaluate
- `dataloader` (DataLoader): Evaluation data
- `maximize_positive` (bool): Expected behavior direction

**Returns:**
- Dict with accuracy and loss metrics

---

### behaviors.py

Utility module for managing behaviors and vector paths.

#### Function: get_vector_dir

Get directory path for steering vectors.

```python
get_vector_dir(
    behavior: str,
    normalized: bool = False
) -> Path
```

**Parameters:**
- `behavior` (str): Behavior name
- `normalized` (bool): Use normalized vectors directory

**Returns:**
- Path: Directory containing vectors

---

#### Function: get_vector_path

Get file path for a specific steering vector.

```python
get_vector_path(
    behavior: str,
    layer: int,
    model_name_path: str
) -> Path
```

**Parameters:**
- `behavior` (str): Behavior name
- `layer` (int): Layer index
- `model_name_path` (str): Model identifier

**Returns:**
- Path: Full path to vector file

---

#### Function: get_raw_data_path

Get path to raw behavioral dataset.

```python
get_raw_data_path(
    behavior: str
) -> Path
```

**Parameters:**
- `behavior` (str): Behavior name

**Returns:**
- Path: Path to raw dataset file

---

### plot_activations.py

Module for visualizing activation patterns.

#### Function: plot_pca_activations

Generate PCA plots of activation differences.

```python
plot_pca_activations(
    activations_pos: np.ndarray,
    activations_neg: np.ndarray,
    layer: int,
    behavior: str,
    save_dir: Path
)
```

**Parameters:**
- `activations_pos` (np.ndarray): Positive behavior activations
- `activations_neg` (np.ndarray): Negative behavior activations
- `layer` (int): Layer index
- `behavior` (str): Behavior name
- `save_dir` (Path): Directory to save plots

---

### plot_results.py

Module for plotting steering experiment results.

#### Function: plot_layer_sweep

Plot performance across layers for different multipliers.

```python
plot_layer_sweep(
    results: Dict[str, Dict[int, float]],
    behavior: str,
    metric: str = "accuracy",
    save_path: Optional[str] = None
)
```

**Parameters:**
- `results` (Dict): Results dictionary with layer and multiplier data
- `behavior` (str): Behavior name
- `metric` (str): Metric to plot ('accuracy' or 'score')
- `save_path` (str, optional): Path to save figure

---

#### Function: plot_multiplier_sweep

Plot performance across multipliers for a fixed layer.

```python
plot_multiplier_sweep(
    results: Dict[float, float],
    behavior: str,
    layer: int,
    metric: str = "accuracy",
    save_path: Optional[str] = None
)
```

**Parameters:**
- `results` (Dict): Results indexed by multiplier
- `behavior` (str): Behavior name
- `layer` (int): Layer index
- `metric` (str): Metric to plot
- `save_path` (str, optional): Save path

---

### normalize_vectors.py

Module for normalizing steering vectors.

#### Function: normalize_vectors_per_layer

Normalize vectors to have consistent norm per layer.

```python
normalize_vectors_per_layer(
    behaviors: List[str],
    layers: List[int],
    model_name: str,
    target_norm: float = 1.0
)
```

**Parameters:**
- `behaviors` (List[str]): List of behaviors
- `layers` (List[int]): Layer indices
- `model_name` (str): Model identifier
- `target_norm` (float): Target norm value

---

## Data Structures

### Behavioral Dataset Format

JSON structure for behavioral datasets:

```json
[
    {
        "question": "Question text",
        "answer_matching_behavior": "Answer exhibiting the behavior",
        "answer_not_matching_behavior": "Answer not exhibiting the behavior",
        "label": 0 or 1
    }
]
```

### Steering Vector Format

Saved as PyTorch tensors (.pt files):
- Shape: `[hidden_size]` (e.g., 4096 for 7B model)
- Dtype: float32 or float16
- File naming: `vec_layer_{layer}_{model_name}.pt`

### Results Format

Evaluation results JSON structure:

```json
{
    "behavior": "behavior_name",
    "layer": 13,
    "multiplier": 1.0,
    "accuracy": 0.85,
    "responses": [
        {
            "question": "...",
            "predicted": "A",
            "correct": "A"
        }
    ]
}
```

## Environment Variables

Required environment variables (set in `.env` file):

- `HF_TOKEN`: Hugging Face API token with Llama 2 access
- `OPEN_AI_KEY`: OpenAI API key for GPT-4 evaluation (optional)

## Model Identifiers

Standard model identifiers used throughout the codebase:

- `meta-llama/Llama-2-7b-hf`: 7B base model
- `meta-llama/Llama-2-7b-chat-hf`: 7B chat model
- `meta-llama/Llama-2-13b-hf`: 13B base model
- `meta-llama/Llama-2-13b-chat-hf`: 13B chat model

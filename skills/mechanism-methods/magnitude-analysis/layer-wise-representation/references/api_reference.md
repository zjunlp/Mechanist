# TruthX API Reference

## Core Classes and Functions

### Module: truthx.models

#### Class: TruthXModel

Main class for loading and applying TruthX editing to language models.

**Constructor:**
```python
TruthXModel(
    base_model_path: str,
    truthx_checkpoint_path: Optional[str] = None,
    device: str = "cuda",
    dtype: torch.dtype = torch.float16
)
```

**Parameters:**
- `base_model_path` (str): Path to the base language model or Hugging Face identifier
- `truthx_checkpoint_path` (str, optional): Path to TruthX checkpoint file (.pt)
- `device` (str): Device to load model on ("cuda" or "cpu")
- `dtype` (torch.dtype): Data type for model weights

**Methods:**

##### apply_editing(edit_strength: float, top_layers: int, mode: str) -> None
Apply TruthX editing vectors to the model.

**Parameters:**
- `edit_strength` (float): Editing strength (-5.0 to 5.0, positive for truthful)
- `top_layers` (int): Number of top layers to edit
- `mode` (str): Editing mode ("truthful" or "hallucinatory")

##### generate(prompt: str, **kwargs) -> str
Generate text with current editing configuration.

**Parameters:**
- `prompt` (str): Input text prompt
- `max_length` (int, optional): Maximum generation length
- `temperature` (float, optional): Sampling temperature
- `top_p` (float, optional): Nucleus sampling parameter

**Returns:**
- `str`: Generated text

---

### Module: truthx.evaluation

#### Class: TruthfulQAEvaluator

Evaluator for TruthfulQA benchmark tasks.

**Constructor:**
```python
TruthfulQAEvaluator(
    model: TruthXModel,
    data_path: str,
    fewshot: bool = True
)
```

**Parameters:**
- `model` (TruthXModel): TruthX model instance
- `data_path` (str): Path to TruthfulQA dataset
- `fewshot` (bool): Whether to use few-shot prompting

**Methods:**

##### evaluate_mc1() -> Dict[str, float]
Evaluate Multiple Choice (single answer) accuracy.

**Returns:**
- `Dict[str, float]`: Dictionary containing:
  - `mc1_accuracy`: MC1 accuracy score
  - `correct`: Number of correct predictions
  - `total`: Total number of examples

##### evaluate_mc2() -> Dict[str, float]
Evaluate Multiple Choice (multiple answers) accuracy.

**Returns:**
- `Dict[str, float]`: Dictionary containing:
  - `mc2_score`: MC2 score
  - `avg_true`: Average score for true answers
  - `avg_false`: Average score for false answers

##### generate_responses(max_length: int = 256) -> List[Dict]
Generate open-ended responses for all examples.

**Parameters:**
- `max_length` (int): Maximum generation length

**Returns:**
- `List[Dict]`: List of dictionaries with question, generated response, and ground truth

---

### Module: truthx.utils

#### Function: load_truthx_checkpoint(path: str) -> Dict
Load TruthX checkpoint from file.

**Parameters:**
- `path` (str): Path to checkpoint file

**Returns:**
- `Dict`: Dictionary containing editing vectors and metadata

**Raises:**
- `FileNotFoundError`: If checkpoint file doesn't exist
- `ValueError`: If checkpoint format is invalid

#### Function: create_prompt(question: str, fewshot: bool = True, template: str = "default") -> str
Create formatted prompt for model input.

**Parameters:**
- `question` (str): Input question
- `fewshot` (bool): Whether to include few-shot examples
- `template` (str): Prompt template to use

**Returns:**
- `str`: Formatted prompt

---

### Module: gui.model_worker

#### Class: ModelWorker

FastChat-compatible model worker for serving TruthX models.

**Constructor:**
```python
ModelWorker(
    model_path: str,
    truthx_model: Optional[str] = None,
    controller_addr: str = "http://localhost:21001",
    worker_addr: str = "http://localhost:31000",
    conv_template: str = "llama-2"
)
```

**Parameters:**
- `model_path` (str): Path to base model
- `truthx_model` (str, optional): Path to TruthX checkpoint
- `controller_addr` (str): Address of FastChat controller
- `worker_addr` (str): Address for this worker
- `conv_template` (str): Conversation template name

**Methods:**

##### register_to_controller() -> None
Register worker to the FastChat controller.

##### generate_stream(params: Dict) -> Generator[str, None, None]
Stream generation with given parameters.

**Parameters:**
- `params` (Dict): Generation parameters including:
  - `prompt`: Input text
  - `temperature`: Sampling temperature
  - `max_new_tokens`: Maximum tokens to generate
  - `edit_strength`: TruthX editing strength
  - `top_layers`: Number of layers to edit

---

### Module: truthfulqa.metrics

#### Function: run_bleu_and_rouge(model_key: str, frame: pd.DataFrame) -> pd.DataFrame
Calculate BLEU and ROUGE scores for generated responses.

**Parameters:**
- `model_key` (str): Model identifier
- `frame` (pd.DataFrame): DataFrame with questions and responses

**Returns:**
- `pd.DataFrame`: DataFrame with added metric columns

**Source:** `TruthfulQA/truthfulqa/metrics.py`

#### Function: run_GPT3(frame: pd.DataFrame, engine: str, tag: str) -> pd.DataFrame
Evaluate responses using GPT-3 as judge.

**Parameters:**
- `frame` (pd.DataFrame): DataFrame with responses
- `engine` (str): GPT-3 engine to use
- `tag` (str): Tag for this evaluation run

**Returns:**
- `pd.DataFrame`: DataFrame with GPT-3 evaluations

**Source:** `TruthfulQA/truthfulqa/models.py`

---

### Module: truthfulqa.utilities

#### Function: load_questions(filename: str) -> pd.DataFrame
Load TruthfulQA questions from CSV file.

**Parameters:**
- `filename` (str): Path to CSV file

**Returns:**
- `pd.DataFrame`: DataFrame containing questions and metadata

**Source:** `TruthfulQA/truthfulqa/utilities.py`

#### Function: format_prompt(ser: pd.Series, preset: str, format: str = "first") -> str
Format question into prompt using specified preset.

**Parameters:**
- `ser` (pd.Series): Series containing question data
- `preset` (str): Preset name for formatting
- `format` (str): Format style ("first", "all", etc.)

**Returns:**
- `str`: Formatted prompt

**Source:** `TruthfulQA/truthfulqa/utilities.py`

---

## Configuration Parameters

### TruthX Editing Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `edit_strength` | float | -5.0 to 5.0 | 1.0 | Editing strength (positive for truthful) |
| `top_layers` | int | 1-32 | 10 | Number of top layers to edit |
| `truthx_model` | str | - | None | Path to TruthX checkpoint |
| `two_fold` | bool | - | False | Enable two-fold validation |

### Generation Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `temperature` | float | 0.0-2.0 | 0.7 | Sampling temperature |
| `top_p` | float | 0.0-1.0 | 0.9 | Nucleus sampling parameter |
| `max_length` | int | 1-2048 | 512 | Maximum generation length |
| `do_sample` | bool | - | True | Whether to use sampling |

### Supported Models

The following models have pre-trained TruthX checkpoints available:

| Model | Identifier | Size |
|-------|------------|------|
| Llama-1 | `huggyllama/llama-7b` | 7B |
| Alpaca | `chavinlo/alpaca-native` | 7B |
| Llama-2 Base | `meta-llama/Llama-2-7b` | 7B |
| Llama-2 Chat | `meta-llama/Llama-2-7b-chat-hf` | 7B |
| Llama-2 Chat | `meta-llama/Llama-2-13b-chat-hf` | 13B |
| Vicuna v1.5 | `lmsys/vicuna-7b-v1.5` | 7B |
| Mistral v0.1 | `mistralai/Mistral-7B-v0.1` | 7B |
| Mistral Instruct v0.1 | `mistralai/Mistral-7B-Instruct-v0.1` | 7B |
| Mistral Instruct v0.2 | `mistralai/Mistral-7B-Instruct-v0.2` | 7B |
| Baichuan2 Base | `baichuan-inc/Baichuan2-7B-Base` | 7B |
| Baichuan2 Chat | `baichuan-inc/Baichuan2-7B-Chat` | 7B |
| ChatGLM3 Base | `THUDM/chatglm3-6b-base` | 6B |
| ChatGLM3 | `THUDM/chatglm3-6b` | 6B |

## Error Handling

### Common Exceptions

#### FileNotFoundError
Raised when TruthX checkpoint or model files are not found.

```python
try:
    model = TruthXModel(base_model_path, truthx_checkpoint_path)
except FileNotFoundError as e:
    print(f"Model files not found: {e}")
```

#### ValueError
Raised when invalid parameters are provided.

```python
try:
    model.apply_editing(edit_strength=10.0)  # Out of range
except ValueError as e:
    print(f"Invalid parameter: {e}")
```

#### RuntimeError
Raised when CUDA is required but not available.

```python
try:
    model = TruthXModel(base_model_path, device="cuda")
except RuntimeError as e:
    print(f"CUDA not available: {e}")
```

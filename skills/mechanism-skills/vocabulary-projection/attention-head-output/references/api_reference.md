# LogitLens4LLMs API Reference

## Core Module: model_factory

### Enum: ModelType

Enumeration of supported model types for LogitLens analysis.

**Values:**
- `LLAMA_3_1_8B` = "llama_3_1_8b" - Meta's Llama 3.1 8B parameter model
- `QWEN_2_5_7B` = "qwen_2_5_7b" - Alibaba's Qwen 2.5 7B parameter model  
- `LLAMA_2_7B` = "llama_2_7b" - Meta's Llama 2 7B parameter model

---

### Class: ModelFactory

Factory class for creating and managing different types of model instances.

#### Method: create_model(model_type: ModelType, use_local: bool = False) -> ModelHelper

Creates a model helper instance based on the specified model type.

**Parameters:**
- `model_type` (ModelType): Type of model to create
- `use_local` (bool, optional): Whether to use locally cached model. Defaults to False.

**Returns:**
- `ModelHelper`: Instance of the appropriate model helper class

**Raises:**
- `ValueError`: If model_type is not supported

**Example:**
```python
from model_factory import ModelFactory, ModelType

model = ModelFactory.create_model(ModelType.LLAMA_3_1_8B, use_local=False)
```

---

## Module: activation_analyzer

### Class: ComponentData

Stores component-level prediction data for analysis.

**Attributes:**
- `attention_mechanism` (List[Tuple[str, float]]): Token predictions from attention mechanism
- `mlp_output` (List[Tuple[str, float]]): Token predictions from MLP layer
- `block_output` (List[Tuple[str, float]]): Combined block output predictions

---

### Class: LayerActivations

Container for layer-wise activation data during analysis.

**Attributes:**
- `layer_idx` (int): Index of the layer (0-based)
- `hidden_states` (torch.Tensor): Hidden state tensor at this layer
- `attention_weights` (torch.Tensor): Attention weight matrix
- `mlp_activations` (torch.Tensor): MLP activation values
- `predictions` (List[Tuple[str, float]]): Top-k token predictions with confidence scores

**Methods:**

#### get_top_predictions(k: int = 5) -> List[Tuple[str, float]]
Get top-k predicted tokens with their confidence scores.

**Parameters:**
- `k` (int): Number of top predictions to return. Defaults to 5.

**Returns:**
- `List[Tuple[str, float]]`: List of (token, confidence_score) tuples

---

### Class: PredictionStep

Data structure for a single prediction step in the generation process.

**Attributes:**
- `step_idx` (int): Step index in generation sequence
- `predicted_token` (str): Token predicted at this step
- `current_text` (str): Full text including this prediction
- `layer_predictions` (List[LayerActivations]): Predictions from all layers
- `important_layers` (List[int]): Indices of layers with high confidence
- `attention_weights` (Dict[int, float]): Attention weights by layer
- `mlp_contributions` (Dict[int, float]): MLP contributions by layer

**Methods:**

#### to_dict() -> Dict[str, Any]
Convert PredictionStep to dictionary for JSON serialization.

**Returns:**
- `Dict[str, Any]`: Dictionary representation of the prediction step

---

## Module: main

### Enum: ModelPath

Enumeration of local model paths for different model types.

**Values:**
- `LLAMA_3_1_8B` = "/path/to/llama-3.1-8b"
- `QWEN_2_5_7B` = "/path/to/qwen-2.5-7b"
- `LLAMA_2_7B` = "/path/to/llama-2-7b"

---

### Function: run_analysis(model_type: ModelType, use_local: bool, token: str) -> List[PredictionStep]

Run LogitLens analysis on a given prompt.

**Parameters:**
- `model_type` (ModelType): Type of model to use
- `use_local` (bool): Whether to use local model
- `token` (str): Hugging Face authentication token (if needed)

**Returns:**
- `List[PredictionStep]`: List of prediction steps with layer-wise analysis

**Example:**
```python
from main import run_analysis
from model_factory import ModelType

results = run_analysis(
    model_type=ModelType.LLAMA_3_1_8B,
    use_local=False,
    token="hf_token"
)
```

---

### Function: main() -> None

Main entry point for the LogitLens analysis program.

**Description:**
Parses command-line arguments and runs analysis based on user input.

**Command-line Arguments:**
- `--model`: Model type to use (llama_3_1_8b, qwen_2_5_7b, llama_2_7b)
- `--local`: Use local model instead of downloading
- `--prompt`: Input prompt for analysis
- `--max-tokens`: Maximum number of tokens to generate
- `--output`: Output directory for results

---

## Module: model_helper.llama_3_1_helper

### Class: Llama3_1_8BHelper

Helper class for Llama 3.1 8B model analysis.

**Constructor:**
```python
Llama3_1_8BHelper(
    model_path: str = "meta-llama/Meta-Llama-3.1-8B",
    use_local: bool = False,
    device: str = "cuda"
)
```

**Parameters:**
- `model_path` (str): Path to model or Hugging Face model ID
- `use_local` (bool): Whether to load from local path
- `device` (str): Device to run model on ("cuda" or "cpu")

**Methods:**

#### generate_with_probing(prompt: str, max_new_tokens: int = 10, print_details: bool = True) -> List[PredictionStep]

Generate text while probing internal layers.

**Parameters:**
- `prompt` (str): Input prompt text
- `max_new_tokens` (int): Maximum tokens to generate
- `print_details` (bool): Whether to print detailed layer information

**Returns:**
- `List[PredictionStep]`: List of prediction steps with layer analysis

#### wrap_block(block_idx: int) -> None

Wrap a transformer block to capture intermediate activations.

**Parameters:**
- `block_idx` (int): Index of the block to wrap

#### unwrap_block(block_idx: int) -> None

Remove wrapper from a transformer block.

**Parameters:**
- `block_idx` (int): Index of the block to unwrap

---

### Class: AttnWrapper

Wrapper for attention mechanism to capture intermediate outputs.

**Constructor:**
```python
AttnWrapper(
    attn_module: nn.Module,
    layer_idx: int,
    analyzer: ActivationAnalyzer
)
```

**Methods:**

#### forward(*args, **kwargs) -> Any

Forward pass through wrapped attention module while capturing activations.

---

### Class: BlockOutputWrapper  

Wrapper for transformer block to capture final output.

**Constructor:**
```python
BlockOutputWrapper(
    block: nn.Module,
    layer_idx: int,
    analyzer: ActivationAnalyzer
)
```

**Methods:**

#### forward(*args, **kwargs) -> Any

Forward pass through wrapped block while capturing output activations.

---

## Module: model_helper.qwen_helper

### Class: QwenHelper

Helper class for Qwen model analysis (similar structure to Llama3_1_8BHelper).

**Constructor:**
```python
QwenHelper(
    model_path: str = "Qwen/Qwen2.5-7B",
    use_local: bool = False,
    device: str = "cuda"
)
```

**Methods:**
- Same as Llama3_1_8BHelper, adapted for Qwen architecture

---

## Module: model_helper.llama_2_helper

### Class: Llama7BHelper

Helper class for Llama 2 7B model analysis (similar structure to Llama3_1_8BHelper).

**Constructor:**
```python
Llama7BHelper(
    model_path: str = "meta-llama/Llama-2-7b-hf",
    use_local: bool = False,
    device: str = "cuda"
)
```

**Methods:**
- Same as Llama3_1_8BHelper, adapted for Llama 2 architecture

---

## Usage Examples

### Basic Analysis
```python
from model_factory import ModelFactory, ModelType

# Create model
model = ModelFactory.create_model(ModelType.LLAMA_3_1_8B)

# Run analysis
results = model.generate_with_probing(
    prompt="The meaning of life is",
    max_new_tokens=10,
    print_details=True
)

# Process results
for step in results:
    print(f"Token: {step.predicted_token}")
    print(f"Important layers: {step.important_layers}")
```

### Custom Layer Analysis
```python
# Wrap specific layers for detailed analysis
model.wrap_block(15)  # Wrap layer 15
model.wrap_block(20)  # Wrap layer 20

# Run generation
results = model.generate_with_probing(prompt="Hello world")

# Unwrap when done
model.unwrap_block(15)
model.unwrap_block(20)
```

### Batch Processing
```python
prompts = ["First prompt", "Second prompt", "Third prompt"]
all_results = []

for prompt in prompts:
    results = model.generate_with_probing(
        prompt=prompt,
        max_new_tokens=5
    )
    all_results.extend(results)

# Save to JSON
import json
with open("batch_results.json", "w") as f:
    json.dump([r.to_dict() for r in all_results], f)
```

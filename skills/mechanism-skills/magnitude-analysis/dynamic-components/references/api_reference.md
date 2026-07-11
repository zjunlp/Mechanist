# Language-Specific Neurons API Reference

## Module: activation

Module for recording neuron activation states across different languages.

### Function: factory(idx)

Factory function for creating activation recording tasks.

**Location:** `activation.py`

**Parameters:**
- `idx` (int): Index identifier for the activation recording task

**Returns:**
- Callable: Function configured for specific activation recording

**Usage:**
```python
from activation import factory

# Create activation recorder for specific index
recorder = factory(0)
```

---

## Module: generation

Module for text generation with selective neuron deactivation.

### Function: load_dataset(lang, sampling_params)

Load language-specific dataset for generation experiments.

**Location:** `generation.py`

**Parameters:**
- `lang` (str): Language code (en, zh, fr, es, vi, id, ja)
- `sampling_params` (dict): Parameters for text sampling including:
  - `temperature` (float): Sampling temperature
  - `top_k` (int): Top-k sampling parameter
  - `top_p` (float): Nucleus sampling parameter
  - `max_tokens` (int): Maximum tokens to generate

**Returns:**
- Dataset: Loaded dataset ready for generation

**Usage:**
```python
from generation import load_dataset

# Load Chinese dataset with specific sampling parameters
dataset = load_dataset(
    lang='zh',
    sampling_params={
        'temperature': 0.7,
        'top_k': 50,
        'top_p': 0.95,
        'max_tokens': 100
    }
)
```

---

## Module: identify

Module for identifying language-specific neurons from activation data.

### Function: activation()

Main function for neuron identification from recorded activations.

**Location:** `identify.py`

**Returns:**
- dict: Dictionary containing identified neurons per language and layer

**Usage:**
```python
from identify import activation

# Identify language-specific neurons
neurons = activation()
```

---

## Data Structures

### Neuron Storage Format

Language-specific neurons are stored as PyTorch tensors in `.pth` files.

**Structure:**
```python
List[List[torch.LongTensor]]
```

**Access Pattern:**
```python
neurons[language_index][layer_index] = torch.LongTensor([neuron_indices])
```

**Language Index Mapping:**
- 0: English (en)
- 1: Chinese (zh)
- 2: French (fr)
- 3: Spanish (es)
- 4: Vietnamese (vi)
- 5: Indonesian (id)
- 6: Japanese (ja)

**Example:**
```python
import torch

# Load neurons
neurons = torch.load('LLaMA-2-7B.neuron.pth')

# Get Chinese neurons in layer 4
chinese_layer_4 = neurons[1][4]  # Returns tensor([6147, 9114, 9292])
```

---

## Activation Mask Format

Activation masks for neuron deactivation are stored as dictionaries.

**Structure:**
```python
Dict[int, torch.Tensor]
```

**Keys:** Layer indices (0-based)
**Values:** Binary masks (1.0 = active, 0.0 = deactivated)

**Example:**
```python
import torch

# Load activation mask
masks = torch.load('activation_mask/chinese_deactivation.pth')

# Access mask for layer 5
layer_5_mask = masks[5]  # Shape: (intermediate_size,)
```

---

## Model Configurations

### LLaMA-2 Models

**LLaMA-2 7B:**
- Layers: 32
- Hidden Size: 4096
- Intermediate Size: 11008
- Model ID: `meta-llama/Llama-2-7b-hf`

**LLaMA-2 13B:**
- Layers: 40
- Hidden Size: 5120
- Intermediate Size: 13824
- Model ID: `meta-llama/Llama-2-13b-hf`

**LLaMA-2 70B:**
- Layers: 80
- Hidden Size: 8192
- Intermediate Size: 28672
- Model ID: `meta-llama/Llama-2-70b-hf`

### Other Supported Models

**BLOOM 7B:**
- Layers: 30
- Hidden Size: 4096
- Intermediate Size: 16384

**OPT 6.7B:**
- Layers: 32
- Hidden Size: 4096
- Intermediate Size: 16384

**Mistral 7B:**
- Layers: 32
- Hidden Size: 4096
- Intermediate Size: 14336

**Phi-2 2.7B:**
- Layers: 32
- Hidden Size: 2560
- Intermediate Size: 10240

---

## Command-Line Interfaces

### activation.py

Record neuron activations for a specific language.

**Arguments:**
- `-m, --model` (str): Model name or path (e.g., `meta-llama/Llama-2-7b-hf`)
- `-l, --language` (str): Language code (en, zh, fr, es, vi, id, ja)

**Example:**
```bash
CUDA_VISIBLE_DEVICES=0 python activation.py -m meta-llama/Llama-2-7b-hf -l zh
```

### identify.py

Identify language-specific neurons from recorded activations.

**Arguments:**
None (uses pre-recorded activation files)

**Example:**
```bash
python identify.py
```

### ppl.py

Compute perplexity with neuron deactivation.

**Arguments:**
- `-m, --model` (str): Model name or path
- `-a, --activation-mask` (str): Path to activation mask file

**Example:**
```bash
CUDA_VISIBLE_DEVICES=0 python ppl.py -m meta-llama/Llama-2-7b-hf -a activation_mask/chinese.pth
```

### generation.py

Generate text with selective neuron deactivation.

**Arguments:**
- `-m, --model` (str): Model name or path
- `-a, --activation-mask` (str): Path to activation mask file

**Example:**
```bash
CUDA_VISIBLE_DEVICES=0 python generation.py -m meta-llama/Llama-2-7b-hf -a activation_mask/chinese.pth
```

---

## File Formats

### Tokenized Data Format

Pre-tokenized data for perplexity computation:
- Format: PyTorch LongTensor
- Location: `data/id.{lang}.train.llama`
- Content: Concatenated token IDs

### Test Prompts Format

Generation test prompts:
- Format: Plain text files
- Location: `data/mvicuna/{lang}.txt`
- Content: One prompt per line

### Activation Files Format

Recorded activation states:
- Format: Binary activation data
- Location: `activations/activation.{lang}.train.{model}`
- Content: Layer-wise activation values

---

## Usage Patterns

### Basic Neuron Analysis Workflow

1. **Record Activations:**
```bash
python activation.py -m meta-llama/Llama-2-7b-hf -l zh
```

2. **Identify Neurons:**
```bash
python identify.py
```

3. **Create Deactivation Mask:**
```python
import torch

neurons = torch.load('LLaMA-2-7B.neuron.pth')
# Create mask for Chinese neurons
chinese_neurons = neurons[1]  # Language index 1 = Chinese
```

4. **Test with Deactivation:**
```bash
python ppl.py -m meta-llama/Llama-2-7b-hf -a activation_mask/chinese.pth
```

### Cross-lingual Analysis Pattern

```python
import torch

# Load neurons for multiple models
llama_neurons = torch.load('LLaMA-2-7B.neuron.pth')
bloom_neurons = torch.load('BLOOM-7B.neuron.pth')

# Compare Chinese neurons across models
llama_chinese = set(llama_neurons[1][0].tolist())  # Layer 0
bloom_chinese = set(bloom_neurons[1][0].tolist())  # Layer 0

# Find common neurons
common = llama_chinese & bloom_chinese
print(f"Common Chinese neurons: {len(common)}")
```

---

## Error Handling

### Common Issues and Solutions

**CUDA Out of Memory:**
- Reduce batch size in data loaders
- Use smaller model variants
- Clear GPU cache: `torch.cuda.empty_cache()`

**File Not Found:**
- Ensure activation recording completed before identification
- Check file paths match expected patterns
- Verify data preparation steps completed

**Version Compatibility:**
- Use `vllm==0.2.7` as specified
- Ensure PyTorch version matches CUDA version
- Check model compatibility with library versions

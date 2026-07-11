# Rope with LLM API Reference

## Core Modules

### Module: llm_example_save_attn

Main module for saving and analyzing attention weights from various LLMs.

#### Function: run_jamba(prompt: str, tokenizer, model) -> Dict
Execute Jamba model inference and extract attention states.

**Parameters:**
- `prompt` (str): Input text prompt for the model
- `tokenizer`: Initialized tokenizer for the Jamba model
- `model`: Loaded Jamba model instance

**Returns:**
- Dictionary containing attention weights and model outputs

**Example:**
```python
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("ai21labs/Jamba-v0.1")
model = AutoModelForCausalLM.from_pretrained("ai21labs/Jamba-v0.1")
results = run_jamba("Explain quantum computing", tokenizer, model)
```

---

#### Function: run_qwen2vl(processor, model) -> Dict
Run Qwen2-VL vision-language model for multimodal analysis.

**Parameters:**
- `processor`: Qwen2VL processor for handling text and image inputs
- `model`: Loaded Qwen2-VL model instance

**Returns:**
- Dictionary containing multimodal attention patterns

---

#### Function: main(args) -> None
Main orchestration function for attention analysis experiments.

**Parameters:**
- `args`: Argument namespace containing:
  - `model_name` (str): HuggingFace model identifier
  - `pattern` (str): Dataset pattern to use
  - `round` (int): Number of rounds to run

---

### Module: modeling_gemma2

Custom Gemma2 model implementation with attention tracking.

#### Class: Gemma2RMSNorm
RMS Normalization layer for Gemma2 models.

**Constructor:**
```python
Gemma2RMSNorm(dim: int, eps: float = 1e-6)
```

**Parameters:**
- `dim` (int): Dimension of the input tensor
- `eps` (float): Small value to prevent division by zero

---

#### Class: Gemma2MLP
Multi-layer perceptron component of Gemma2.

**Constructor:**
```python
Gemma2MLP(config: Gemma2Config)
```

**Parameters:**
- `config`: Configuration object containing model hyperparameters

---

#### Class: Gemma2RotaryEmbedding
Rotary position embedding implementation for Gemma2.

**Constructor:**
```python
Gemma2RotaryEmbedding(dim: int, max_position_embeddings: int = 2048, base: int = 10000)
```

**Parameters:**
- `dim` (int): Dimension of the embedding
- `max_position_embeddings` (int): Maximum sequence length
- `base` (int): Base value for frequency calculation

---

#### Function: rotate_half(x: torch.Tensor) -> torch.Tensor
Rotate half the hidden dims of the input tensor.

**Parameters:**
- `x` (torch.Tensor): Input tensor of shape (batch, seq_len, heads, dim)

**Returns:**
- Rotated tensor with same shape

---

#### Function: apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]
Apply rotary position embeddings to query and key tensors.

**Parameters:**
- `q` (torch.Tensor): Query tensor
- `k` (torch.Tensor): Key tensor
- `cos` (torch.Tensor): Cosine positional encoding
- `sin` (torch.Tensor): Sine positional encoding

**Returns:**
- Tuple of (rotated_query, rotated_key)

---

#### Function: repeat_kv(hidden_states: torch.Tensor, n_rep: int) -> torch.Tensor
Repeat key/value heads to match query heads for multi-query attention.

**Parameters:**
- `hidden_states` (torch.Tensor): Key or value states
- `n_rep` (int): Number of repetitions

**Returns:**
- Repeated tensor with expanded heads

---

### Module: modeling_llama

Llama model implementation with massive value tracking.

#### Global Variables
- `GLOBAL_L` (int): Current layer index for attention saving
- `add_mean_perturbation` (bool): Flag to enable mean value perturbation
- `add_other_perturbation` (bool): Flag to enable other value perturbation

#### Attention State Saving
The module includes hooks for saving attention states at specified layers:

```python
if GLOBAL_L in [1, 2, 10]:
    torch.save(query_states, f"{save_dir}/q_merged_attn_weights_layer{GLOBAL_L}.pt")
    torch.save(key_states, f"{save_dir}/k_merged_attn_weights_layer{GLOBAL_L}.pt")
    torch.save(value_states, f"{save_dir}/v_merged_attn_weights_layer{GLOBAL_L}.pt")
```

#### Massive Value Disruption
Apply perturbations to massive values in attention matrices:

```python
if add_mean_perturbation:
    # Identify outliers
    values, indices = torch.topk(outlier, num_outliers)
    # Replace with mean
    for idx in top_indices:
        query_states[:, :, head_idx, idx] = mean_value
```

---

### Module: modeling_gpt2

GPT-2 model components with attention analysis capabilities.

#### Class: GPT2Attention
Multi-headed attention implementation for GPT-2.

**Constructor:**
```python
GPT2Attention(config: GPT2Config, is_cross_attention: bool = False, layer_idx: int = None)
```

**Parameters:**
- `config`: GPT-2 configuration object
- `is_cross_attention` (bool): Whether this is cross-attention
- `layer_idx` (int): Index of the layer

---

#### Class: GPT2MLP
Feed-forward network for GPT-2.

**Constructor:**
```python
GPT2MLP(intermediate_size: int, config: GPT2Config)
```

**Parameters:**
- `intermediate_size` (int): Size of intermediate layer
- `config`: GPT-2 configuration

---

#### Class: GPT2Block
Complete transformer block for GPT-2.

**Constructor:**
```python
GPT2Block(config: GPT2Config, layer_idx: int = None)
```

---

#### Function: load_tf_weights_in_gpt2(model, config, gpt2_checkpoint_path) -> None
Load TensorFlow checkpoint weights into PyTorch GPT-2 model.

**Parameters:**
- `model`: PyTorch GPT-2 model instance
- `config`: Model configuration
- `gpt2_checkpoint_path` (str): Path to TensorFlow checkpoint

---

#### Function: eager_attention_forward(module, query, key, value, attention_mask) -> Tuple
Forward pass for eager attention computation.

**Parameters:**
- `module`: Attention module
- `query` (torch.Tensor): Query tensor
- `key` (torch.Tensor): Key tensor
- `value` (torch.Tensor): Value tensor
- `attention_mask` (torch.Tensor, optional): Attention mask

**Returns:**
- Tuple of (attention_output, attention_weights)

---

### Module: modeling_gpt_neo

GPT-Neo model implementation.

#### Class: GPTNeoSelfAttention
Self-attention mechanism for GPT-Neo.

**Constructor:**
```python
GPTNeoSelfAttention(config: GPTNeoConfig, attention_type: str)
```

**Parameters:**
- `config`: GPT-Neo configuration
- `attention_type` (str): Type of attention ('global' or 'local')

---

#### Class: GPTNeoAttention
Complete attention block for GPT-Neo.

**Constructor:**
```python
GPTNeoAttention(config: GPTNeoConfig, layer_id: int = 0)
```

---

#### Class: GPTNeoMLP
MLP block for GPT-Neo.

**Constructor:**
```python
GPTNeoMLP(intermediate_size: int, config: GPTNeoConfig)
```

---

#### Function: load_tf_weights_in_gpt_neo(model, config, gpt_neo_checkpoint_path) -> None
Load TensorFlow weights into GPT-Neo model.

---

### Module: modeling_gpt_neox

GPT-NeoX model implementation with RoPE.

#### Class: GPTNeoXMLP
Feed-forward network for GPT-NeoX.

**Constructor:**
```python
GPTNeoXMLP(config: GPTNeoXConfig)
```

---

#### Class: GPTNeoXAttention
Attention mechanism with rotary embeddings.

**Constructor:**
```python
GPTNeoXAttention(config: GPTNeoXConfig, layer_idx: int = None)
```

---

#### Class: GPTNeoXLayer
Complete transformer layer for GPT-NeoX.

**Constructor:**
```python
GPTNeoXLayer(config: GPTNeoXConfig, layer_idx: int = None)
```

---

#### Function: rotate_half(x: torch.Tensor) -> torch.Tensor
Rotate half of the hidden dimensions for RoPE.

---

#### Function: apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> Tuple
Apply rotary position embeddings to queries and keys.

---

### Module: Quantization Methods

#### AWQ (Activation-aware Weight Quantization)
Configuration for AWQ quantization:
```python
awq_config = {
    'bits': 4,
    'group_size': 128,
    'zero_point': True
}
```

#### SmoothQuant
Configuration for SmoothQuant:
```python
smooth_quant_config = {
    'alpha': 0.5,
    'migration_strength': 0.1
}
```

#### GPTQ
Configuration for GPTQ:
```python
gptq_config = {
    'bits': 4,
    'dataset': 'c4',
    'nsamples': 128,
    'group_size': 128
}
```

---

## Dataset Generation

### Passkey Retrieval Dataset

#### Parameters:
- `seq_length` (int): Total sequence length (minimum 101)
- `begin_pos` (int): Starting position for passkey insertion
- `passkey_length` (int): Length of the passkey
- `num_gen_example` (int): Number of examples to generate
- `max_data_num` (int): Maximum dataset size

### Knowledge QA Dataset

#### Function: create_knowledge_qa(category: str, num_pairs: int) -> List[Dict]
Generate knowledge question-answer pairs.

**Parameters:**
- `category` (str): Category of knowledge ('city', 'aqua', 'imdb', 'sports', 'art', 'cele', 'long')
- `num_pairs` (int): Number of QA pairs to generate

**Returns:**
- List of dictionaries containing context, question, and answer

---

## Visualization

### Attention Map Visualization

#### Function: visualize_attention_map(attention_weights: torch.Tensor, save_path: str) -> None
Create heatmap visualization of attention weights.

**Parameters:**
- `attention_weights` (torch.Tensor): Attention weight tensor
- `save_path` (str): Path to save the visualization

### Massive Value Distribution

#### Function: plot_massive_value_distribution(values: Dict, layer_idx: int) -> None
Plot the distribution of massive values across heads and positions.

**Parameters:**
- `values` (Dict): Dictionary containing massive value positions and magnitudes
- `layer_idx` (int): Layer index for the title

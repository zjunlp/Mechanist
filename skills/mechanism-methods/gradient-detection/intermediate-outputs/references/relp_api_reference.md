# RelP API Reference

## Module: transformer_lens

Enhanced version of TransformerLens with Layer-wise Relevance Propagation (LRP) support for circuit discovery in language models.

### Class: HookedTransformer

Main model class for transformer models with hooks and LRP capabilities.

**Constructor:**
```python
HookedTransformer.from_pretrained(
    model_name: str,
    checkpoint_index: Optional[int] = None,
    checkpoint_value: Optional[int] = None,
    hf_model: Optional[Any] = None,
    device: Optional[str] = None,
    n_devices: int = 1,
    tokenizer: Optional[Any] = None,
    dtype: Optional[torch.dtype] = torch.float32,
    default_padding_side: str = "right",
    **from_pretrained_kwargs
) -> HookedTransformer
```

**Parameters:**
- `model_name` (str): Name of pretrained model (e.g., "gpt2-small", "gpt2-medium", "gpt2-large")
- `checkpoint_index` (int, optional): Checkpoint index for models with multiple checkpoints
- `checkpoint_value` (int, optional): Checkpoint value for loading specific training steps
- `hf_model` (optional): Pre-loaded HuggingFace model
- `device` (str, optional): Device to load model on ("cuda", "cpu", "mps")
- `n_devices` (int): Number of devices for model parallelism
- `tokenizer` (optional): Custom tokenizer to use
- `dtype` (torch.dtype): Data type for model weights
- `default_padding_side` (str): Padding side for tokenization

**Methods:**

#### run_with_cache(input, return_type: Optional[str] = "logits", **kwargs) -> Tuple[torch.Tensor, ActivationCache]
Execute forward pass and cache all intermediate activations.

**Parameters:**
- `input` (Union[str, List[str], torch.Tensor]): Input text or token ids
- `return_type` (str): Type of output to return ("logits", "loss", "both")
- `kwargs`: Additional arguments for forward pass

**Returns:**
- `Tuple[torch.Tensor, ActivationCache]`: Model output and activation cache

**Example:**
```python
model = HookedTransformer.from_pretrained("gpt2-small")
model.cfg.use_lrp = True
logits, cache = model.run_with_cache("Hello world")
```

#### to_tokens(input: Union[str, List[str]], prepend_bos: bool = True) -> torch.Tensor
Convert text input to token tensors.

**Parameters:**
- `input` (Union[str, List[str]]): Text to tokenize
- `prepend_bos` (bool): Whether to prepend beginning-of-sequence token

**Returns:**
- `torch.Tensor`: Token tensor of shape [batch, sequence_length]

#### to_str_tokens(input: Union[str, torch.Tensor], prepend_bos: bool = True) -> List[str]
Convert input to list of string tokens.

**Parameters:**
- `input` (Union[str, torch.Tensor]): Input text or token ids
- `prepend_bos` (bool): Whether to include BOS token

**Returns:**
- `List[str]`: List of token strings

#### to_single_token(token_str: str) -> int
Convert a single token string to token id.

**Parameters:**
- `token_str` (str): Token string

**Returns:**
- `int`: Token id

#### to_single_str_token(token_id: int) -> str
Convert token id to string representation.

**Parameters:**
- `token_id` (int): Token id

**Returns:**
- `str`: Token string

---

### Class: HookedTransformerConfig

Configuration class for HookedTransformer models with LRP settings.

**Key Attributes:**

#### use_lrp: bool = False
Enable Layer-wise Relevance Propagation for circuit discovery.

#### LRP_rules: List[str] = []
List of LRP propagation rules to apply. Available rules:
- `"LN-rule"`: For LayerNorm/RMSNorm layers
- `"Identity-rule"`: For activation functions (GELU, ReLU)
- `"0-rule"`: For linear layers
- `"AH-rule"`: For attention mechanisms
- `"Half-rule"`: For multiplicative gates

**Example:**
```python
model.cfg.use_lrp = True
model.cfg.LRP_rules = ['LN-rule', 'Identity-rule', 'Half-rule']
```

#### n_layers: int
Number of transformer layers in the model.

#### n_heads: int
Number of attention heads per layer.

#### d_model: int
Hidden dimension size of the model.

#### d_head: int
Dimension of each attention head.

#### d_mlp: int
Dimension of MLP hidden layer.

#### d_vocab: int
Vocabulary size of the model.

---

### Class: ActivationCache

Cache for storing and accessing model activations during forward pass.

**Methods:**

#### __getitem__(key: str) -> torch.Tensor
Access cached activation by key.

**Parameters:**
- `key` (str): Activation key (e.g., "blocks.0.attn.hook_pattern")

**Returns:**
- `torch.Tensor`: Cached activation tensor

#### __contains__(key: str) -> bool
Check if activation key exists in cache.

**Parameters:**
- `key` (str): Activation key to check

**Returns:**
- `bool`: True if key exists in cache

#### keys() -> List[str]
Get all activation keys in cache.

**Returns:**
- `List[str]`: List of all cached activation keys

#### apply_ln_to_stack(stack: torch.Tensor, layer: int, pos_slice: slice = slice(None)) -> torch.Tensor
Apply layer normalization to residual stream stack.

**Parameters:**
- `stack` (torch.Tensor): Residual stream tensor
- `layer` (int): Layer index
- `pos_slice` (slice): Position slice to apply normalization

**Returns:**
- `torch.Tensor`: Normalized tensor

---

## LRP Propagation Rules

### LN-rule
Propagation rule for LayerNorm and RMSNorm layers that preserves relevance through normalization.

**Reference:** [Ali et al., 2022](https://proceedings.mlr.press/v162/ali22a.html)

### Identity-rule
Propagation rule for activation functions (GELU, ReLU, etc.) that passes relevance unchanged.

**Reference:** [Jafari et al., 2024](https://neurips.cc/virtual/2024/poster/96794)

### 0-rule (Epsilon-rule)
Standard LRP rule for linear layers with numerical stability.

**Reference:** [Montavon et al., 2019](https://iphome.hhi.de/samek/pdf/MonXAI19.pdf)

### AH-rule
Specialized rule for attention head mechanisms in transformers.

**Reference:** [Ali et al., 2022](https://proceedings.mlr.press/v162/ali22a.html)

### Half-rule
Propagation rule for multiplicative gates that splits relevance equally.

**References:** 
- [Jafari et al., 2024](https://neurips.cc/virtual/2024/poster/96794)
- [Arras et al., 2019](https://link.springer.com/chapter/10.1007/978-3-030-28954-6_11)

---

## Hook Points

Common hook points for accessing model internals:

### Attention Hooks
- `blocks.{layer}.attn.hook_q`: Query vectors
- `blocks.{layer}.attn.hook_k`: Key vectors
- `blocks.{layer}.attn.hook_v`: Value vectors
- `blocks.{layer}.attn.hook_pattern`: Attention patterns
- `blocks.{layer}.attn.hook_result`: Per-head attention outputs
- `blocks.{layer}.hook_attn_out`: Combined attention output

### MLP Hooks
- `blocks.{layer}.mlp.hook_pre`: MLP pre-activation
- `blocks.{layer}.mlp.hook_post`: MLP post-activation
- `blocks.{layer}.hook_mlp_out`: MLP output

### Residual Stream Hooks
- `blocks.{layer}.hook_resid_pre`: Residual stream before layer
- `blocks.{layer}.hook_resid_mid`: Residual stream after attention
- `blocks.{layer}.hook_resid_post`: Residual stream after layer

### Embedding/Output Hooks
- `hook_embed`: Token embeddings
- `hook_pos_embed`: Positional embeddings
- `ln_final.hook_normalized`: Final layer norm output

---

## Utility Functions

### get_ioi_tokens_and_answer_tokens(model: HookedTransformer) -> Tuple[torch.Tensor, torch.Tensor]
Generate tokens for Indirect Object Identification task.

**Located in:** TransformerLens/tests/acceptance/test_activation_cache.py

**Parameters:**
- `model` (HookedTransformer): Model to generate tokens for

**Returns:**
- `Tuple[torch.Tensor, torch.Tensor]`: IOI tokens and expected answer tokens

### load_model(name: str) -> HookedTransformer
Load a pretrained model by name.

**Located in:** TransformerLens/tests/acceptance/test_activation_cache.py

**Parameters:**
- `name` (str): Model name

**Returns:**
- `HookedTransformer`: Loaded model

---

## Example Usage Patterns

### Basic Circuit Discovery with RelP
```python
import transformer_lens

# Setup model with LRP
model = transformer_lens.HookedTransformer.from_pretrained("gpt2-small")
model.cfg.use_lrp = True
model.cfg.LRP_rules = ['LN-rule', 'Identity-rule', 'Half-rule']

# Analyze text
text = "The capital of France is Paris"
logits, cache = model.run_with_cache(text)

# Access specific activations
attn_pattern = cache["blocks.5.attn.hook_pattern"]  # Layer 5 attention
mlp_out = cache["blocks.5.hook_mlp_out"]  # Layer 5 MLP output
```

### Comparing Methods
```python
# RelP analysis
model.cfg.use_lrp = True
relp_logits, relp_cache = model.run_with_cache(text)

# Standard attribution
model.cfg.use_lrp = False
attr_logits, attr_cache = model.run_with_cache(text)

# Compare results
relp_relevance = relp_cache["blocks.5.hook_mlp_out"].abs().mean()
attr_relevance = attr_cache["blocks.5.hook_mlp_out"].abs().mean()
```

### IOI Task Analysis
```python
# Prepare IOI example
ioi_text = "When Mary and John went to the store, John gave a drink to"
tokens = model.to_tokens(ioi_text)

# Get predictions
logits, cache = model.run_with_cache(tokens)

# Analyze attention to names
mary_pos = 1  # Position of "Mary" token
john_pos = 3  # Position of "John" token

for layer in range(model.cfg.n_layers):
    attn = cache[f"blocks.{layer}.attn.hook_pattern"]
    # Attention from last position to name positions
    mary_attn = attn[0, :, -1, mary_pos].mean()
    john_attn = attn[0, :, -1, john_pos].mean()
    print(f"Layer {layer}: Mary={mary_attn:.3f}, John={john_attn:.3f}")
```

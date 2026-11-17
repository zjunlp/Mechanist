# Dissecting Factual Predictions API Reference

## Module: utils

### Class: ModelAndTokenizer

An object to hold a GPT-style language model and tokenizer for factual association analysis.

**Location:** `dissecting_factual_predictions/utils.py`

**Constructor:**
```python
ModelAndTokenizer(
    model_name: str = "gpt2",
    device: str = None
)
```

**Parameters:**
- `model_name` (str): Name of the model to load from Huggingface (e.g., "gpt2", "gpt2-xl", "EleutherAI/gpt-j-6B")
- `device` (str, optional): Device to load model on ("cuda", "cpu"). Auto-detects if not specified.

**Attributes:**
- `model`: The loaded language model
- `tokenizer`: The associated tokenizer
- `device`: The device the model is loaded on

---

### Function: make_inputs

Create model inputs from a list of text prompts.

**Location:** `dissecting_factual_predictions/utils.py`

**Signature:**
```python
make_inputs(
    tokenizer: PreTrainedTokenizer,
    prompts: Union[str, List[str]],
    device: torch.device
) -> BatchEncoding
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizer): Tokenizer instance for encoding text
- `prompts` (str or List[str]): Single prompt or list of prompts to encode
- `device` (torch.device): Device to place tensors on

**Returns:**
- `BatchEncoding`: Dictionary-like object containing input_ids and attention_mask tensors

**Example:**
```python
inputs = make_inputs(tokenizer, ["The capital of France is"], device)
outputs = model(**inputs)
```

---

### Function: decode_tokens

Decode a tensor of token IDs back to text.

**Location:** `dissecting_factual_predictions/utils.py`

**Signature:**
```python
decode_tokens(
    tokenizer: PreTrainedTokenizer,
    token_array: torch.Tensor
) -> Union[str, List[str]]
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizer): Tokenizer instance for decoding
- `token_array` (torch.Tensor): Tensor of token IDs to decode

**Returns:**
- `str` or `List[str]`: Decoded text string(s)

**Example:**
```python
text = decode_tokens(tokenizer, output_ids)
print(f"Generated text: {text}")
```

---

### Function: find_token_range

Find the token indices corresponding to a substring within tokenized text.

**Location:** `dissecting_factual_predictions/utils.py`

**Signature:**
```python
find_token_range(
    tokenizer: PreTrainedTokenizer,
    token_array: torch.Tensor,
    substring: str
) -> Tuple[int, int]
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizer): Tokenizer instance
- `token_array` (torch.Tensor): Tensor of token IDs
- `substring` (str): Substring to locate in the tokenized text

**Returns:**
- `Tuple[int, int]`: Start and end indices of the substring in the token array

**Example:**
```python
start, end = find_token_range(tokenizer, input_ids, "France")
relevant_tokens = input_ids[start:end]
```

---

## Notebook Sections API

The main Jupyter notebook (`factual_associations_dissection.ipynb`) provides several key experimental functions:

### Information Flow Analysis

#### attention_knockout

Perform attention knockout to study information flow.

**Signature:**
```python
attention_knockout(
    model: GPT2LMHeadModel,
    layer_idx: int,
    head_idx: int,
    input_ids: torch.Tensor
) -> Dict[str, Any]
```

**Parameters:**
- `model`: The GPT-2 model instance
- `layer_idx`: Index of the layer to perform knockout on (0 to n_layers-1)
- `head_idx`: Index of the attention head to knockout (0 to n_heads-1)
- `input_ids`: Input token IDs

**Returns:**
- Dictionary containing original and knockout predictions, probability changes

---

### Attribute Extraction

#### project_to_vocabulary

Project hidden states to vocabulary space.

**Signature:**
```python
project_to_vocabulary(
    hidden_state: torch.Tensor,
    model: GPT2LMHeadModel
) -> torch.Tensor
```

**Parameters:**
- `hidden_state`: Hidden state tensor to project (shape: [batch, seq_len, hidden_dim])
- `model`: The GPT-2 model instance (uses lm_head for projection)

**Returns:**
- `torch.Tensor`: Vocabulary logits (shape: [batch, seq_len, vocab_size])

---

#### patch_hidden_state

Patch hidden states from one computation into another.

**Signature:**
```python
patch_hidden_state(
    model: GPT2LMHeadModel,
    source_hidden: torch.Tensor,
    target_position: int,
    layer_idx: int
) -> None
```

**Parameters:**
- `model`: The GPT-2 model instance
- `source_hidden`: Hidden state to patch in
- `target_position`: Position in sequence to patch
- `layer_idx`: Layer at which to perform patching

---

### Subject Enrichment Evaluation

#### sublayer_knockout

Knockout entire sublayers to evaluate their contribution.

**Signature:**
```python
sublayer_knockout(
    model: GPT2LMHeadModel,
    layer_idx: int,
    sublayer_type: str,
    input_ids: torch.Tensor
) -> Dict[str, Any]
```

**Parameters:**
- `model`: The GPT-2 model instance
- `layer_idx`: Index of the layer
- `sublayer_type`: Type of sublayer ("attn" or "mlp")
- `input_ids`: Input token IDs

**Returns:**
- Dictionary with prediction changes and importance scores

---

## Model Architecture References

### GPT-2 Module Names

For hooking and intervention purposes:

**Transformer Blocks:**
- `model.transformer.h[i]` - i-th transformer block (0 to n_layers-1)

**Attention Components:**
- `model.transformer.h[i].attn` - Attention module
- `model.transformer.h[i].attn.c_attn` - Query, Key, Value projection
- `model.transformer.h[i].attn.c_proj` - Output projection

**MLP Components:**
- `model.transformer.h[i].mlp` - MLP module
- `model.transformer.h[i].mlp.c_fc` - First linear layer (expansion)
- `model.transformer.h[i].mlp.c_proj` - Second linear layer (compression)

**Layer Normalization:**
- `model.transformer.h[i].ln_1` - Pre-attention layer norm
- `model.transformer.h[i].ln_2` - Pre-MLP layer norm
- `model.transformer.ln_f` - Final layer norm

**Embeddings and Output:**
- `model.transformer.wte` - Token embeddings
- `model.transformer.wpe` - Position embeddings
- `model.lm_head` - Language modeling head (vocabulary projection)

### GPT-J Module Names

For adapting code to GPT-J models:

**Key Differences:**
- MLP first layer: `fc_in` (instead of `c_fc`)
- MLP second layer: `fc_out` (instead of `c_proj`)
- Attention uses different internal structure

**Example Adaptation:**
```python
if model_type == "gptj":
    mlp_first = model.transformer.h[i].mlp.fc_in
    mlp_second = model.transformer.h[i].mlp.fc_out
else:  # gpt2
    mlp_first = model.transformer.h[i].mlp.c_fc
    mlp_second = model.transformer.h[i].mlp.c_proj
```

---

## Hook Registration Examples

### Forward Hook for Activation Extraction

```python
def get_activation(name):
    def hook(module, input, output):
        activations[name] = output.detach()
    return hook

# Register hook
handle = model.transformer.h[5].mlp.register_forward_hook(
    get_activation('layer_5_mlp')
)

# Run forward pass
outputs = model(**inputs)

# Access stored activation
mlp_output = activations['layer_5_mlp']

# Remove hook
handle.remove()
```

### Intervention Hook for Knockout

```python
def knockout_hook(module, input, output):
    # Zero out the output
    if isinstance(output, tuple):
        return (torch.zeros_like(output[0]),) + output[1:]
    return torch.zeros_like(output)

# Apply to specific sublayer
handle = model.transformer.h[3].attn.register_forward_hook(knockout_hook)
```

---

## Data Formats

### Input Format
- Text prompts as strings
- Tokenized inputs as PyTorch tensors
- Batch processing supported

### Output Format
- Predictions as token IDs or decoded text
- Probabilities as float tensors
- Analysis results as dictionaries with layer-wise information

### Evaluation Data
The notebook expects evaluation data in the following format:
- Factual queries with known answers
- Format: `(prompt, expected_attribute)`
- Example: `("The capital of France is", "Paris")`

---

## External Tool Integration

### LM-Debugger Integration
For MLP parameter interpretation:
- Repository: https://github.com/mega002/lm-debugger
- Used for vocabulary projection of MLP parameters
- Provides interpretable views of MLP contributions

### Embedding Space Analysis
For attention head interpretation:
- Repository: https://github.com/guyd1995/embedding-space
- Method from Dar et al., ACL 2023
- Projects attention parameters to vocabulary space

---

## Performance Considerations

### GPU Requirements
- **GPT2-base/medium:** Any modern GPU (8GB+ VRAM)
- **GPT2-large:** 16GB+ VRAM recommended
- **GPT2-xl:** V100 (16GB) or better
- **GPT-J-6B:** A100 (40GB) required

### Batch Processing
- Use batched inputs for efficiency
- Clear GPU cache between experiments: `torch.cuda.empty_cache()`

### Memory Management
- Use `torch.no_grad()` for inference
- Detach tensors when storing: `.detach()`
- Remove hooks after use: `handle.remove()`

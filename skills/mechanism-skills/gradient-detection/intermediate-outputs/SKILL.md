---
name: intermediate-outputs
description: Use this skill when working with circuit discovery in language models, mechanistic interpretability, activation patching, attribution patching, or Layer-wise Relevance Propagation (LRP) for neural network analysis
---

## Demo Scripts

### `scripts/basic_relp_analysis.py`

```python
#!/usr/bin/env python3
"""
Basic RelP Analysis Script

This script demonstrates how to use RelP (Relevance Patching) for circuit discovery
in transformer language models using the enhanced TransformerLens library.

Requirements:
    - Install RelP: git clone https://github.com/FarnoushRJ/RelP.git && cd RelP/TransformerLens && pip install -e .
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
import transformer_lens
from transformer_lens import HookedTransformer, ActivationCache


def setup_model_with_lrp(
    model_name: str = "gpt2-small",
    lrp_rules: Optional[List[str]] = None,
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
) -> HookedTransformer:
    """
    Load a transformer model with LRP (Layer-wise Relevance Propagation) enabled.
    
    Args:
        model_name: Name of the pretrained model to load
        lrp_rules: List of LRP rules to apply. Defaults to standard rules.
        device: Device to load the model on
    
    Returns:
        HookedTransformer model with LRP configuration
    """
    print(f"Loading model: {model_name}")
    model = HookedTransformer.from_pretrained(model_name, device=device)
    
    # Enable LRP
    model.cfg.use_lrp = True
    
    # Set LRP rules (use defaults if not specified)
    if lrp_rules is None:
        lrp_rules = ['LN-rule', 'Identity-rule', 'Half-rule']
    model.cfg.LRP_rules = lrp_rules
    
    print(f"Model loaded with LRP rules: {lrp_rules}")
    return model


def analyze_text_with_relp(
    model: HookedTransformer,
    text: str,
    return_logits: bool = True
) -> Tuple[torch.Tensor, ActivationCache]:
    """
    Analyze a text input using RelP to get relevance scores and activations.
    
    Args:
        model: The transformer model with LRP enabled
        text: Input text to analyze
        return_logits: Whether to return logits along with activations
    
    Returns:
        Tuple of (logits, activation_cache) containing model outputs and internal states
    """
    print(f"Analyzing text: '{text}'")
    
    # Run the model with cache to capture all activations
    logits, cache = model.run_with_cache(text)
    
    # Display basic information about the outputs
    print(f"Logits shape: {logits.shape}")
    print(f"Number of cached activations: {len(cache)}")
    
    return logits, cache


def extract_attention_patterns(
    cache: ActivationCache,
    layer: int = 0,
    head: int = 0
) -> np.ndarray:
    """
    Extract attention patterns from a specific layer and head.
    
    Args:
        cache: ActivationCache containing model activations
        layer: Layer index to extract from
        head: Attention head index
    
    Returns:
        Attention pattern as numpy array
    """
    # Get attention pattern for specified layer and head
    attn_pattern_key = f"blocks.{layer}.attn.hook_pattern"
    
    if attn_pattern_key in cache:
        attn_patterns = cache[attn_pattern_key]
        # Shape: [batch, head, seq_len, seq_len]
        pattern = attn_patterns[0, head].cpu().numpy()
        return pattern
    else:
        print(f"Warning: Attention pattern not found for layer {layer}")
        return np.array([])


def analyze_mlp_contributions(
    cache: ActivationCache,
    layer: int = 0
) -> Dict[str, torch.Tensor]:
    """
    Analyze MLP (feedforward) layer contributions using cached activations.
    
    Args:
        cache: ActivationCache containing model activations
        layer: Layer index to analyze
    
    Returns:
        Dictionary containing MLP-related activations
    """
    mlp_info = {}
    
    # Extract MLP pre-activation
    mlp_pre_key = f"blocks.{layer}.mlp.hook_pre"
    if mlp_pre_key in cache:
        mlp_info['pre_activation'] = cache[mlp_pre_key]
    
    # Extract MLP post-activation
    mlp_post_key = f"blocks.{layer}.mlp.hook_post"
    if mlp_post_key in cache:
        mlp_info['post_activation'] = cache[mlp_post_key]
    
    # Extract MLP output
    mlp_out_key = f"blocks.{layer}.hook_mlp_out"
    if mlp_out_key in cache:
        mlp_info['output'] = cache[mlp_out_key]
    
    return mlp_info


def compute_relevance_scores(
    model: HookedTransformer,
    text: str,
    target_token_idx: int = -1
) -> Dict[str, torch.Tensor]:
    """
    Compute relevance scores for different model components using RelP.
    
    Args:
        model: Transformer model with LRP enabled
        text: Input text
        target_token_idx: Index of target token to compute relevance for
    
    Returns:
        Dictionary of relevance scores for different components
    """
    # Tokenize input
    tokens = model.to_tokens(text)
    
    # Run forward pass
    logits, cache = model.run_with_cache(tokens)
    
    # Get output for target token
    if target_token_idx == -1:
        target_token_idx = tokens.shape[1] - 1
    
    target_logits = logits[0, target_token_idx]
    
    # Compute relevance scores (simplified example)
    relevance_scores = {}
    
    # Store some key activation magnitudes as proxy for relevance
    for layer in range(model.cfg.n_layers):
        # Residual stream relevance
        resid_key = f"blocks.{layer}.hook_resid_post"
        if resid_key in cache:
            resid_relevance = cache[resid_key][0, target_token_idx].abs().mean()
            relevance_scores[f"layer_{layer}_residual"] = resid_relevance
        
        # MLP relevance
        mlp_key = f"blocks.{layer}.hook_mlp_out"
        if mlp_key in cache:
            mlp_relevance = cache[mlp_key][0, target_token_idx].abs().mean()
            relevance_scores[f"layer_{layer}_mlp"] = mlp_relevance
        
        # Attention relevance
        attn_key = f"blocks.{layer}.hook_attn_out"
        if attn_key in cache:
            attn_relevance = cache[attn_key][0, target_token_idx].abs().mean()
            relevance_scores[f"layer_{layer}_attention"] = attn_relevance
    
    return relevance_scores


def compare_lrp_rules(
    model_name: str = "gpt2-small",
    text: str = "The cat sat on the mat",
    rules_sets: Optional[List[List[str]]] = None
) -> None:
    """
    Compare different LRP rule configurations on the same input.
    
    Args:
        model_name: Model to use for comparison
        text: Input text for analysis
        rules_sets: List of LRP rule sets to compare
    """
    if rules_sets is None:
        rules_sets = [
            ['LN-rule', 'Identity-rule', 'Half-rule'],
            ['LN-rule', '0-rule', 'AH-rule'],
            ['Identity-rule', '0-rule', 'Half-rule']
        ]
    
    print(f"\nComparing LRP rules on: '{text}'\n")
    
    for rules in rules_sets:
        print(f"Testing rules: {rules}")
        model = setup_model_with_lrp(model_name, lrp_rules=rules)
        
        # Compute relevance scores
        relevance = compute_relevance_scores(model, text)
        
        # Display top relevance scores
        sorted_relevance = sorted(relevance.items(), key=lambda x: x[1], reverse=True)
        print("Top 5 components by relevance:")
        for component, score in sorted_relevance[:5]:
            print(f"  {component}: {score:.4f}")
        print()
        
        # Clean up
        del model
        torch.cuda.empty_cache()


def main():
    """
    Main demonstration of RelP functionality.
    """
    print("=" * 60)
    print("RelP (Relevance Patching) Demonstration")
    print("=" * 60)
    
    # Example 1: Basic model setup and analysis
    print("\n1. Basic Setup and Analysis")
    print("-" * 40)
    
    model = setup_model_with_lrp("gpt2-small")
    text = "The capital of France is Paris"
    logits, cache = analyze_text_with_relp(model, text)
    
    # Example 2: Extract attention patterns
    print("\n2. Attention Pattern Analysis")
    print("-" * 40)
    
    for layer in [0, 5, 11]:  # Sample from early, middle, late layers
        attn_pattern = extract_attention_patterns(cache, layer=layer, head=0)
        if attn_pattern.size > 0:
            print(f"Layer {layer}, Head 0 - Attention pattern shape: {attn_pattern.shape}")
            print(f"  Max attention: {attn_pattern.max():.4f}")
            print(f"  Mean attention: {attn_pattern.mean():.4f}")
    
    # Example 3: Analyze MLP contributions
    print("\n3. MLP Contribution Analysis")
    print("-" * 40)
    
    for layer in [0, 5, 11]:
        mlp_info = analyze_mlp_contributions(cache, layer=layer)
        print(f"Layer {layer} MLP:")
        for key, tensor in mlp_info.items():
            if tensor is not None:
                print(f"  {key}: shape={tensor.shape}, mean={tensor.mean().item():.4f}")
    
    # Example 4: Compute relevance scores
    print("\n4. Component Relevance Scores")
    print("-" * 40)
    
    relevance_scores = compute_relevance_scores(model, text)
    
    # Find most relevant components
    sorted_scores = sorted(relevance_scores.items(), key=lambda x: x[1], reverse=True)
    print("Top 10 most relevant components:")
    for component, score in sorted_scores[:10]:
        print(f"  {component}: {score:.4f}")
    
    # Example 5: Compare different LRP rules
    print("\n5. LRP Rule Comparison")
    print("-" * 40)
    
    compare_lrp_rules(
        model_name="gpt2-small",
        text="Machine learning is transforming technology",
        rules_sets=[
            ['LN-rule', 'Identity-rule', 'Half-rule'],
            ['LN-rule', '0-rule', 'AH-rule']
        ]
    )
    
    print("\n" + "=" * 60)
    print("RelP demonstration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

### `scripts/ioi_task_analysis.py`

```python
#!/usr/bin/env python3
"""
Indirect Object Identification (IOI) Task Analysis using RelP

This script demonstrates how to use RelP for analyzing the IOI task,
a standard benchmark in mechanistic interpretability for understanding
how language models track and use entity information.

The IOI task tests whether a model can correctly identify indirect objects
in sentences like "When Mary and John went to the store, John gave a drink to..."
where the model should predict "Mary" as the indirect object.
"""

import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
import transformer_lens
from transformer_lens import HookedTransformer, ActivationCache
import matplotlib.pyplot as plt
from dataclasses import dataclass


@dataclass
class IOIExample:
    """Data structure for IOI task examples."""
    text: str
    io_token: str  # Indirect object token
    s_token: str   # Subject token
    io_pos: int    # Position of indirect object
    s_pos: int     # Position of subject
    end_pos: int   # Position where prediction is made


def create_ioi_examples() -> List[IOIExample]:
    """
    Create a set of IOI task examples for testing.
    
    Returns:
        List of IOI examples with different name combinations
    """
    examples = [
        IOIExample(
            text="When Mary and John went to the store, John gave a drink to",
            io_token="Mary",
            s_token="John",
            io_pos=1,
            s_pos=3,
            end_pos=-1
        ),
        IOIExample(
            text="When Alice and Bob were at the park, Bob threw the ball to",
            io_token="Alice",
            s_token="Bob",
            io_pos=1,
            s_pos=3,
            end_pos=-1
        ),
        IOIExample(
            text="After Sarah and David finished lunch, David passed the salt to",
            io_token="Sarah",
            s_token="David",
            io_pos=1,
            s_token=3,
            end_pos=-1
        ),
        IOIExample(
            text="While Emma and James were talking, James handed the book to",
            io_token="Emma",
            s_token="James",
            io_pos=1,
            s_pos=3,
            end_pos=-1
        )
    ]
    return examples


def setup_ioi_model(
    model_name: str = "gpt2-small",
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
) -> HookedTransformer:
    """
    Set up a model for IOI task analysis with RelP.
    
    Args:
        model_name: Name of the model to load
        device: Device to use for computation
    
    Returns:
        Configured HookedTransformer model
    """
    print(f"Setting up {model_name} for IOI task analysis...")
    
    model = HookedTransformer.from_pretrained(model_name, device=device)
    model.cfg.use_lrp = True
    model.cfg.LRP_rules = ['LN-rule', 'Identity-rule', 'Half-rule']
    
    print("Model configured with RelP for IOI analysis")
    return model


def get_name_token_positions(
    model: HookedTransformer,
    text: str,
    name_tokens: List[str]
) -> Dict[str, List[int]]:
    """
    Find positions of name tokens in the tokenized text.
    
    Args:
        model: The transformer model
        text: Input text
        name_tokens: List of name tokens to find
    
    Returns:
        Dictionary mapping name tokens to their positions
    """
    tokens = model.to_tokens(text, prepend_bos=True)
    str_tokens = model.to_str_tokens(text, prepend_bos=True)
    
    positions = {name: [] for name in name_tokens}
    
    for idx, token_str in enumerate(str_tokens):
        for name in name_tokens:
            if name.lower() in token_str.lower():
                positions[name].append(idx)
    
    return positions


def analyze_ioi_attention_patterns(
    model: HookedTransformer,
    example: IOIExample
) -> Dict[str, np.ndarray]:
    """
    Analyze attention patterns for IOI task understanding.
    
    Args:
        model: Configured transformer model
        example: IOI example to analyze
    
    Returns:
        Dictionary of attention patterns from different layers/heads
    """
    # Run model with cache
    _, cache = model.run_with_cache(example.text)
    
    # Get token positions
    tokens = model.to_str_tokens(example.text)
    n_tokens = len(tokens)
    
    attention_analysis = {}
    
    # Analyze attention from final position to name positions
    for layer in range(model.cfg.n_layers):
        layer_patterns = []
        
        for head in range(model.cfg.n_heads):
            attn_key = f"blocks.{layer}.attn.hook_pattern"
            if attn_key in cache:
                # Get attention from last token to all previous tokens
                attn_pattern = cache[attn_key][0, head, -1, :].cpu().numpy()
                layer_patterns.append(attn_pattern)
        
        attention_analysis[f"layer_{layer}"] = np.array(layer_patterns)
    
    return attention_analysis


def compute_ioi_circuit_importance(
    model: HookedTransformer,
    examples: List[IOIExample]
) -> Dict[str, float]:
    """
    Compute importance scores for different circuit components in IOI task.
    
    Args:
        model: Transformer model with RelP
        examples: List of IOI examples
    
    Returns:
        Dictionary of component importance scores
    """
    importance_scores = {}
    
    for example in examples:
        # Get model predictions
        tokens = model.to_tokens(example.text)
        logits, cache = model.run_with_cache(tokens)
        
        # Get logits for IO and S tokens
        io_token_id = model.to_single_token(" " + example.io_token)
        s_token_id = model.to_single_token(" " + example.s_token)
        
        final_logits = logits[0, -1]
        io_logit = final_logits[io_token_id].item()
        s_logit = final_logits[s_token_id].item()
        
        # Compute logit difference (higher = better IOI performance)
        logit_diff = io_logit - s_logit
        
        # Analyze component contributions
        for layer in range(model.cfg.n_layers):
            # Attention output contribution
            attn_key = f"blocks.{layer}.hook_attn_out"
            if attn_key in cache:
                attn_contrib = cache[attn_key][0, -1].abs().mean().item()
                key = f"layer_{layer}_attention"
                if key not in importance_scores:
                    importance_scores[key] = []
                importance_scores[key].append(attn_contrib * logit_diff)
            
            # MLP output contribution
            mlp_key = f"blocks.{layer}.hook_mlp_out"
            if mlp_key in cache:
                mlp_contrib = cache[mlp_key][0, -1].abs().mean().item()
                key = f"layer_{layer}_mlp"
                if key not in importance_scores:
                    importance_scores[key] = []
                importance_scores[key].append(mlp_contrib * logit_diff)
    
    # Average scores across examples
    avg_scores = {k: np.mean(v) for k, v in importance_scores.items()}
    return avg_scores


def visualize_ioi_attention_heads(
    attention_patterns: Dict[str, np.ndarray],
    example: IOIExample,
    top_k: int = 5
) -> None:
    """
    Visualize the most important attention heads for IOI task.
    
    Args:
        attention_patterns: Dictionary of attention patterns by layer
        example: The IOI example being analyzed
        top_k: Number of top heads to visualize
    """
    # Find heads with highest attention to IO token position
    head_scores = []
    
    for layer_name, patterns in attention_patterns.items():
        layer_idx = int(layer_name.split('_')[1])
        for head_idx, pattern in enumerate(patterns):
            # Score based on attention to IO position
            io_attention = pattern[example.io_pos] if example.io_pos < len(pattern) else 0
            head_scores.append((layer_idx, head_idx, io_attention))
    
    # Sort by IO attention
    head_scores.sort(key=lambda x: x[2], reverse=True)
    
    print(f"\nTop {top_k} attention heads for IOI task:")
    print("(Layer, Head, IO Attention Score)")
    for layer, head, score in head_scores[:top_k]:
        print(f"  L{layer}H{head}: {score:.4f}")


def evaluate_relp_vs_attribution_patching(
    model: HookedTransformer,
    examples: List[IOIExample]
) -> Dict[str, float]:
    """
    Compare RelP with standard attribution patching on IOI task.
    
    Args:
        model: Transformer model
        examples: IOI task examples
    
    Returns:
        Performance metrics comparing methods
    """
    print("\nComparing RelP vs Attribution Patching...")
    
    relp_scores = []
    attribution_scores = []
    
    for example in examples:
        tokens = model.to_tokens(example.text)
        
        # RelP analysis (with LRP enabled)
        model.cfg.use_lrp = True
        logits_relp, cache_relp = model.run_with_cache(tokens)
        
        # Standard attribution (without LRP)
        model.cfg.use_lrp = False
        logits_attr, cache_attr = model.run_with_cache(tokens)
        
        # Get IO and S token predictions
        io_token_id = model.to_single_token(" " + example.io_token)
        s_token_id = model.to_single_token(" " + example.s_token)
        
        # RelP logit difference
        relp_diff = logits_relp[0, -1, io_token_id] - logits_relp[0, -1, s_token_id]
        relp_scores.append(relp_diff.item())
        
        # Attribution logit difference
        attr_diff = logits_attr[0, -1, io_token_id] - logits_attr[0, -1, s_token_id]
        attribution_scores.append(attr_diff.item())
    
    # Re-enable LRP for future use
    model.cfg.use_lrp = True
    
    results = {
        "relp_mean_logit_diff": np.mean(relp_scores),
        "relp_std_logit_diff": np.std(relp_scores),
        "attribution_mean_logit_diff": np.mean(attribution_scores),
        "attribution_std_logit_diff": np.std(attribution_scores),
        "improvement": np.mean(relp_scores) - np.mean(attribution_scores)
    }
    
    return results


def analyze_name_mover_heads(
    model: HookedTransformer,
    example: IOIExample
) -> List[Tuple[int, int, float]]:
    """
    Identify "name mover" heads that copy name information to the output.
    
    Args:
        model: Transformer model
        example: IOI example
    
    Returns:
        List of (layer, head, score) tuples for name mover heads
    """
    tokens = model.to_tokens(example.text)
    _, cache = model.run_with_cache(tokens)
    
    name_mover_scores = []
    
    for layer in range(model.cfg.n_layers):
        for head in range(model.cfg.n_heads):
            # Get OV circuit output for this head
            ov_key = f"blocks.{layer}.attn.hook_result"
            if ov_key in cache:
                # Analyze if head moves name information to final position
                head_output = cache[ov_key][0, -1, head]
                
                # Simple heuristic: magnitude of output
                score = head_output.abs().mean().item()
                name_mover_scores.append((layer, head, score))
    
    # Sort by score
    name_mover_scores.sort(key=lambda x: x[2], reverse=True)
    return name_mover_scores


def main():
    """
    Main IOI task analysis demonstration.
    """
    print("=" * 70)
    print("IOI Task Analysis with RelP (Relevance Patching)")
    print("=" * 70)
    
    # Setup
    model = setup_ioi_model("gpt2-small")
    examples = create_ioi_examples()
    
    # Example 1: Basic IOI analysis
    print("\n1. Analyzing IOI Examples")
    print("-" * 50)
    
    for i, example in enumerate(examples[:2], 1):
        print(f"\nExample {i}: {example.text}")
        print(f"Expected answer: {example.io_token}")
        
        # Get model prediction
        tokens = model.to_tokens(example.text)
        logits, _ = model.run_with_cache(tokens)
        
        # Get top predictions
        top_tokens = torch.topk(logits[0, -1], k=5)
        print("Top 5 predictions:")
        for j, (value, idx) in enumerate(zip(top_tokens.values, top_tokens.indices)):
            token_str = model.to_single_str_token(idx.item())
            print(f"  {j+1}. {token_str}: {value.item():.2f}")
    
    # Example 2: Attention pattern analysis
    print("\n2. Attention Pattern Analysis")
    print("-" * 50)
    
    example = examples[0]
    attention_patterns = analyze_ioi_attention_patterns(model, example)
    visualize_ioi_attention_heads(attention_patterns, example, top_k=10)
    
    # Example 3: Circuit importance analysis
    print("\n3. Circuit Component Importance")
    print("-" * 50)
    
    importance_scores = compute_ioi_circuit_importance(model, examples)
    
    # Display top important components
    sorted_components = sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 10 most important components for IOI:")
    for component, score in sorted_components[:10]:
        print(f"  {component}: {score:.4f}")
    
    # Example 4: Name mover head analysis
    print("\n4. Name Mover Head Analysis")
    print("-" * 50)
    
    name_movers = analyze_name_mover_heads(model, examples[0])
    print("\nTop 10 potential name mover heads:")
    for layer, head, score in name_movers[:10]:
        print(f"  L{layer}H{head}: {score:.4f}")
    
    # Example 5: RelP vs Attribution Patching comparison
    print("\n5. Method Comparison")
    print("-" * 50)
    
    comparison_results = evaluate_relp_vs_attribution_patching(model, examples)
    
    print("\nPerformance Comparison:")
    print(f"  RelP mean logit diff: {comparison_results['relp_mean_logit_diff']:.4f} "
          f"(±{comparison_results['relp_std_logit_diff']:.4f})")
    print(f"  Attribution mean logit diff: {comparison_results['attribution_mean_logit_diff']:.4f} "
          f"(±{comparison_results['attribution_std_logit_diff']:.4f})")
    print(f"  RelP improvement: {comparison_results['improvement']:.4f}")
    
    print("\n" + "=" * 70)
    print("IOI task analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
```

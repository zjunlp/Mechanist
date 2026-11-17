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

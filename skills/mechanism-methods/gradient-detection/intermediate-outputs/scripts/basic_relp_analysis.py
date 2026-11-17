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

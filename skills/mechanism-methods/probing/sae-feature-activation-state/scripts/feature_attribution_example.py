#!/usr/bin/env python3
"""
Feature Attribution Example for SAE Analysis

This script demonstrates how to use the sae_spelling library to perform
feature attribution analysis, including integrated gradient attribution
patching to understand how SAE features contribute to model outputs.

Requires: poetry install (or pip install sae-spelling)
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from pathlib import Path
import json

# Mock imports - replace with actual imports when available
# from sae_spelling.feature_attribution import (
#     calculate_feature_attribution,
#     calculate_integrated_gradient_attribution_patching
# )
# from sae_spelling.sae_utils import apply_saes_and_run
# from sae_spelling.experiments.common import load_gemma2_model, load_gemmascope_sae

def calculate_feature_attribution(
    model,
    sae,
    input_text: str,
    target_token: str,
    layer_name: str,
    num_steps: int = 50
) -> Dict[int, float]:
    """
    Calculate feature attribution scores using integrated gradients.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        input_text: Input prompt text
        target_token: Target token to predict
        layer_name: Name of the layer to analyze
        num_steps: Number of integration steps
    
    Returns:
        Dictionary mapping feature indices to attribution scores
    """
    raise NotImplementedError("Reference template: connect the actual model/method backend before measuring results.")

def calculate_integrated_gradient_attribution(
    model,
    sae,
    input_ids: torch.Tensor,
    target_idx: int,
    baseline_ids: Optional[torch.Tensor] = None,
    num_steps: int = 50
) -> torch.Tensor:
    """
    Calculate integrated gradient attribution for SAE features.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        input_ids: Input token IDs
        target_idx: Target token index in vocabulary
        baseline_ids: Baseline input for integration
        num_steps: Number of integration steps
    
    Returns:
        Attribution scores for each SAE feature
    """
    raise NotImplementedError("Reference template: connect the actual model/method backend before measuring results.")

def analyze_top_features(
    attribution_scores: Dict[int, float],
    top_k: int = 10
) -> List[Tuple[int, float]]:
    """
    Identify and analyze the top-k most important features.
    
    Args:
        attribution_scores: Feature attribution scores
        top_k: Number of top features to return
    
    Returns:
        List of (feature_idx, score) tuples
    """
    # Sort features by attribution score
    sorted_features = sorted(
        attribution_scores.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    
    top_features = sorted_features[:top_k]
    
    print(f"\nTop {top_k} Most Important Features:")
    for idx, (feat_idx, score) in enumerate(top_features, 1):
        print(f"  {idx}. Feature {feat_idx}: {score:.4f}")
    
    return top_features

def compare_attribution_methods(
    model,
    sae,
    test_prompts: List[Tuple[str, str]],
    layer_name: str
) -> Dict[str, Dict[str, Any]]:
    """
    Compare different attribution methods on test prompts.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        test_prompts: List of (prompt, target) tuples
        layer_name: Layer to analyze
    
    Returns:
        Comparison results dictionary
    """
    raise NotImplementedError("Reference template: connect the actual model/method backend before measuring results.")

def visualize_feature_attribution(
    attribution_scores: Dict[int, float],
    save_path: Optional[Path] = None
):
    """
    Create a visualization of feature attribution scores.
    
    Args:
        attribution_scores: Feature attribution scores
        save_path: Optional path to save visualization
    """
    import matplotlib.pyplot as plt
    
    # Sort features by score
    sorted_items = sorted(attribution_scores.items(), key=lambda x: abs(x[1]), reverse=True)
    top_items = sorted_items[:20]  # Show top 20 features
    
    if not top_items:
        print("No features to visualize")
        return
    
    feature_indices = [f"F{idx}" for idx, _ in top_items]
    scores = [score for _, score in top_items]
    
    # Create bar plot
    plt.figure(figsize=(12, 6))
    colors = ['green' if s > 0 else 'red' for s in scores]
    plt.bar(feature_indices, scores, color=colors, alpha=0.7)
    plt.xlabel('Feature Index')
    plt.ylabel('Attribution Score')
    plt.title('Top Feature Attribution Scores')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Add zero line
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to {save_path}")
    
    plt.show()

def run_spelling_attribution_analysis(
    model,
    sae,
    tokenizer,
    layer_name: str
):
    """
    Run attribution analysis specifically for spelling tasks.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        tokenizer: Model tokenizer
        layer_name: Layer to analyze
    
    Returns:
        Attribution analysis results
    """
    # Define spelling-related prompts
    spelling_prompts = [
        ("The first letter of 'cat' is", "c"),
        ("The first letter of 'dog' is", "d"),
        ("The word 'house' starts with the letter", "h"),
        ("Spell the word 'tree': t-r-e-", "e"),
        ("The last letter of 'book' is", "k")
    ]
    
    results = {}
    
    for prompt, target in spelling_prompts:
        print(f"\nSpelling task: '{prompt}' → '{target}'")
        
        # Calculate attribution
        attribution = calculate_feature_attribution(
            model, sae, prompt, target, layer_name
        )
        
        # Find top features for this spelling task
        top_features = analyze_top_features(attribution, top_k=5)
        
        # Store results
        results[prompt] = {
            "target": target,
            "attribution": attribution,
            "top_features": top_features,
            "num_active_features": len(attribution),
            "max_attribution": max(attribution.values()) if attribution else 0,
            "mean_attribution": np.mean(list(attribution.values())) if attribution else 0
        }
    
    # Analyze feature overlap across spelling tasks
    all_features = set()
    for result in results.values():
        all_features.update(result["attribution"].keys())
    
    print(f"\n" + "=" * 50)
    print(f"Spelling Attribution Analysis Summary:")
    print(f"  Total unique features used: {len(all_features)}")
    print(f"  Average features per task: {np.mean([r['num_active_features'] for r in results.values()]):.1f}")
    
    return results

def save_attribution_results(
    results: Dict[str, Any],
    output_path: Path
):
    """
    Save attribution analysis results to JSON file.
    
    Args:
        results: Attribution analysis results
        output_path: Path to save results
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert results to JSON-serializable format
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, dict):
            serializable_results[key] = {}
            for k, v in value.items():
                if isinstance(v, (list, tuple)):
                    serializable_results[key][k] = [
                        (int(idx), float(score)) if isinstance(idx, (int, np.integer)) else (idx, score)
                        for idx, score in v
                    ]
                elif isinstance(v, dict):
                    serializable_results[key][k] = {
                        int(feat_idx) if isinstance(feat_idx, (int, np.integer)) else feat_idx: float(score)
                        for feat_idx, score in v.items()
                    }
                else:
                    serializable_results[key][k] = v
        else:
            serializable_results[key] = value
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")

def main():
    """
    Main function to demonstrate feature attribution analysis.
    """
    print("SAE Feature Attribution Analysis")
    print("=" * 50)
    
    # Configuration
    layer = 12
    layer_name = f"layer_{layer}"
    output_dir = Path("attribution_results")
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Load model and SAE (mock for demonstration)
    print("\nLoading model and SAE...")
    model = None  # load_gemma2_model(dtype=torch.float32, device="cuda")
    sae = None    # load_gemmascope_sae(layer=layer, width=16384, l0=128)
    tokenizer = None  # from model loading
    
    # Step 2: Run basic attribution analysis
    test_prompts = [
        ("The capital of France is", "Paris"),
        ("Two plus two equals", "four"),
        ("The first letter of alphabet is", "a")
    ]
    
    print("\nRunning attribution analysis...")
    comparison_results = compare_attribution_methods(
        model, sae, test_prompts, layer_name
    )
    
    # Step 3: Run spelling-specific attribution
    spelling_results = run_spelling_attribution_analysis(
        model, sae, tokenizer, layer_name
    )
    
    # Step 4: Visualize top attributions
    if spelling_results:
        first_result = list(spelling_results.values())[0]
        visualize_feature_attribution(
            first_result["attribution"],
            save_path=output_dir / "attribution_visualization.png"
        )
    
    # Step 5: Save all results
    all_results = {
        "comparison_analysis": comparison_results,
        "spelling_analysis": spelling_results
    }
    
    save_attribution_results(
        all_results,
        output_dir / "attribution_results.json"
    )
    
    print("\n" + "=" * 50)
    print("Attribution analysis complete!")

if __name__ == "__main__":
    main()

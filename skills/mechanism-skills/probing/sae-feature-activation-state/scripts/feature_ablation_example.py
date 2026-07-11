#!/usr/bin/env python3
"""
Feature Ablation Example for SAE Analysis

This script demonstrates how to use the sae_spelling library to perform
feature ablation experiments on Sparse Autoencoders (SAEs). It shows how
to ablate individual SAE features and measure their impact on model outputs.

Requires: poetry install (or pip install sae-spelling)
"""

import torch
from typing import List, Dict, Any
from pathlib import Path

# Mock imports - replace with actual imports when available
# from sae_spelling.feature_ablation import calculate_individual_feature_ablations
# from sae_spelling.experiments.common import load_gemma2_model, load_gemmascope_sae
# from sae_spelling.prompting import create_icl_prompt, first_letter_formatter
# from sae_spelling.vocab import get_alpha_tokens

def setup_model_and_sae(layer: int = 12, sae_width: int = 16384, sae_l0: int = 128):
    """
    Load a Gemma-2 model and corresponding SAE.
    
    Args:
        layer: Which transformer layer to analyze
        sae_width: Width of the SAE (number of features)
        sae_l0: L0 target for SAE sparsity
    
    Returns:
        Tuple of (model, sae, tokenizer)
    """
    print(f"Loading Gemma-2 model...")
    # model, tokenizer = load_gemma2_model(dtype=torch.float32, device="cuda")
    
    print(f"Loading GemmaScope SAE for layer {layer}...")
    # sae = load_gemmascope_sae(layer=layer, width=sae_width, l0=sae_l0)
    
    # Mock implementation for demonstration
    model = None
    sae = None
    tokenizer = None
    
    return model, sae, tokenizer

def prepare_spelling_prompts(tokenizer, num_examples: int = 10):
    """
    Create prompts for first-letter spelling tasks.
    
    Args:
        tokenizer: The model's tokenizer
        num_examples: Number of example prompts to generate
    
    Returns:
        List of formatted prompts
    """
    # Get alphabetic tokens from vocabulary
    # alpha_tokens = get_alpha_tokens(tokenizer)
    
    # Create ICL prompts for first-letter task
    prompts = []
    
    # Mock implementation
    example_tokens = ["cat", "dog", "house", "tree", "book"]
    
    for token in example_tokens[:num_examples]:
        # prompt = create_icl_prompt(
        #     tokens=[token],
        #     formatter=first_letter_formatter(),
        #     num_shots=5
        # )
        prompt = f"The first letter of '{token}' is"
        prompts.append(prompt)
    
    return prompts

def run_feature_ablation_analysis(
    model,
    sae,
    tokenizer,
    prompts: List[str],
    metric_fn=None
):
    """
    Perform feature ablation analysis on given prompts.
    
    Args:
        model: The language model
        sae: The Sparse Autoencoder
        tokenizer: Model tokenizer
        prompts: List of evaluation prompts
        metric_fn: Function to evaluate model output quality
    
    Returns:
        Dict containing ablation results for each feature
    """
    results = {}
    
    print("Running feature ablation experiments...")
    
    for prompt_idx, prompt in enumerate(prompts):
        print(f"Processing prompt {prompt_idx + 1}/{len(prompts)}: {prompt[:50]}...")
        
        # Tokenize the prompt
        # tokens = tokenizer(prompt, return_tensors="pt")
        
        # Get baseline model output
        # with torch.no_grad():
        #     baseline_output = model(tokens)
        
        # Calculate individual feature ablations
        # ablation_effects = calculate_individual_feature_ablations(
        #     model=model,
        #     sae=sae,
        #     prompt=prompt,
        #     metric_fn=metric_fn or default_metric
        # )
        
        # Mock results for demonstration
        ablation_effects = {
            f"feature_{i}": {
                "effect_size": torch.randn(1).item(),
                "firing_rate": torch.rand(1).item(),
                "importance_score": torch.rand(1).item()
            }
            for i in range(5)  # Mock 5 features
        }
        
        results[f"prompt_{prompt_idx}"] = {
            "prompt": prompt,
            "ablation_effects": ablation_effects
        }
    
    return results

def analyze_feature_importance(ablation_results: Dict[str, Any]):
    """
    Analyze and summarize feature importance from ablation results.
    
    Args:
        ablation_results: Results from feature ablation analysis
    
    Returns:
        Summary statistics of feature importance
    """
    print("\nAnalyzing feature importance...")
    
    # Aggregate feature effects across prompts
    feature_scores = {}
    
    for prompt_key, prompt_results in ablation_results.items():
        for feature_name, effects in prompt_results["ablation_effects"].items():
            if feature_name not in feature_scores:
                feature_scores[feature_name] = []
            
            feature_scores[feature_name].append(effects["importance_score"])
    
    # Calculate average importance for each feature
    feature_importance = {}
    for feature_name, scores in feature_scores.items():
        feature_importance[feature_name] = {
            "mean_importance": sum(scores) / len(scores),
            "max_importance": max(scores),
            "frequency": len([s for s in scores if s > 0.5]) / len(scores)
        }
    
    # Sort features by mean importance
    sorted_features = sorted(
        feature_importance.items(),
        key=lambda x: x[1]["mean_importance"],
        reverse=True
    )
    
    print("\nTop 5 Most Important Features:")
    for feature_name, stats in sorted_features[:5]:
        print(f"  {feature_name}:")
        print(f"    Mean importance: {stats['mean_importance']:.4f}")
        print(f"    Max importance: {stats['max_importance']:.4f}")
        print(f"    Active frequency: {stats['frequency']:.2%}")
    
    return feature_importance

def save_results(results: Dict[str, Any], output_path: Path):
    """
    Save ablation results to disk for further analysis.
    
    Args:
        results: Ablation analysis results
        output_path: Path to save results
    """
    import json
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert torch tensors to regular Python types for JSON serialization
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, torch.Tensor):
            serializable_results[key] = value.tolist()
        elif isinstance(value, dict):
            serializable_results[key] = {
                k: v.tolist() if isinstance(v, torch.Tensor) else v
                for k, v in value.items()
            }
        else:
            serializable_results[key] = value
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")

def main():
    """
    Main function to run the feature ablation example.
    """
    print("SAE Feature Ablation Analysis Example")
    print("=" * 50)
    
    # Configuration
    layer = 12
    sae_width = 16384
    sae_l0 = 128
    num_prompts = 5
    output_path = Path("ablation_results.json")
    
    # Step 1: Load model and SAE
    model, sae, tokenizer = setup_model_and_sae(
        layer=layer,
        sae_width=sae_width,
        sae_l0=sae_l0
    )
    
    # Step 2: Prepare evaluation prompts
    prompts = prepare_spelling_prompts(tokenizer, num_examples=num_prompts)
    
    # Step 3: Run ablation analysis
    ablation_results = run_feature_ablation_analysis(
        model=model,
        sae=sae,
        tokenizer=tokenizer,
        prompts=prompts
    )
    
    # Step 4: Analyze feature importance
    feature_importance = analyze_feature_importance(ablation_results)
    
    # Step 5: Save results
    save_results(
        {
            "ablation_results": ablation_results,
            "feature_importance": feature_importance
        },
        output_path
    )
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()

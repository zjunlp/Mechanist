#!/usr/bin/env python3
"""
Compute Input and Output Scores for SAE Features

This script demonstrates how to calculate input and output scores for SAE features
to identify which features are most effective for model steering.

Requires: pip install sae-lens accelerate transformers torch
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from sae_lens import SAE
import numpy as np


def load_features(features_file: str) -> Dict:
    """
    Load feature definitions from a JSON file.
    
    Args:
        features_file: Path to JSON file containing feature specifications
        
    Returns:
        Dictionary containing feature definitions
    """
    with open(features_file, 'r') as f:
        features = json.load(f)
    print(f"Loaded {len(features)} features from {features_file}")
    return features


def compute_output_score(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    layer: int,
    feature_idx: int,
    test_prompts: Optional[List[str]] = None
) -> float:
    """
    Calculate the output score for a specific SAE feature.
    
    The output score measures how much a feature affects the model's output
    distribution when activated.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        layer: Layer index where the feature is located
        feature_idx: Index of the feature to score
        test_prompts: Optional list of prompts to use for scoring
        
    Returns:
        Output score (higher indicates stronger effect on output)
    """
    if test_prompts is None:
        test_prompts = [
            "The weather today is",
            "In conclusion, we should",
            "The most important thing is",
            "Research has shown that",
            "People often think"
        ]
    
    scores = []
    
    for prompt in test_prompts:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        
        # Get baseline logits
        with torch.no_grad():
            baseline_outputs = model(**inputs)
            baseline_logits = baseline_outputs.logits[0, -1, :]
        
        # Get logits with feature amplified (simplified version)
        # In practice, this would use SAE hooks to amplify the specific feature
        # Here we demonstrate the scoring concept
        
        # Calculate KL divergence or other metrics
        # This is a simplified scoring mechanism
        score = torch.rand(1).item()  # Placeholder for actual computation
        scores.append(score)
    
    return np.mean(scores)


def compute_input_score(
    tokenizer: AutoTokenizer,
    feature_data: Dict,
    feature_idx: int
) -> float:
    """
    Calculate the input score for a specific SAE feature.
    
    The input score measures how consistently a feature activates on
    specific input patterns.
    
    Args:
        tokenizer: Model tokenizer
        feature_data: Dictionary containing activation data for features
        feature_idx: Index of the feature to score
        
    Returns:
        Input score (higher indicates more consistent input pattern)
    """
    # Extract tokens that activate this feature
    if str(feature_idx) not in feature_data:
        return 0.0
    
    activation_data = feature_data[str(feature_idx)]
    
    # Calculate consistency metrics
    # This is a simplified version - actual implementation would analyze
    # token patterns, activation strengths, and consistency
    
    # Example metrics:
    # - Entropy of activating tokens
    # - Consistency of activation patterns
    # - Specificity to certain token types
    
    input_score = np.random.rand()  # Placeholder for actual computation
    return input_score


def filter_features_by_scores(
    features: Dict,
    output_scores: Dict[int, float],
    input_scores: Dict[int, float],
    output_threshold: float = 0.5,
    input_threshold: float = 0.7
) -> List[int]:
    """
    Filter features based on their input and output scores.
    
    The key insight: features with high output scores but moderate input scores
    are most effective for steering.
    
    Args:
        features: Dictionary of all features
        output_scores: Computed output scores
        input_scores: Computed input scores
        output_threshold: Minimum output score required
        input_threshold: Maximum input score allowed
        
    Returns:
        List of feature indices that pass the filtering criteria
    """
    selected_features = []
    
    for feature_idx in features.keys():
        idx = int(feature_idx)
        
        # Check if feature has high output score (affects model output)
        if output_scores.get(idx, 0) < output_threshold:
            continue
            
        # Check if feature has moderate input score (not too input-specific)
        if input_scores.get(idx, 1.0) > input_threshold:
            continue
            
        selected_features.append(idx)
    
    print(f"Selected {len(selected_features)} features out of {len(features)}")
    print(f"Output threshold: {output_threshold}, Input threshold: {input_threshold}")
    
    return selected_features


def save_scores(
    output_scores: Dict[int, float],
    input_scores: Dict[int, float],
    output_file: str
):
    """
    Save computed scores to a JSON file for later use.
    
    Args:
        output_scores: Dictionary of output scores
        input_scores: Dictionary of input scores
        output_file: Path to save the scores
    """
    scores_data = {
        "output_scores": output_scores,
        "input_scores": input_scores,
        "metadata": {
            "num_features": len(output_scores),
            "avg_output_score": np.mean(list(output_scores.values())),
            "avg_input_score": np.mean(list(input_scores.values()))
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(scores_data, f, indent=2)
    
    print(f"Saved scores to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Compute SAE feature scores for steering")
    parser.add_argument("--model_name", type=str, default="google/gemma-2b",
                        help="Name of the model to analyze")
    parser.add_argument("--features_file", type=str, required=True,
                        help="Path to features JSON file")
    parser.add_argument("--output_file", type=str, default="feature_scores.json",
                        help="Path to save computed scores")
    parser.add_argument("--compute_output", action="store_true",
                        help="Compute output scores")
    parser.add_argument("--compute_input", action="store_true",
                        help="Compute input scores")
    
    args = parser.parse_args()
    
    # Load features
    features = load_features(args.features_file)
    
    # Initialize scores dictionaries
    output_scores = {}
    input_scores = {}
    
    if args.compute_output:
        print("Computing output scores...")
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Compute output scores for each feature
        for feature_idx in features.keys():
            idx = int(feature_idx)
            layer = features[feature_idx].get("layer", 0)
            score = compute_output_score(model, tokenizer, layer, idx)
            output_scores[idx] = score
            
            if idx % 100 == 0:
                print(f"Processed {idx} features...")
    
    if args.compute_input:
        print("Computing input scores...")
        # Load tokenizer for input analysis
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        
        # Load feature activation data (would come from Neuronpedia or similar)
        feature_data = {}  # Placeholder - would load actual data
        
        # Compute input scores for each feature
        for feature_idx in features.keys():
            idx = int(feature_idx)
            score = compute_input_score(tokenizer, feature_data, idx)
            input_scores[idx] = score
    
    # Filter features based on scores
    if output_scores and input_scores:
        selected = filter_features_by_scores(features, output_scores, input_scores)
        print(f"Best features for steering: {selected[:10]}")
    
    # Save results
    if output_scores or input_scores:
        save_scores(output_scores, input_scores, args.output_file)


if __name__ == "__main__":
    main()

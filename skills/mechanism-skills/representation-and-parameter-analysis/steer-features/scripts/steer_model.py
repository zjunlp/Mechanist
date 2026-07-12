#!/usr/bin/env python3
"""
Steer Language Model Output using SAE Features

This script demonstrates how to use selected SAE features to steer model outputs
toward desired concepts or behaviors.

Requires: pip install sae-lens transformers torch accelerate
"""

import json
import argparse
from typing import List, Dict, Optional, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from dataclasses import dataclass
import numpy as np


@dataclass
class SteeringConfig:
    """Configuration for steering experiments."""
    model_name: str
    feature_idx: int
    layer: int
    steering_factor: float
    max_length: int = 100
    temperature: float = 0.7
    top_p: float = 0.9


class SAESteeringHook:
    """
    Hook for amplifying specific SAE features during model inference.
    
    This class demonstrates the core steering mechanism where specific
    features are amplified to influence model behavior.
    """
    
    def __init__(self, layer: int, feature_idx: int, steering_factor: float):
        """
        Initialize the steering hook.
        
        Args:
            layer: Model layer to hook into
            feature_idx: Index of the SAE feature to amplify
            steering_factor: Amplification factor (typically 0.2 to 20.0)
        """
        self.layer = layer
        self.feature_idx = feature_idx
        self.steering_factor = steering_factor
        self.hook_handle = None
        
    def steering_hook(self, module, input, output):
        """
        The actual hook function that modifies activations.
        
        Args:
            module: The hooked module
            input: Input to the module
            output: Output from the module
            
        Returns:
            Modified output with amplified feature
        """
        # In practice, this would interact with the SAE to:
        # 1. Decode current activations to features
        # 2. Amplify the target feature
        # 3. Reconstruct activations
        
        # Simplified version for demonstration
        if isinstance(output, tuple):
            hidden_states = output[0]
        else:
            hidden_states = output
            
        # Apply steering (simplified - actual implementation would use SAE)
        # This is a placeholder for the actual SAE feature amplification
        batch_size, seq_len, hidden_dim = hidden_states.shape
        
        # Create a steering vector (would come from SAE in practice)
        steering_vector = torch.randn(1, 1, hidden_dim, device=hidden_states.device)
        steering_vector = steering_vector * self.steering_factor
        
        # Apply steering to the last token position (generation position)
        hidden_states[:, -1, :] = hidden_states[:, -1, :] + steering_vector.squeeze()
        
        if isinstance(output, tuple):
            return (hidden_states,) + output[1:]
        return hidden_states
    
    def register(self, model: AutoModelForCausalLM):
        """Register the hook with the model."""
        # Get the appropriate layer
        if hasattr(model, 'model'):  # For models like Gemma
            layers = model.model.layers
        elif hasattr(model, 'transformer'):  # For models like GPT
            layers = model.transformer.h
        else:
            layers = model.layers
            
        target_layer = layers[self.layer]
        self.hook_handle = target_layer.register_forward_hook(self.steering_hook)
        
    def remove(self):
        """Remove the hook from the model."""
        if self.hook_handle:
            self.hook_handle.remove()
            self.hook_handle = None


def load_best_features(scores_file: str, top_k: int = 10) -> List[Tuple[int, float]]:
    """
    Load the best features for steering based on pre-computed scores.
    
    Args:
        scores_file: Path to JSON file with feature scores
        top_k: Number of top features to return
        
    Returns:
        List of (feature_idx, score) tuples
    """
    with open(scores_file, 'r') as f:
        scores_data = json.load(f)
    
    output_scores = scores_data.get('output_scores', {})
    input_scores = scores_data.get('input_scores', {})
    
    # Calculate combined score (high output, moderate input)
    combined_scores = {}
    for feature_idx, out_score in output_scores.items():
        in_score = input_scores.get(feature_idx, 0.5)
        # Favor high output score with moderate input score
        combined = out_score * (1.0 - abs(in_score - 0.5))
        combined_scores[int(feature_idx)] = combined
    
    # Sort and return top features
    sorted_features = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_features[:top_k]


def generate_with_steering(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    config: SteeringConfig
) -> str:
    """
    Generate text with SAE feature steering applied.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        prompt: Input prompt
        config: Steering configuration
        
    Returns:
        Generated text with steering applied
    """
    # Create and register steering hook
    hook = SAESteeringHook(
        layer=config.layer,
        feature_idx=config.feature_idx,
        steering_factor=config.steering_factor
    )
    hook.register(model)
    
    try:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate with steering
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=config.max_length,
                temperature=config.temperature,
                top_p=config.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode output
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return generated_text
        
    finally:
        # Always remove hook after generation
        hook.remove()


def compare_steering_factors(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    feature_idx: int,
    layer: int,
    factors: List[float] = [0.0, 0.4, 0.8, 1.2, 2.0, 4.0, 8.0]
) -> Dict[float, str]:
    """
    Compare outputs with different steering factors.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        prompt: Input prompt
        feature_idx: SAE feature to steer with
        layer: Model layer containing the feature
        factors: List of steering factors to test
        
    Returns:
        Dictionary mapping steering factors to generated outputs
    """
    results = {}
    
    for factor in factors:
        config = SteeringConfig(
            model_name=model.config.name_or_path,
            feature_idx=feature_idx,
            layer=layer,
            steering_factor=factor
        )
        
        output = generate_with_steering(model, tokenizer, prompt, config)
        results[factor] = output
        
        print(f"\n--- Steering Factor: {factor} ---")
        print(output)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Steer model output using SAE features")
    parser.add_argument("--model_name", type=str, default="google/gemma-2b",
                        help="Name of the model to steer")
    parser.add_argument("--prompt", type=str, default="The future of AI is",
                        help="Input prompt for generation")
    parser.add_argument("--feature_idx", type=int, help="Feature index to use for steering")
    parser.add_argument("--layer", type=int, default=10, help="Model layer for steering")
    parser.add_argument("--steering_factor", type=float, default=2.0,
                        help="Steering amplification factor")
    parser.add_argument("--scores_file", type=str, help="Path to feature scores file")
    parser.add_argument("--compare_factors", action="store_true",
                        help="Compare multiple steering factors")
    
    args = parser.parse_args()
    
    # Load model and tokenizer
    print(f"Loading model: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # If scores file provided, use best features
    if args.scores_file:
        best_features = load_best_features(args.scores_file, top_k=5)
        print(f"Best features for steering: {best_features}")
        
        if not args.feature_idx:
            # Use the best feature if not specified
            args.feature_idx = best_features[0][0]
            print(f"Using best feature: {args.feature_idx}")
    
    if args.compare_factors:
        # Compare different steering factors
        results = compare_steering_factors(
            model, tokenizer, args.prompt,
            args.feature_idx, args.layer
        )
        
        # Save results
        with open("steering_comparison.json", 'w') as f:
            json.dump(results, f, indent=2)
        print("\nSaved comparison results to steering_comparison.json")
    else:
        # Single generation with specified parameters
        config = SteeringConfig(
            model_name=args.model_name,
            feature_idx=args.feature_idx,
            layer=args.layer,
            steering_factor=args.steering_factor
        )
        
        output = generate_with_steering(model, tokenizer, args.prompt, config)
        
        print(f"\n--- Generated with steering factor {args.steering_factor} ---")
        print(output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Basic LogitLens Analysis Script

This script demonstrates how to use LogitLens4LLMs to analyze layer-wise predictions
in large language models like Llama-3.1-8B and Qwen-2.5-7B.

Requirements:
    pip install torch transformers matplotlib seaborn numpy
"""

import json
import os
from typing import List, Dict, Any
from enum import Enum

# Mock implementation of the LogitLens components
# In actual usage, import from the installed package

class ModelType(Enum):
    """Enumeration of supported model types"""
    LLAMA_3_1_8B = "llama_3_1_8b"
    QWEN_2_5_7B = "qwen_2_5_7b"
    LLAMA_2_7B = "llama_2_7b"


class LogitLensAnalyzer:
    """Main analyzer class for LogitLens analysis"""
    
    def __init__(self, model_type: ModelType, use_local: bool = False):
        """
        Initialize the LogitLens analyzer.
        
        Args:
            model_type: Type of model to analyze
            use_local: Whether to use locally cached model
        """
        self.model_type = model_type
        self.use_local = use_local
        self.model_name = self._get_model_name()
        
    def _get_model_name(self) -> str:
        """Get the Hugging Face model identifier"""
        model_map = {
            ModelType.LLAMA_3_1_8B: "meta-llama/Meta-Llama-3.1-8B",
            ModelType.QWEN_2_5_7B: "Qwen/Qwen2.5-7B",
            ModelType.LLAMA_2_7B: "meta-llama/Llama-2-7b-hf"
        }
        return model_map.get(self.model_type, "")
    
    def analyze_prompt(self, 
                      prompt: str, 
                      max_new_tokens: int = 10,
                      temperature: float = 0.7,
                      print_details: bool = True) -> List[Dict[str, Any]]:
        """
        Perform LogitLens analysis on a given prompt.
        
        Args:
            prompt: Input text to analyze
            max_new_tokens: Number of tokens to generate
            temperature: Sampling temperature
            print_details: Whether to print detailed layer information
            
        Returns:
            List of prediction steps with layer-wise analysis
        """
        prediction_steps = []
        
        print(f"Running LogitLens analysis on {self.model_type.value}")
        print(f"Prompt: {prompt}")
        print("-" * 50)
        
        # Simulate generation steps
        generated_tokens = self._simulate_generation(prompt, max_new_tokens)
        
        for step_idx, token in enumerate(generated_tokens):
            step_data = self._analyze_step(prompt, token, step_idx, print_details)
            prediction_steps.append(step_data)
            
            if print_details:
                self._print_step_analysis(step_data)
        
        return prediction_steps
    
    def _simulate_generation(self, prompt: str, max_tokens: int) -> List[str]:
        """Simulate token generation for demonstration"""
        # In real implementation, this would use the actual model
        example_completions = {
            "The cat sat on the": ["mat", "and", "looked", "at", "the", "mouse"],
            "Once upon a time": ["there", "was", "a", "brave", "knight"],
            "The weather today is": ["sunny", "with", "clear", "blue", "skies"]
        }
        
        for key in example_completions:
            if key in prompt:
                return example_completions[key][:max_tokens]
        
        # Default tokens
        return ["token"] * min(max_tokens, 5)
    
    def _analyze_step(self, 
                     prompt: str, 
                     token: str, 
                     step_idx: int,
                     include_all_layers: bool = True) -> Dict[str, Any]:
        """
        Analyze a single generation step.
        
        Args:
            prompt: Current prompt text
            token: Generated token
            step_idx: Step index
            include_all_layers: Whether to include all layer predictions
            
        Returns:
            Dictionary containing step analysis data
        """
        # Simulate layer-wise predictions
        num_layers = 32 if "8b" in self.model_type.value.lower() else 28
        
        layer_predictions = []
        important_layers = []
        
        for layer_idx in range(num_layers):
            # Simulate confidence scores decreasing with layer depth
            confidence = 100 - (layer_idx * 2) + (step_idx * 5)
            confidence = max(10, min(100, confidence))
            
            layer_data = {
                "layer_idx": layer_idx,
                "predicted_token": token,
                "confidence": confidence,
                "top_k_predictions": self._get_top_k_predictions(token, layer_idx)
            }
            
            layer_predictions.append(layer_data)
            
            # Mark important layers (high confidence)
            if confidence > 70:
                important_layers.append(layer_idx)
        
        return {
            "step_idx": step_idx,
            "predicted_token": token,
            "current_text": f"{prompt} {token}",
            "layer_predictions": layer_predictions if include_all_layers else None,
            "important_layers": important_layers,
            "attention_weights": self._simulate_attention_weights(num_layers),
            "mlp_contributions": self._simulate_mlp_contributions(num_layers)
        }
    
    def _get_top_k_predictions(self, token: str, layer_idx: int) -> List[tuple]:
        """Get top-k token predictions for a layer"""
        # Simulate alternative predictions
        alternatives = {
            "mat": ["floor", "carpet", "rug", "ground"],
            "sunny": ["cloudy", "rainy", "warm", "bright"],
            "there": ["once", "lived", "existed", "came"]
        }
        
        alt_tokens = alternatives.get(token, ["alt1", "alt2", "alt3"])
        predictions = [(token, 85 - layer_idx)]
        
        for i, alt in enumerate(alt_tokens[:3]):
            score = max(5, 70 - layer_idx - (i * 20))
            predictions.append((alt, score))
        
        return predictions
    
    def _simulate_attention_weights(self, num_layers: int) -> Dict[int, float]:
        """Simulate attention weights across layers"""
        weights = {}
        for i in range(num_layers):
            # Higher attention in middle layers
            if i < num_layers // 3:
                weights[i] = 0.3 + (i * 0.02)
            elif i < 2 * num_layers // 3:
                weights[i] = 0.6 + (i * 0.01)
            else:
                weights[i] = 0.8 + (i * 0.005)
        return weights
    
    def _simulate_mlp_contributions(self, num_layers: int) -> Dict[int, float]:
        """Simulate MLP contributions across layers"""
        contributions = {}
        for i in range(num_layers):
            # MLP contribution increases with depth
            contributions[i] = 0.2 + (i / num_layers) * 0.6
        return contributions
    
    def _print_step_analysis(self, step_data: Dict[str, Any]):
        """Print formatted analysis for a generation step"""
        print(f"\nStep {step_data['step_idx'] + 1}: Generated '{step_data['predicted_token']}'")
        print(f"Current text: {step_data['current_text']}")
        
        if step_data['important_layers']:
            print(f"Important layers: {step_data['important_layers'][:5]}")
        
        print("Top predictions from final layers:")
        if step_data['layer_predictions']:
            for layer in step_data['layer_predictions'][-3:]:
                preds = layer['top_k_predictions'][:3]
                pred_str = ", ".join([f"{t}({s}%)" for t, s in preds])
                print(f"  Layer {layer['layer_idx']}: {pred_str}")
    
    def save_analysis(self, 
                     prediction_steps: List[Dict[str, Any]], 
                     output_path: str = "output/analysis_results.json"):
        """
        Save analysis results to JSON file.
        
        Args:
            prediction_steps: List of prediction step data
            output_path: Path to save the JSON file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Prepare data for JSON serialization
        output_data = {
            "model_type": self.model_type.value,
            "num_steps": len(prediction_steps),
            "predictions": []
        }
        
        for step in prediction_steps:
            step_summary = {
                "step_idx": step["step_idx"],
                "token": step["predicted_token"],
                "text": step["current_text"],
                "important_layers": step["important_layers"][:5] if step["important_layers"] else []
            }
            output_data["predictions"].append(step_summary)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nAnalysis saved to: {output_path}")


def main():
    """Main function demonstrating LogitLens analysis workflow"""
    
    # Example 1: Analyze Llama-3.1-8B
    print("=" * 60)
    print("Example 1: Llama-3.1-8B Analysis")
    print("=" * 60)
    
    analyzer = LogitLensAnalyzer(ModelType.LLAMA_3_1_8B, use_local=False)
    
    prompt = "Complete this sentence: The cat sat on the"
    results = analyzer.analyze_prompt(
        prompt=prompt,
        max_new_tokens=5,
        temperature=0.7,
        print_details=True
    )
    
    # Save results
    analyzer.save_analysis(results, "output/llama_analysis.json")
    
    # Example 2: Analyze Qwen-2.5-7B
    print("\n" + "=" * 60)
    print("Example 2: Qwen-2.5-7B Analysis")
    print("=" * 60)
    
    qwen_analyzer = LogitLensAnalyzer(ModelType.QWEN_2_5_7B, use_local=False)
    
    prompt = "The weather today is"
    qwen_results = qwen_analyzer.analyze_prompt(
        prompt=prompt,
        max_new_tokens=5,
        temperature=0.8,
        print_details=True
    )
    
    # Save results
    qwen_analyzer.save_analysis(qwen_results, "output/qwen_analysis.json")
    
    # Example 3: Batch analysis
    print("\n" + "=" * 60)
    print("Example 3: Batch Analysis")
    print("=" * 60)
    
    prompts = [
        "Once upon a time",
        "The secret to happiness is",
        "In the future, AI will"
    ]
    
    batch_analyzer = LogitLensAnalyzer(ModelType.LLAMA_2_7B, use_local=False)
    
    all_results = []
    for prompt in prompts:
        print(f"\nAnalyzing: {prompt}")
        results = batch_analyzer.analyze_prompt(
            prompt=prompt,
            max_new_tokens=3,
            print_details=False
        )
        all_results.extend(results)
    
    print(f"\nCompleted batch analysis of {len(prompts)} prompts")
    print(f"Total prediction steps analyzed: {len(all_results)}")


if __name__ == "__main__":
    main()

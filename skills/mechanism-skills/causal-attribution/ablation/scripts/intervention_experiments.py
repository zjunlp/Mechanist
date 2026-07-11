#!/usr/bin/env python3
"""
Intervention Experiments for Factual Association Analysis

This script demonstrates intervention techniques including hidden state patching,
sublayer knockout, and causal analysis of factual recall in language models.

Requires: pip install torch transformers numpy matplotlib
"""

import torch
import torch.nn.functional as F
import numpy as np
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import List, Dict, Tuple, Optional, Callable
import matplotlib.pyplot as plt
from dataclasses import dataclass


@dataclass
class InterventionResult:
    """Store results from intervention experiments."""
    original_prediction: str
    original_prob: float
    intervened_prediction: str
    intervened_prob: float
    layer: int
    intervention_type: str
    

class InterventionAnalyzer:
    """
    Performs intervention experiments on language models to analyze factual recall.
    """
    
    def __init__(self, model_name: str = "gpt2"):
        """Initialize the intervention analyzer."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model.eval()
        
        # Get model configuration
        self.n_layers = self.model.config.n_layer
        self.n_heads = self.model.config.n_head
        self.d_model = self.model.config.n_embd
        
        print(f"Loaded {model_name}: {self.n_layers} layers, {self.n_heads} heads, {self.d_model} dims")
        
    def get_predictions(self, text: str, top_k: int = 1) -> Tuple[List[str], List[float]]:
        """
        Get model predictions for the next token.
        
        Args:
            text: Input text
            top_k: Number of top predictions to return
            
        Returns:
            Tuple of (predicted tokens, probabilities)
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0, -1]
            probs = F.softmax(logits, dim=-1)
            top_probs, top_indices = torch.topk(probs, k=top_k)
            
        tokens = [self.tokenizer.decode([idx]) for idx in top_indices]
        return tokens, top_probs.cpu().numpy()
    
    def patch_hidden_states(self, 
                          source_text: str, 
                          target_text: str, 
                          layer_idx: int,
                          position: int = -1) -> InterventionResult:
        """
        Patch hidden states from source to target at a specific layer.
        
        Args:
            source_text: Text to extract hidden state from
            target_text: Text to inject hidden state into
            layer_idx: Layer at which to perform patching
            position: Token position to patch (-1 for last)
            
        Returns:
            InterventionResult with analysis
        """
        # Get original predictions
        orig_tokens, orig_probs = self.get_predictions(target_text)
        
        # Get source hidden states
        source_inputs = self.tokenizer(source_text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            source_outputs = self.model(**source_inputs, output_hidden_states=True)
            source_hidden = source_outputs.hidden_states[layer_idx][0, position].unsqueeze(0).unsqueeze(0)
        
        # Prepare target with intervention
        target_inputs = self.tokenizer(target_text, return_tensors="pt").to(self.device)
        
        # Define intervention hook
        def patch_hook(module, input, output):
            if isinstance(output, tuple):
                hidden_states = output[0]
            else:
                hidden_states = output
            
            # Patch the hidden state at specified position
            hidden_states[0, position] = source_hidden[0, 0]
            
            if isinstance(output, tuple):
                return (hidden_states,) + output[1:]
            return hidden_states
        
        # Register hook and run with intervention
        if layer_idx == 0:
            handle = self.model.transformer.wte.register_forward_hook(patch_hook)
        else:
            handle = self.model.transformer.h[layer_idx-1].register_forward_hook(patch_hook)
        
        with torch.no_grad():
            intervened_outputs = self.model(**target_inputs)
            intervened_logits = intervened_outputs.logits[0, -1]
            intervened_probs = F.softmax(intervened_logits, dim=-1)
            top_prob, top_idx = torch.topk(intervened_probs, k=1)
        
        handle.remove()
        
        intervened_token = self.tokenizer.decode([top_idx[0]])
        
        return InterventionResult(
            original_prediction=orig_tokens[0],
            original_prob=orig_probs[0],
            intervened_prediction=intervened_token,
            intervened_prob=top_prob[0].cpu().item(),
            layer=layer_idx,
            intervention_type="hidden_state_patch"
        )
    
    def knockout_sublayer(self, 
                         text: str, 
                         layer_idx: int, 
                         sublayer: str = "attn") -> InterventionResult:
        """
        Knockout (zero out) a specific sublayer's contribution.
        
        Args:
            text: Input text
            layer_idx: Layer index
            sublayer: "attn" or "mlp"
            
        Returns:
            InterventionResult with analysis
        """
        # Get original predictions
        orig_tokens, orig_probs = self.get_predictions(text)
        
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Define knockout hook
        def knockout_hook(module, input, output):
            if isinstance(output, tuple):
                # Return zeros for the sublayer output
                zeros = torch.zeros_like(output[0])
                return (zeros,) + output[1:] if len(output) > 1 else zeros
            else:
                return torch.zeros_like(output)
        
        # Register hook on appropriate sublayer
        if sublayer == "attn":
            target_module = self.model.transformer.h[layer_idx].attn
        elif sublayer == "mlp":
            target_module = self.model.transformer.h[layer_idx].mlp
        else:
            raise ValueError(f"Unknown sublayer: {sublayer}")
        
        handle = target_module.register_forward_hook(knockout_hook)
        
        with torch.no_grad():
            knockout_outputs = self.model(**inputs)
            knockout_logits = knockout_outputs.logits[0, -1]
            knockout_probs = F.softmax(knockout_logits, dim=-1)
            top_prob, top_idx = torch.topk(knockout_probs, k=1)
        
        handle.remove()
        
        knockout_token = self.tokenizer.decode([top_idx[0]])
        
        return InterventionResult(
            original_prediction=orig_tokens[0],
            original_prob=orig_probs[0],
            intervened_prediction=knockout_token,
            intervened_prob=top_prob[0].cpu().item(),
            layer=layer_idx,
            intervention_type=f"{sublayer}_knockout"
        )
    
    def analyze_factual_flow(self, 
                           prompt: str, 
                           expected_answer: str) -> Dict:
        """
        Analyze how factual information flows through the network.
        
        Args:
            prompt: Question or prompt requiring factual knowledge
            expected_answer: Expected factual answer
            
        Returns:
            Dictionary with layer-wise analysis
        """
        results = {
            "prompt": prompt,
            "expected": expected_answer,
            "layer_analysis": []
        }
        
        # Get base prediction
        base_tokens, base_probs = self.get_predictions(prompt)
        results["base_prediction"] = base_tokens[0]
        results["base_confidence"] = base_probs[0]
        
        # Analyze each layer's contribution
        for layer_idx in range(self.n_layers):
            layer_info = {"layer": layer_idx}
            
            # Test attention knockout
            attn_result = self.knockout_sublayer(prompt, layer_idx, "attn")
            layer_info["attn_knockout_changes_prediction"] = (
                attn_result.intervened_prediction != base_tokens[0]
            )
            
            # Test MLP knockout
            mlp_result = self.knockout_sublayer(prompt, layer_idx, "mlp")
            layer_info["mlp_knockout_changes_prediction"] = (
                mlp_result.intervened_prediction != base_tokens[0]
            )
            
            # Calculate importance scores
            layer_info["attn_importance"] = abs(
                base_probs[0] - attn_result.intervened_prob
            )
            layer_info["mlp_importance"] = abs(
                base_probs[0] - mlp_result.intervened_prob
            )
            
            results["layer_analysis"].append(layer_info)
        
        return results
    
    def visualize_layer_importance(self, analysis_results: Dict):
        """
        Visualize the importance of different layers for factual prediction.
        
        Args:
            analysis_results: Results from analyze_factual_flow
        """
        layers = [item["layer"] for item in analysis_results["layer_analysis"]]
        attn_importance = [item["attn_importance"] for item in analysis_results["layer_analysis"]]
        mlp_importance = [item["mlp_importance"] for item in analysis_results["layer_analysis"]]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot attention importance
        ax1.bar(layers, attn_importance, color='blue', alpha=0.7)
        ax1.set_xlabel('Layer')
        ax1.set_ylabel('Importance Score')
        ax1.set_title('Attention Sublayer Importance for Factual Prediction')
        ax1.grid(True, alpha=0.3)
        
        # Plot MLP importance
        ax2.bar(layers, mlp_importance, color='green', alpha=0.7)
        ax2.set_xlabel('Layer')
        ax2.set_ylabel('Importance Score')
        ax2.set_title('MLP Sublayer Importance for Factual Prediction')
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(f'Layer Analysis: "{analysis_results["prompt"]}"')
        plt.tight_layout()
        return fig


def run_intervention_experiments():
    """
    Run a series of intervention experiments to analyze factual recall.
    """
    print("Initializing Intervention Analyzer...")
    analyzer = InterventionAnalyzer("gpt2")
    
    # Test cases for factual associations
    test_cases = [
        ("The capital of France is", "Paris"),
        ("Water freezes at", "0"),
        ("The largest planet is", "Jupiter"),
    ]
    
    for prompt, expected in test_cases:
        print(f"\n{'='*60}")
        print(f"Analyzing: '{prompt}'")
        print(f"Expected: '{expected}'")
        print("-" * 60)
        
        # Get baseline prediction
        predictions, probs = analyzer.get_predictions(prompt, top_k=3)
        print(f"\nTop 3 predictions: {list(zip(predictions, probs))}")
        
        # Test hidden state patching
        print("\n--- Hidden State Patching Experiment ---")
        # Create a source that strongly predicts the expected answer
        source_text = f"The answer is definitely {expected}"
        for layer in [0, 6, 11]:  # Early, middle, late layers
            patch_result = analyzer.patch_hidden_states(
                source_text, prompt, layer
            )
            print(f"Layer {layer}: {patch_result.original_prediction} -> {patch_result.intervened_prediction}")
        
        # Test sublayer knockout
        print("\n--- Sublayer Knockout Experiment ---")
        critical_layers = []
        for layer in range(analyzer.n_layers):
            attn_ko = analyzer.knockout_sublayer(prompt, layer, "attn")
            mlp_ko = analyzer.knockout_sublayer(prompt, layer, "mlp")
            
            if attn_ko.intervened_prediction != predictions[0]:
                critical_layers.append(f"L{layer}-attn")
            if mlp_ko.intervened_prediction != predictions[0]:
                critical_layers.append(f"L{layer}-mlp")
        
        print(f"Critical sublayers (change prediction): {critical_layers[:5]}...")
        
        # Comprehensive factual flow analysis
        print("\n--- Factual Flow Analysis ---")
        flow_analysis = analyzer.analyze_factual_flow(prompt, expected)
        
        # Find most important layers
        layer_data = flow_analysis["layer_analysis"]
        most_important_attn = max(layer_data, key=lambda x: x["attn_importance"])
        most_important_mlp = max(layer_data, key=lambda x: x["mlp_importance"])
        
        print(f"Most important attention layer: {most_important_attn['layer']} "
              f"(importance: {most_important_attn['attn_importance']:.4f})")
        print(f"Most important MLP layer: {most_important_mlp['layer']} "
              f"(importance: {most_important_mlp['mlp_importance']:.4f})")
        
        # Visualize if matplotlib is available
        try:
            fig = analyzer.visualize_layer_importance(flow_analysis)
            # Save figure
            fig.savefig(f'layer_importance_{prompt[:20].replace(" ", "_")}.png')
            print(f"Visualization saved to layer_importance_{prompt[:20].replace(' ', '_')}.png")
            plt.close(fig)
        except:
            print("Visualization skipped (matplotlib issue)")


if __name__ == "__main__":
    print("Starting Intervention Experiments for Factual Association Analysis")
    print("=" * 60)
    
    # Check GPU availability
    if torch.cuda.is_available():
        print(f"GPU available: {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU (GPU recommended)")
    
    # Run experiments
    run_intervention_experiments()
    
    print("\n" + "=" * 60)
    print("Experiments complete!")
    print("\nNote: For more detailed analysis with GPT2-xl or GPT-J,")
    print("use appropriate GPU resources (V100/A100) and adjust model name.")

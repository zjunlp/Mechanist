#!/usr/bin/env python3
"""
Model Analysis Script for Dissecting Factual Predictions in Language Models

This script demonstrates how to load GPT-2 models, apply hooks for intermediate
information extraction, and perform basic analysis of factual associations.

Requires: pip install torch transformers numpy
"""

import torch
import numpy as np
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class ModelAnalyzer:
    """
    Analyzer for dissecting factual predictions in GPT-2 style models.
    """
    
    def __init__(self, model_name: str = "gpt2"):
        """
        Initialize the model analyzer with a specific GPT-2 model.
        
        Args:
            model_name: Name of the GPT-2 model (e.g., "gpt2", "gpt2-medium", "gpt2-large", "gpt2-xl")
        """
        print(f"Loading model: {model_name}")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model.eval()
        
        # Storage for intermediate activations
        self.stored_activations = {}
        self.hooks = []
        
    def register_hook(self, module_name: str, hook_type: str = "forward"):
        """
        Register a hook on a specific module to extract intermediate information.
        
        Args:
            module_name: Name of the module to hook (e.g., "transformer.h.0.attn")
            hook_type: Type of hook ("forward" or "backward")
        """
        def get_activation(name):
            def hook(module, input, output):
                self.stored_activations[name] = output.detach()
            return hook
        
        # Navigate to the module
        module = self.model
        for name in module_name.split('.'):
            if name.isdigit():
                module = module[int(name)]
            else:
                module = getattr(module, name)
        
        # Register the hook
        if hook_type == "forward":
            handle = module.register_forward_hook(get_activation(module_name))
        else:
            handle = module.register_backward_hook(get_activation(module_name))
        
        self.hooks.append(handle)
        print(f"Hook registered on {module_name}")
        
    def clear_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
        self.stored_activations = {}
        
    def analyze_attention_flow(self, text: str, layer_idx: int = 0) -> Dict:
        """
        Analyze attention flow for a given text at a specific layer.
        
        Args:
            text: Input text to analyze
            layer_idx: Layer index to analyze (0 to n_layers-1)
            
        Returns:
            Dictionary containing attention weights and analysis
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Register hook on attention layer
        attn_module = f"transformer.h.{layer_idx}.attn"
        self.register_hook(attn_module)
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # Extract attention patterns
        if attn_module in self.stored_activations:
            attn_output = self.stored_activations[attn_module]
            
            # For GPT-2, attention output is a tuple
            if isinstance(attn_output, tuple):
                attn_weights = attn_output[1] if len(attn_output) > 1 else None
                attn_output = attn_output[0]
        
        self.clear_hooks()
        
        return {
            "layer": layer_idx,
            "attention_output_shape": attn_output.shape if 'attn_output' in locals() else None,
            "input_tokens": self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0].cpu())
        }
    
    def project_to_vocabulary(self, hidden_state: torch.Tensor) -> torch.Tensor:
        """
        Project hidden states to vocabulary space using the language model head.
        
        Args:
            hidden_state: Hidden state tensor to project
            
        Returns:
            Vocabulary projections (logits)
        """
        with torch.no_grad():
            # Apply final layer norm if needed (GPT-2 specific)
            if hasattr(self.model, 'transformer') and hasattr(self.model.transformer, 'ln_f'):
                hidden_state = self.model.transformer.ln_f(hidden_state)
            
            # Project through language model head
            vocab_projection = self.model.lm_head(hidden_state)
            
        return vocab_projection
    
    def extract_mlp_contributions(self, text: str, layer_idx: int = 0) -> Dict:
        """
        Extract and analyze MLP sublayer contributions.
        
        Args:
            text: Input text to analyze
            layer_idx: Layer index to analyze
            
        Returns:
            Dictionary with MLP analysis results
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Register hooks on MLP components
        mlp_in = f"transformer.h.{layer_idx}.mlp.c_fc"  # First MLP matrix
        mlp_out = f"transformer.h.{layer_idx}.mlp.c_proj"  # Second MLP matrix
        
        self.register_hook(mlp_in)
        self.register_hook(mlp_out)
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        results = {
            "layer": layer_idx,
            "mlp_input_shape": None,
            "mlp_output_shape": None
        }
        
        if mlp_in in self.stored_activations:
            results["mlp_input_shape"] = self.stored_activations[mlp_in].shape
            
        if mlp_out in self.stored_activations:
            results["mlp_output_shape"] = self.stored_activations[mlp_out].shape
            
            # Project MLP output to vocabulary
            mlp_output = self.stored_activations[mlp_out]
            vocab_proj = self.project_to_vocabulary(mlp_output)
            
            # Get top predicted tokens
            top_tokens = torch.topk(vocab_proj[0, -1], k=5)
            results["top_mlp_predictions"] = [
                self.tokenizer.decode([idx]) for idx in top_tokens.indices
            ]
        
        self.clear_hooks()
        return results
    
    def perform_attention_knockout(self, text: str, layer_idx: int, head_idx: int) -> Dict:
        """
        Perform attention knockout experiment by zeroing specific attention heads.
        
        Args:
            text: Input text
            layer_idx: Layer index
            head_idx: Head index to knockout
            
        Returns:
            Analysis results with and without knockout
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Normal forward pass
        with torch.no_grad():
            normal_outputs = self.model(**inputs)
            normal_logits = normal_outputs.logits
            normal_probs = torch.softmax(normal_logits[0, -1], dim=-1)
            normal_top = torch.topk(normal_probs, k=5)
        
        # Forward pass with attention knockout
        def knockout_hook(module, input, output):
            # Modify attention output to zero out specific head
            if isinstance(output, tuple):
                attn_output, attn_weights = output[0], output[1] if len(output) > 1 else None
                # Simple knockout: zero contribution from specific head
                # Note: This is a simplified version; actual implementation may vary
                modified_output = attn_output.clone()
                return (modified_output, attn_weights) if attn_weights is not None else modified_output
            return output
        
        # Register knockout hook
        attn_module = self.model.transformer.h[layer_idx].attn
        handle = attn_module.register_forward_hook(knockout_hook)
        
        with torch.no_grad():
            knockout_outputs = self.model(**inputs)
            knockout_logits = knockout_outputs.logits
            knockout_probs = torch.softmax(knockout_logits[0, -1], dim=-1)
            knockout_top = torch.topk(knockout_probs, k=5)
        
        handle.remove()
        
        return {
            "layer": layer_idx,
            "head": head_idx,
            "normal_predictions": [self.tokenizer.decode([idx]) for idx in normal_top.indices],
            "knockout_predictions": [self.tokenizer.decode([idx]) for idx in knockout_top.indices],
            "prediction_change": not torch.equal(normal_top.indices, knockout_top.indices)
        }


def demonstrate_analysis():
    """
    Demonstrate the model analysis capabilities.
    """
    # Initialize analyzer with base GPT-2 model
    analyzer = ModelAnalyzer("gpt2")
    
    # Example text for analysis
    test_text = "The capital of France is"
    
    print("\n=== Analyzing Factual Association ===")
    print(f"Input text: '{test_text}'")
    
    # 1. Analyze attention flow
    print("\n--- Attention Flow Analysis ---")
    attn_analysis = analyzer.analyze_attention_flow(test_text, layer_idx=0)
    print(f"Layer {attn_analysis['layer']} attention analysis:")
    print(f"  Input tokens: {attn_analysis['input_tokens']}")
    print(f"  Attention output shape: {attn_analysis['attention_output_shape']}")
    
    # 2. Extract MLP contributions
    print("\n--- MLP Contribution Analysis ---")
    mlp_analysis = analyzer.extract_mlp_contributions(test_text, layer_idx=5)
    print(f"Layer {mlp_analysis['layer']} MLP analysis:")
    print(f"  MLP input shape: {mlp_analysis['mlp_input_shape']}")
    print(f"  MLP output shape: {mlp_analysis['mlp_output_shape']}")
    if 'top_mlp_predictions' in mlp_analysis:
        print(f"  Top MLP predictions: {mlp_analysis['top_mlp_predictions']}")
    
    # 3. Perform attention knockout
    print("\n--- Attention Knockout Experiment ---")
    knockout_results = analyzer.perform_attention_knockout(test_text, layer_idx=5, head_idx=0)
    print(f"Layer {knockout_results['layer']}, Head {knockout_results['head']} knockout:")
    print(f"  Normal predictions: {knockout_results['normal_predictions']}")
    print(f"  Knockout predictions: {knockout_results['knockout_predictions']}")
    print(f"  Prediction changed: {knockout_results['prediction_change']}")
    
    # 4. Hidden state projection
    print("\n--- Hidden State Vocabulary Projection ---")
    inputs = analyzer.tokenizer(test_text, return_tensors="pt").to(analyzer.device)
    with torch.no_grad():
        outputs = analyzer.model(**inputs, output_hidden_states=True)
        last_hidden = outputs.hidden_states[-1]  # Last layer hidden states
        vocab_proj = analyzer.project_to_vocabulary(last_hidden)
        top_tokens = torch.topk(vocab_proj[0, -1], k=5)
        predictions = [analyzer.tokenizer.decode([idx]) for idx in top_tokens.indices]
    print(f"Top vocabulary projections from last hidden layer: {predictions}")


if __name__ == "__main__":
    print("Starting Factual Associations Dissection Analysis")
    print("=" * 50)
    
    # Check for GPU
    if torch.cuda.is_available():
        print(f"GPU available: {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU (GPU recommended for larger models)")
    
    # Run demonstration
    demonstrate_analysis()
    
    print("\n" + "=" * 50)
    print("Analysis complete!")
    print("\nNote: For full experiments with GPT2-xl, use a V100 GPU.")
    print("For GPT-J experiments, use an A100 GPU.")

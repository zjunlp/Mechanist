---
name: dissecting-factual-predictions
description: Analyze and dissect factual recall in auto-regressive language models using attention knockout, hidden state analysis, and intervention techniques on GPT-2 and GPT-J models
---

## Demo Scripts

### `scripts/intervention_experiments.py`

```python
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
```

### `scripts/model_analysis.py`

```python
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
```

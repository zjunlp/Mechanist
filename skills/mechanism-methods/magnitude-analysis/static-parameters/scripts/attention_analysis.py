#!/usr/bin/env python3
"""
Attention Analysis for Massive Values in LLMs

This script demonstrates how to extract and analyze attention matrices (Q, K, V)
from transformer models to identify massive values in low-frequency dimensions.
"""

import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
from typing import Dict, List, Tuple, Optional
import argparse

class AttentionAnalyzer:
    """
    Analyzer for extracting and visualizing attention patterns in LLMs.
    """
    
    def __init__(self, model_name: str, device: str = 'cuda'):
        """
        Initialize the attention analyzer with a specific model.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run the model on ('cuda' or 'cpu')
        """
        self.model_name = model_name
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map='auto'
        )
        self.attention_weights = {}
        
    def extract_attention_states(self, 
                                  text: str, 
                                  layers: List[int] = None) -> Dict[str, torch.Tensor]:
        """
        Extract Q, K, V states from specified layers.
        
        Args:
            text: Input text to analyze
            layers: List of layer indices to extract (None for all)
            
        Returns:
            Dictionary containing Q, K, V tensors for each layer
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Storage for attention states
        attention_states = {
            'query': {},
            'key': {},
            'value': {}
        }
        
        # Register hooks to capture attention states
        hooks = []
        
        def create_hook(layer_idx):
            def hook_fn(module, input, output):
                # Extract Q, K, V from attention output
                if hasattr(module, 'q_proj'):
                    hidden_states = input[0]
                    query_states = module.q_proj(hidden_states)
                    key_states = module.k_proj(hidden_states)
                    value_states = module.v_proj(hidden_states)
                    
                    attention_states['query'][layer_idx] = query_states.detach().cpu()
                    attention_states['key'][layer_idx] = key_states.detach().cpu()
                    attention_states['value'][layer_idx] = value_states.detach().cpu()
            return hook_fn
        
        # Register hooks on attention layers
        for idx, layer in enumerate(self.model.model.layers):
            if layers is None or idx in layers:
                hook = layer.self_attn.register_forward_hook(create_hook(idx))
                hooks.append(hook)
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Remove hooks
        for hook in hooks:
            hook.remove()
            
        return attention_states
    
    def identify_massive_values(self, 
                                attention_states: Dict[str, torch.Tensor],
                                threshold_percentile: float = 99.0) -> Dict[str, List[Tuple]]:
        """
        Identify massive values in attention matrices.
        
        Args:
            attention_states: Dictionary of Q, K, V states
            threshold_percentile: Percentile threshold for identifying massive values
            
        Returns:
            Dictionary containing positions of massive values
        """
        massive_values = {
            'query': [],
            'key': [],
            'value': []
        }
        
        for matrix_type in ['query', 'key', 'value']:
            for layer_idx, tensor in attention_states[matrix_type].items():
                # Calculate L2 norm across embedding dimension
                norms = torch.norm(tensor, dim=-1)
                
                # Find threshold
                threshold = torch.quantile(norms.flatten(), threshold_percentile / 100)
                
                # Find positions exceeding threshold
                positions = torch.where(norms > threshold)
                
                for i in range(len(positions[0])):
                    massive_values[matrix_type].append({
                        'layer': layer_idx,
                        'batch': positions[0][i].item(),
                        'position': positions[1][i].item() if len(positions) > 1 else 0,
                        'head': positions[2][i].item() if len(positions) > 2 else 0,
                        'value': norms[tuple(p[i] for p in positions)].item()
                    })
                    
        return massive_values
    
    def analyze_frequency_distribution(self, 
                                      attention_states: Dict[str, torch.Tensor]) -> Dict:
        """
        Analyze the frequency distribution of attention values.
        
        Args:
            attention_states: Dictionary of Q, K, V states
            
        Returns:
            Frequency analysis results
        """
        results = {}
        
        for matrix_type in ['query', 'key', 'value']:
            results[matrix_type] = {}
            
            for layer_idx, tensor in attention_states[matrix_type].items():
                # Reshape to (batch * seq_len * num_heads, hidden_dim)
                reshaped = tensor.view(-1, tensor.size(-1))
                
                # Apply FFT to analyze frequency components
                fft_result = torch.fft.rfft(reshaped, dim=-1)
                magnitude = torch.abs(fft_result)
                
                # Separate into low and high frequency
                freq_bins = magnitude.size(-1)
                low_freq_cutoff = freq_bins // 4
                
                low_freq_energy = torch.sum(magnitude[:, :low_freq_cutoff], dim=-1)
                high_freq_energy = torch.sum(magnitude[:, low_freq_cutoff:], dim=-1)
                
                results[matrix_type][layer_idx] = {
                    'low_freq_mean': low_freq_energy.mean().item(),
                    'high_freq_mean': high_freq_energy.mean().item(),
                    'low_freq_std': low_freq_energy.std().item(),
                    'high_freq_std': high_freq_energy.std().item(),
                    'ratio': (low_freq_energy.mean() / high_freq_energy.mean()).item()
                }
                
        return results
    
    def visualize_attention_maps(self, 
                                 attention_states: Dict[str, torch.Tensor],
                                 layer_idx: int,
                                 save_path: str = None):
        """
        Create visualization of attention patterns.
        
        Args:
            attention_states: Dictionary of Q, K, V states
            layer_idx: Layer index to visualize
            save_path: Path to save the visualization
        """
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        for idx, (matrix_type, ax) in enumerate(zip(['query', 'key', 'value'], axes)):
            if layer_idx in attention_states[matrix_type]:
                tensor = attention_states[matrix_type][layer_idx]
                
                # Calculate norms for visualization
                norms = torch.norm(tensor, dim=-1).squeeze(0)
                
                # Create heatmap
                im = ax.imshow(norms.cpu().numpy(), aspect='auto', cmap='hot')
                ax.set_title(f'{matrix_type.upper()} - Layer {layer_idx}')
                ax.set_xlabel('Hidden Dimension')
                ax.set_ylabel('Attention Head')
                plt.colorbar(im, ax=ax)
        
        plt.suptitle(f'Attention Analysis - {self.model_name}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Visualization saved to {save_path}")
        else:
            plt.show()
        
        plt.close()

def main():
    """
    Main function to run attention analysis.
    """
    parser = argparse.ArgumentParser(description='Analyze massive values in LLM attention')
    parser.add_argument('--model_name', type=str, 
                       default='meta-llama/Llama-2-7b-chat-hf',
                       help='HuggingFace model name')
    parser.add_argument('--text', type=str,
                       default="The capital of France is Paris. What is the capital of France?",
                       help='Input text to analyze')
    parser.add_argument('--layers', type=int, nargs='+',
                       default=[1, 2, 10],
                       help='Layer indices to analyze')
    parser.add_argument('--save_dir', type=str,
                       default='./attention_analysis_output',
                       help='Directory to save results')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.save_dir, exist_ok=True)
    
    # Initialize analyzer
    print(f"Initializing analyzer for {args.model_name}...")
    analyzer = AttentionAnalyzer(args.model_name)
    
    # Extract attention states
    print("Extracting attention states...")
    attention_states = analyzer.extract_attention_states(args.text, args.layers)
    
    # Identify massive values
    print("Identifying massive values...")
    massive_values = analyzer.identify_massive_values(attention_states)
    
    # Print summary
    for matrix_type in ['query', 'key', 'value']:
        count = len(massive_values[matrix_type])
        print(f"\n{matrix_type.upper()}: Found {count} massive values")
        if count > 0:
            # Show top 5
            sorted_values = sorted(massive_values[matrix_type], 
                                 key=lambda x: x['value'], 
                                 reverse=True)[:5]
            for item in sorted_values:
                print(f"  Layer {item['layer']}, Head {item['head']}: {item['value']:.2f}")
    
    # Analyze frequency distribution
    print("\nAnalyzing frequency distribution...")
    freq_analysis = analyzer.analyze_frequency_distribution(attention_states)
    
    for matrix_type in ['query', 'key', 'value']:
        print(f"\n{matrix_type.upper()} Frequency Analysis:")
        for layer_idx, stats in freq_analysis[matrix_type].items():
            print(f"  Layer {layer_idx}:")
            print(f"    Low-freq/High-freq ratio: {stats['ratio']:.3f}")
            print(f"    Low-freq mean: {stats['low_freq_mean']:.3f}")
            print(f"    High-freq mean: {stats['high_freq_mean']:.3f}")
    
    # Visualize each layer
    for layer_idx in args.layers:
        save_path = os.path.join(args.save_dir, f'attention_layer_{layer_idx}.png')
        analyzer.visualize_attention_maps(attention_states, layer_idx, save_path)
    
    # Save attention states
    for matrix_type in ['query', 'key', 'value']:
        for layer_idx, tensor in attention_states[matrix_type].items():
            save_path = os.path.join(args.save_dir, 
                                    f'{matrix_type}_layer_{layer_idx}.pt')
            torch.save(tensor, save_path)
            print(f"Saved {matrix_type} layer {layer_idx} to {save_path}")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()

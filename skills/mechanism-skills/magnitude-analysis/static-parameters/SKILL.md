---
name: static-parameters
description: Analyze and manipulate massive values in LLM attention mechanisms, particularly for understanding contextual knowledge processing in transformer models with RoPE
---

# Rope with LLM - Massive Values in Self-Attention Analysis

## When to Use

This skill should be activated when you need to:
- Analyze massive values appearing in transformer attention mechanisms (Q, K, V matrices)
- Understand how LLMs process contextual vs parametric knowledge
- Investigate the impact of RoPE (Rotary Positional Encoding) on attention patterns
- Perform experiments on attention value disruption and its effects
- Evaluate quantization methods' impact on contextual knowledge understanding
- Generate synthetic datasets for passkey retrieval and knowledge QA tasks
- Extract and visualize attention maps from various LLMs (Llama, Mistral, Qwen, Gemma, etc.)

**Trigger keywords:** massive values, attention mechanism, RoPE, contextual knowledge, attention maps, Q/K/V matrices, quantization impact, passkey retrieval, knowledge QA

## Quick Reference

- **Paper:** [Massive Values in Self-Attention Modules are the Key to Contextual Knowledge Understanding](https://arxiv.org/abs/2502.01563)
- **Website:** [https://mingyuj666.github.io/massive_value/](https://mingyuj666.github.io/massive_value/)
- **Repository:** [https://github.com/MingyuJ666/Rope_with_LLM](https://github.com/MingyuJ666/Rope_with_LLM)
- **Conference:** ICML 2025 (Accepted)

## Installation/Setup

### Environment Setup
```bash
conda create -n myenv python=3.9
conda activate myenv
pip install -r requirements.txt
```

### Environment Variables Configuration
Create a `.env` file with:

## Demo Scripts

### `scripts/attention_analysis.py`

```python
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
```

### `scripts/disruption_experiment.py`

```python
#!/usr/bin/env python3
"""
Massive Value Disruption Experiments

This script performs experiments to test the impact of disrupting massive values
in attention mechanisms on model performance, particularly for contextual knowledge
understanding.
"""

import torch
import torch.nn as nn
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Dict, List, Optional, Tuple
import json
import argparse
from dataclasses import dataclass
import os
from tqdm import tqdm

@dataclass
class DisruptionConfig:
    """Configuration for disruption experiments."""
    disruption_type: str  # 'mean', 'zero', 'random', 'none'
    target_matrix: str  # 'query', 'key', 'value'
    num_outliers: int  # Number of top outliers to disrupt
    layers_to_disrupt: List[int]  # Which layers to apply disruption

class MassiveValueDisruptor:
    """
    Handles disruption of massive values in attention mechanisms.
    """
    
    def __init__(self, model_name: str, device: str = 'cuda'):
        """
        Initialize the disruptor with a model.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run experiments on
        """
        self.model_name = model_name
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map='auto'
        )
        self.original_forward_methods = {}
        
    def apply_disruption(self, config: DisruptionConfig):
        """
        Apply disruption to specified attention matrices.
        
        Args:
            config: Configuration specifying disruption parameters
        """
        for layer_idx in config.layers_to_disrupt:
            layer = self.model.model.layers[layer_idx]
            
            # Store original forward method
            if layer_idx not in self.original_forward_methods:
                self.original_forward_methods[layer_idx] = layer.self_attn.forward
            
            # Create disrupted forward method
            def create_disrupted_forward(original_forward, layer_idx):
                def disrupted_forward(hidden_states, attention_mask=None, 
                                    position_ids=None, past_key_value=None,
                                    output_attentions=False, use_cache=False, **kwargs):
                    
                    # Get Q, K, V projections
                    bsz, q_len, _ = hidden_states.size()
                    
                    query_states = layer.self_attn.q_proj(hidden_states)
                    key_states = layer.self_attn.k_proj(hidden_states)
                    value_states = layer.self_attn.v_proj(hidden_states)
                    
                    # Reshape for attention heads
                    query_states = query_states.view(bsz, q_len, 
                                                    layer.self_attn.num_heads, 
                                                    layer.self_attn.head_dim).transpose(1, 2)
                    key_states = key_states.view(bsz, q_len,
                                                layer.self_attn.num_key_value_heads,
                                                layer.self_attn.head_dim).transpose(1, 2)
                    value_states = value_states.view(bsz, q_len,
                                                    layer.self_attn.num_key_value_heads,
                                                    layer.self_attn.head_dim).transpose(1, 2)
                    
                    # Apply disruption based on config
                    if config.target_matrix in ['query', 'key']:
                        target_states = query_states if config.target_matrix == 'query' else key_states
                        
                        # Identify massive values
                        num_heads = target_states.size(1)
                        for head_idx in range(num_heads):
                            head_states = target_states[:, head_idx, :, :]
                            norms = torch.norm(head_states, dim=-1)
                            
                            # Find top outliers
                            values, indices = torch.topk(norms.flatten(), 
                                                        min(config.num_outliers, norms.numel()))
                            
                            if config.disruption_type == 'mean':
                                # Replace with mean
                                mean_val = head_states.mean()
                                for idx in indices:
                                    pos = (idx // head_states.size(-1), idx % head_states.size(-1))
                                    target_states[:, head_idx, pos[0], pos[1]] = mean_val
                                    
                            elif config.disruption_type == 'zero':
                                # Replace with zero
                                for idx in indices:
                                    pos = (idx // head_states.size(-1), idx % head_states.size(-1))
                                    target_states[:, head_idx, pos[0], pos[1]] = 0
                                    
                            elif config.disruption_type == 'random':
                                # Replace with random values
                                for idx in indices:
                                    pos = (idx // head_states.size(-1), idx % head_states.size(-1))
                                    target_states[:, head_idx, pos[0], pos[1]] = torch.randn_like(
                                        target_states[:, head_idx, pos[0], pos[1]]
                                    )
                        
                        # Update the states
                        if config.target_matrix == 'query':
                            query_states = target_states
                        else:
                            key_states = target_states
                    
                    # Continue with normal attention computation
                    # (Simplified - actual implementation would include RoPE, etc.)
                    attn_weights = torch.matmul(query_states, key_states.transpose(2, 3))
                    attn_weights = attn_weights / np.sqrt(layer.self_attn.head_dim)
                    
                    if attention_mask is not None:
                        attn_weights = attn_weights + attention_mask
                    
                    attn_weights = nn.functional.softmax(attn_weights, dim=-1)
                    attn_output = torch.matmul(attn_weights, value_states)
                    
                    attn_output = attn_output.transpose(1, 2).contiguous()
                    attn_output = attn_output.reshape(bsz, q_len, -1)
                    attn_output = layer.self_attn.o_proj(attn_output)
                    
                    return attn_output, None, past_key_value
                
                return disrupted_forward
            
            # Replace forward method
            layer.self_attn.forward = create_disrupted_forward(
                layer.self_attn.forward, layer_idx
            )
    
    def restore_original(self):
        """
        Restore original forward methods.
        """
        for layer_idx, original_forward in self.original_forward_methods.items():
            self.model.model.layers[layer_idx].self_attn.forward = original_forward
        self.original_forward_methods.clear()
    
    def evaluate_contextual_knowledge(self, 
                                     test_data: List[Dict],
                                     max_samples: int = None) -> Dict[str, float]:
        """
        Evaluate model performance on contextual knowledge tasks.
        
        Args:
            test_data: List of test examples with context and questions
            max_samples: Maximum number of samples to evaluate
            
        Returns:
            Dictionary of evaluation metrics
        """
        correct = 0
        total = 0
        results = []
        
        samples = test_data[:max_samples] if max_samples else test_data
        
        for sample in tqdm(samples, desc="Evaluating"):
            context = sample.get('context', '')
            question = sample.get('question', '')
            expected_answer = sample.get('answer', '')
            
            # Prepare input
            prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
            inputs = self.tokenizer(prompt, return_tensors="pt", 
                                   max_length=512, truncation=True).to(self.device)
            
            # Generate answer
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=50,
                    temperature=0.1,
                    do_sample=False
                )
            
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            generated_answer = generated_text.split("Answer:")[-1].strip()
            
            # Check correctness (simple string matching)
            is_correct = expected_answer.lower() in generated_answer.lower()
            correct += int(is_correct)
            total += 1
            
            results.append({
                'question': question,
                'expected': expected_answer,
                'generated': generated_answer,
                'correct': is_correct
            })
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'results': results
        }

def load_test_data(pattern: str, data_path: str = './datasets') -> List[Dict]:
    """
    Load test data for evaluation.
    
    Args:
        pattern: Dataset pattern ('city', 'aqua', 'imdb', etc.)
        data_path: Path to datasets directory
        
    Returns:
        List of test examples
    """
    file_path = os.path.join(data_path, f'{pattern}_test.json')
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        # Generate sample data if file doesn't exist
        print(f"Warning: {file_path} not found. Using sample data.")
        return [
            {
                'context': 'The Eiffel Tower is located in Paris, France. It was built in 1889.',
                'question': 'Where is the Eiffel Tower located?',
                'answer': 'Paris'
            },
            {
                'context': 'Python was created by Guido van Rossum and first released in 1991.',
                'question': 'Who created Python?',
                'answer': 'Guido van Rossum'
            }
        ]

def main():
    """
    Main function to run disruption experiments.
    """
    parser = argparse.ArgumentParser(description='Massive value disruption experiments')
    parser.add_argument('--model_name', type=str,
                       default='meta-llama/Llama-2-7b-chat-hf',
                       help='Model to test')
    parser.add_argument('--pattern', type=str, default='city',
                       choices=['city', 'aqua', 'imdb', 'sports', 'art', 'cele', 'long'],
                       help='Dataset pattern')
    parser.add_argument('--disruption_type', type=str, default='mean',
                       choices=['mean', 'zero', 'random', 'none'],
                       help='Type of disruption to apply')
    parser.add_argument('--target_matrix', type=str, default='query',
                       choices=['query', 'key', 'value'],
                       help='Which attention matrix to disrupt')
    parser.add_argument('--num_outliers', type=int, default=1,
                       help='Number of outliers to disrupt')
    parser.add_argument('--layers', type=int, nargs='+', default=[1, 2, 10],
                       help='Layers to disrupt')
    parser.add_argument('--max_samples', type=int, default=50,
                       help='Maximum samples to evaluate')
    parser.add_argument('--output_dir', type=str, default='./disruption_results',
                       help='Directory to save results')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize disruptor
    print(f"Initializing disruptor for {args.model_name}...")
    disruptor = MassiveValueDisruptor(args.model_name)
    
    # Load test data
    print(f"Loading {args.pattern} test data...")
    test_data = load_test_data(args.pattern)
    
    # Baseline evaluation (no disruption)
    print("\nEvaluating baseline (no disruption)...")
    baseline_results = disruptor.evaluate_contextual_knowledge(
        test_data, args.max_samples
    )
    print(f"Baseline accuracy: {baseline_results['accuracy']:.3f}")
    
    # Apply disruption and evaluate
    if args.disruption_type != 'none':
        print(f"\nApplying {args.disruption_type} disruption to {args.target_matrix}...")
        config = DisruptionConfig(
            disruption_type=args.disruption_type,
            target_matrix=args.target_matrix,
            num_outliers=args.num_outliers,
            layers_to_disrupt=args.layers
        )
        disruptor.apply_disruption(config)
        
        disrupted_results = disruptor.evaluate_contextual_knowledge(
            test_data, args.max_samples
        )
        print(f"Disrupted accuracy: {disrupted_results['accuracy']:.3f}")
        
        # Calculate performance drop
        performance_drop = baseline_results['accuracy'] - disrupted_results['accuracy']
        print(f"Performance drop: {performance_drop:.3f}")
        
        # Restore original model
        disruptor.restore_original()
    else:
        disrupted_results = baseline_results
        performance_drop = 0
    
    # Save results
    results = {
        'model': args.model_name,
        'pattern': args.pattern,
        'disruption_config': {
            'type': args.disruption_type,
            'target': args.target_matrix,
            'num_outliers': args.num_outliers,
            'layers': args.layers
        },
        'baseline_accuracy': baseline_results['accuracy'],
        'disrupted_accuracy': disrupted_results['accuracy'],
        'performance_drop': performance_drop,
        'baseline_results': baseline_results['results'][:10],  # Save sample
        'disrupted_results': disrupted_results['results'][:10]
    }
    
    output_file = os.path.join(
        args.output_dir,
        f'{args.pattern}_{args.disruption_type}_{args.target_matrix}_results.json'
    )
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    # Print summary
    print("\n" + "="*50)
    print("EXPERIMENT SUMMARY")
    print("="*50)
    print(f"Model: {args.model_name}")
    print(f"Dataset: {args.pattern}")
    print(f"Disruption: {args.disruption_type} on {args.target_matrix}")
    print(f"Baseline Accuracy: {baseline_results['accuracy']:.3f}")
    print(f"Disrupted Accuracy: {disrupted_results['accuracy']:.3f}")
    print(f"Performance Drop: {performance_drop:.3f}")

if __name__ == "__main__":
    main()
```

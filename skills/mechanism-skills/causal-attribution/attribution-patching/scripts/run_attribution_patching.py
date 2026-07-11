#!/usr/bin/env python3
"""
Edge Attribution Patching Example Script

This script demonstrates how to use the edge attribution patching framework
for automated circuit discovery in transformer models. It shows how to:
1. Set up an experiment with a specific task
2. Run attribution patching with different configurations
3. Analyze and save results

Requires: pip install transformer-lens torch numpy
"""

import json
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PatchingConfig:
    """Configuration for attribution patching experiments."""
    task: str  # 'ioi', 'greaterthan', or 'docstring'
    model_name: str
    threshold: float = 0.1
    use_abs_value: bool = True
    num_samples: int = 100
    batch_size: int = 10
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

class AttributionPatchingExperiment:
    """
    Main class for running edge attribution patching experiments.
    
    This demonstrates the core API for performing attribution patching
    to discover important circuits in transformer models.
    """
    
    def __init__(self, config: PatchingConfig):
        """
        Initialize the attribution patching experiment.
        
        Args:
            config: Configuration object with experiment parameters
        """
        self.config = config
        self.model = None
        self.dataset = None
        self.results = {
            'pruned_heads': [],
            'pruned_attrs': [],
            'num_passes': 0,
            'final_score': 0.0
        }
    
    def setup_model(self):
        """
        Load and configure the transformer model for analysis.
        
        Note: In actual implementation, this would load from TransformerLens
        """
        print(f"Loading model: {self.config.model_name}")
        # Placeholder for model loading
        # In practice: self.model = load_transformer_model(self.config.model_name)
        self.model = {'name': self.config.model_name, 'loaded': True}
    
    def prepare_dataset(self) -> Dict:
        """
        Prepare task-specific dataset for attribution patching.
        
        Returns:
            Dictionary containing prompts and labels for the task
        """
        print(f"Preparing dataset for task: {self.config.task}")
        
        if self.config.task == 'ioi':
            # IOI task: Indirect Object Identification
            dataset = {
                'prompts': [
                    "When Mary and John went to the store, John gave a drink to",
                    "After Tom and Sarah finished dinner, Sarah passed the salt to",
                ],
                'labels': ['Mary', 'Tom'],
                'task_type': 'indirect_object'
            }
        elif self.config.task == 'greaterthan':
            # Greater-than comparison task
            dataset = {
                'prompts': [
                    "Compare 5 and 3: The larger number is",
                    "Between 10 and 7, the greater value is",
                ],
                'labels': ['5', '10'],
                'task_type': 'comparison'
            }
        elif self.config.task == 'docstring':
            # Docstring generation task
            dataset = {
                'prompts': [
                    "def add(a, b):\n    '''",
                    "def multiply(x, y):\n    '''",
                ],
                'labels': [
                    'Add two numbers together',
                    'Multiply two numbers'
                ],
                'task_type': 'generation'
            }
        else:
            raise ValueError(f"Unknown task: {self.config.task}")
        
        self.dataset = dataset
        return dataset
    
    def compute_attributions(self, prompt: str, label: str) -> np.ndarray:
        """
        Compute edge attributions for a given prompt-label pair.
        
        Args:
            prompt: Input prompt text
            label: Expected output label
            
        Returns:
            Attribution matrix for model edges
        """
        # Placeholder for attribution computation
        # In practice, this would use gradient-based attribution methods
        print(f"Computing attributions for prompt: {prompt[:50]}...")
        
        # Simulate attribution matrix (layers x heads x embedding_dim)
        n_layers = 12
        n_heads = 12
        attribution_matrix = np.random.randn(n_layers, n_heads)
        
        if self.config.use_abs_value:
            attribution_matrix = np.abs(attribution_matrix)
        
        return attribution_matrix
    
    def prune_edges(self, attributions: np.ndarray, threshold: float) -> Tuple[List, List]:
        """
        Prune edges based on attribution scores and threshold.
        
        Args:
            attributions: Attribution matrix
            threshold: Pruning threshold
            
        Returns:
            Tuple of (pruned_heads, pruned_attrs)
        """
        pruned_heads = []
        pruned_attrs = []
        
        for layer_idx in range(attributions.shape[0]):
            for head_idx in range(attributions.shape[1]):
                attr_value = attributions[layer_idx, head_idx]
                
                if attr_value < threshold:
                    pruned_heads.append((layer_idx, head_idx))
                    pruned_attrs.append(float(attr_value))
        
        return pruned_heads, pruned_attrs
    
    def run_attribution_patching(self) -> Dict:
        """
        Run the complete attribution patching pipeline.
        
        Returns:
            Dictionary containing experiment results
        """
        print("Starting attribution patching experiment...")
        
        # Setup
        self.setup_model()
        dataset = self.prepare_dataset()
        
        all_attributions = []
        
        # Process each prompt-label pair
        for prompt, label in zip(dataset['prompts'], dataset['labels']):
            attrs = self.compute_attributions(prompt, label)
            all_attributions.append(attrs)
        
        # Aggregate attributions
        mean_attributions = np.mean(all_attributions, axis=0)
        
        # Iterative pruning
        current_threshold = self.config.threshold
        num_passes = 0
        max_passes = 10
        
        while num_passes < max_passes:
            num_passes += 1
            print(f"Pass {num_passes}: Pruning with threshold {current_threshold:.3f}")
            
            pruned_heads, pruned_attrs = self.prune_edges(
                mean_attributions, current_threshold
            )
            
            # Check convergence (simplified)
            if len(pruned_heads) > len(mean_attributions.flatten()) * 0.9:
                print("Convergence reached")
                break
            
            # Adaptive threshold update
            current_threshold *= 1.1
        
        # Store results
        self.results['pruned_heads'] = pruned_heads
        self.results['pruned_attrs'] = pruned_attrs
        self.results['num_passes'] = num_passes
        self.results['final_score'] = self.evaluate_circuit()
        
        return self.results
    
    def evaluate_circuit(self) -> float:
        """
        Evaluate the discovered circuit's performance.
        
        Returns:
            Performance score of the pruned circuit
        """
        # Placeholder evaluation
        # In practice, this would test the pruned model on held-out data
        num_edges_remaining = len(self.results['pruned_heads'])
        total_edges = 12 * 12  # layers * heads
        sparsity = 1.0 - (num_edges_remaining / total_edges)
        
        # Simulate performance score (higher sparsity with maintained accuracy)
        performance_score = 0.8 + 0.2 * sparsity
        
        return performance_score
    
    def save_results(self, output_path: str):
        """
        Save experiment results to JSON files.
        
        Args:
            output_path: Directory path for saving results
        """
        # Save pruned heads
        with open(f"{output_path}/pruned_heads_{self.config.task}.json", 'w') as f:
            json.dump(self.results['pruned_heads'], f, indent=2)
        
        # Save pruned attributions
        with open(f"{output_path}/pruned_attrs_{self.config.task}.json", 'w') as f:
            json.dump(self.results['pruned_attrs'], f, indent=2)
        
        # Save summary
        summary = {
            'task': self.config.task,
            'model': self.config.model_name,
            'threshold': self.config.threshold,
            'use_abs_value': self.config.use_abs_value,
            'num_passes': self.results['num_passes'],
            'final_score': self.results['final_score'],
            'num_pruned_edges': len(self.results['pruned_heads'])
        }
        
        with open(f"{output_path}/summary_{self.config.task}.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Results saved to {output_path}")

def main():
    """Main function demonstrating the attribution patching workflow."""
    
    # Example 1: IOI Task
    print("=" * 50)
    print("Running IOI Task Attribution Patching")
    print("=" * 50)
    
    ioi_config = PatchingConfig(
        task='ioi',
        model_name='gpt2-small',
        threshold=0.1,
        use_abs_value=True
    )
    
    ioi_exp = AttributionPatchingExperiment(ioi_config)
    ioi_results = ioi_exp.run_attribution_patching()
    
    print(f"\nIOI Results:")
    print(f"  Pruned {len(ioi_results['pruned_heads'])} edges")
    print(f"  Completed in {ioi_results['num_passes']} passes")
    print(f"  Final score: {ioi_results['final_score']:.3f}")
    
    # Example 2: Greater-than Task
    print("\n" + "=" * 50)
    print("Running Greater-than Task Attribution Patching")
    print("=" * 50)
    
    gt_config = PatchingConfig(
        task='greaterthan',
        model_name='gpt2-small',
        threshold=0.15,
        use_abs_value=True
    )
    
    gt_exp = AttributionPatchingExperiment(gt_config)
    gt_results = gt_exp.run_attribution_patching()
    
    print(f"\nGreater-than Results:")
    print(f"  Pruned {len(gt_results['pruned_heads'])} edges")
    print(f"  Completed in {gt_results['num_passes']} passes")
    print(f"  Final score: {gt_results['final_score']:.3f}")
    
    # Example 3: Docstring Task
    print("\n" + "=" * 50)
    print("Running Docstring Task Attribution Patching")
    print("=" * 50)
    
    doc_config = PatchingConfig(
        task='docstring',
        model_name='gpt2-medium',
        threshold=0.08,
        use_abs_value=False  # Try without absolute value
    )
    
    doc_exp = AttributionPatchingExperiment(doc_config)
    doc_results = doc_exp.run_attribution_patching()
    
    print(f"\nDocstring Results:")
    print(f"  Pruned {len(doc_results['pruned_heads'])} edges")
    print(f"  Completed in {doc_results['num_passes']} passes")
    print(f"  Final score: {doc_results['final_score']:.3f}")
    
    # Save all results
    print("\n" + "=" * 50)
    print("Saving Results")
    print("=" * 50)
    
    # Note: In practice, create output directory first
    # ioi_exp.save_results("./results/ioi_task")
    # gt_exp.save_results("./results/greaterthan_task")
    # doc_exp.save_results("./results/docstring_task")
    
    print("\nAll experiments completed successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Compute Perplexity with Deactivated Language-Specific Neurons

This script demonstrates how to compute perplexity on multilingual text data
when specific language neurons are deactivated, enabling analysis of how
neuron deactivation affects model performance.

Requires: pip install torch transformers
"""

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import numpy as np
from tqdm import tqdm

class TokenizedDataset(Dataset):
    """Dataset for pre-tokenized text data."""
    
    def __init__(self, data_path: str, max_length: int = 1024):
        """
        Initialize dataset with pre-tokenized data.
        
        Args:
            data_path: Path to tokenized data file (LongTensor)
            max_length: Maximum sequence length for each sample
        """
        self.data = torch.load(data_path, map_location='cpu')
        self.max_length = max_length
        
        # Split data into chunks
        self.chunks = []
        for i in range(0, len(self.data) - max_length, max_length):
            self.chunks.append(self.data[i:i + max_length])
    
    def __len__(self):
        return len(self.chunks)
    
    def __getitem__(self, idx):
        return self.chunks[idx]

class PerplexityCalculator:
    """Calculate perplexity with optional neuron deactivation."""
    
    def __init__(self, model_name: str, device: str = "cuda"):
        """
        Initialize the perplexity calculator.
        
        Args:
            model_name: Name or path of the model
            device: Device to use for computation
        """
        self.model_name = model_name
        self.device = device
        self.activation_masks = None
    
    def load_activation_masks(self, mask_path: str):
        """Load activation masks for neuron deactivation."""
        if Path(mask_path).exists():
            self.activation_masks = torch.load(mask_path, map_location=self.device)
            print(f"Loaded activation masks from {mask_path}")
        else:
            print(f"Warning: Mask file not found at {mask_path}")
    
    def apply_neuron_deactivation(self, activations: torch.Tensor, 
                                 layer_idx: int) -> torch.Tensor:
        """
        Apply neuron deactivation mask to layer activations.
        
        Args:
            activations: Layer activations (batch_size, seq_len, hidden_dim)
            layer_idx: Index of the current layer
        
        Returns:
            Modified activations with certain neurons deactivated
        """
        if self.activation_masks is None or layer_idx not in self.activation_masks:
            return activations
        
        mask = self.activation_masks[layer_idx].to(activations.device)
        
        # Expand mask to match activation dimensions
        if len(activations.shape) == 3:
            mask = mask.unsqueeze(0).unsqueeze(0)
            mask = mask.expand_as(activations)
        
        return activations * mask
    
    def compute_perplexity(self, 
                          data_loader: DataLoader,
                          apply_deactivation: bool = True) -> Dict:
        """
        Compute perplexity on the dataset.
        
        Args:
            data_loader: DataLoader for the tokenized dataset
            apply_deactivation: Whether to apply neuron deactivation
        
        Returns:
            Dictionary containing perplexity and related metrics
        """
        total_loss = 0.0
        total_tokens = 0
        batch_losses = []
        
        print(f"Computing perplexity with{'' if apply_deactivation else 'out'} neuron deactivation...")
        
        with torch.no_grad():
            for batch_idx, input_ids in enumerate(tqdm(data_loader)):
                input_ids = input_ids.to(self.device)
                
                # Shift inputs and targets for language modeling
                inputs = input_ids[:, :-1]
                targets = input_ids[:, 1:]
                
                # Simulate forward pass with deactivation
                # (In actual implementation, this would hook into the model)
                logits = self.simulated_forward(inputs, apply_deactivation)
                
                # Calculate loss
                loss = F.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    targets.reshape(-1),
                    reduction='none'
                )
                
                batch_loss = loss.mean().item()
                batch_losses.append(batch_loss)
                
                total_loss += loss.sum().item()
                total_tokens += targets.numel()
        
        # Calculate perplexity
        avg_loss = total_loss / total_tokens
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        
        return {
            "perplexity": perplexity,
            "avg_loss": avg_loss,
            "total_tokens": total_tokens,
            "batch_losses": batch_losses,
            "std_loss": np.std(batch_losses)
        }
    
    def simulated_forward(self, input_ids: torch.Tensor, 
                         apply_deactivation: bool) -> torch.Tensor:
        """
        Simulated forward pass (placeholder for actual model forward).
        In real implementation, this would use hooks to modify activations.
        
        Args:
            input_ids: Input token IDs
            apply_deactivation: Whether to apply neuron deactivation
        
        Returns:
            Logits tensor
        """
        # This is a simplified simulation
        # In practice, you would use model hooks to intercept and modify activations
        batch_size, seq_len = input_ids.shape
        vocab_size = 32000  # Typical vocab size for LLaMA models
        
        # Generate random logits for demonstration
        logits = torch.randn(batch_size, seq_len, vocab_size, device=input_ids.device)
        
        # If deactivation is applied, slightly increase the entropy
        if apply_deactivation and self.activation_masks:
            logits = logits * 0.95  # Simulated effect of deactivation
        
        return logits

class PerplexityExperiment:
    """Run comprehensive perplexity experiments."""
    
    def __init__(self, model_name: str, languages: List[str]):
        """
        Initialize experiment runner.
        
        Args:
            model_name: Model to use
            languages: List of languages to test
        """
        self.model_name = model_name
        self.languages = languages
        self.results = {}
    
    def run_language_comparison(self, 
                               data_dir: str,
                               mask_dir: str,
                               output_file: str):
        """
        Run perplexity comparison across languages.
        
        Args:
            data_dir: Directory containing tokenized data files
            mask_dir: Directory containing activation masks
            output_file: Path to save results
        """
        for lang in self.languages:
            print(f"\n{'='*50}")
            print(f"Testing language: {lang}")
            print('='*50)
            
            # Prepare data path
            data_path = f"{data_dir}/id.{lang}.train.llama"
            
            if not Path(data_path).exists():
                print(f"Data file not found: {data_path}")
                continue
            
            # Create dataset and dataloader
            dataset = TokenizedDataset(data_path)
            data_loader = DataLoader(dataset, batch_size=4, shuffle=False)
            
            # Calculate baseline perplexity (no deactivation)
            calculator = PerplexityCalculator(self.model_name)
            baseline_results = calculator.compute_perplexity(
                data_loader, apply_deactivation=False
            )
            
            lang_results = {
                "baseline": baseline_results,
                "deactivation_experiments": {}
            }
            
            # Test with different deactivation masks
            for mask_lang in self.languages:
                mask_path = f"{mask_dir}/mask_{mask_lang}_100%.pth"
                
                if Path(mask_path).exists():
                    calculator.load_activation_masks(mask_path)
                    deact_results = calculator.compute_perplexity(
                        data_loader, apply_deactivation=True
                    )
                    
                    # Calculate perplexity change
                    ppl_change = (deact_results["perplexity"] - baseline_results["perplexity"]) / baseline_results["perplexity"] * 100
                    
                    lang_results["deactivation_experiments"][mask_lang] = {
                        **deact_results,
                        "perplexity_change_percent": ppl_change
                    }
                    
                    print(f"  Deactivating {mask_lang} neurons: PPL {deact_results['perplexity']:.2f} "
                          f"(change: {ppl_change:+.2f}%)")
            
            self.results[lang] = lang_results
        
        # Save results
        self.save_results(output_file)
    
    def run_progressive_deactivation(self,
                                    data_path: str,
                                    mask_pattern: str,
                                    ratios: List[float]):
        """
        Test perplexity with progressive neuron deactivation.
        
        Args:
            data_path: Path to tokenized data
            mask_pattern: Pattern for mask files (with {ratio} placeholder)
            ratios: List of deactivation ratios to test
        """
        dataset = TokenizedDataset(data_path)
        data_loader = DataLoader(dataset, batch_size=4, shuffle=False)
        
        results = {"ratios": {}}
        
        for ratio in ratios:
            mask_path = mask_pattern.format(ratio=int(ratio*100))
            
            calculator = PerplexityCalculator(self.model_name)
            
            if Path(mask_path).exists():
                calculator.load_activation_masks(mask_path)
                ppl_results = calculator.compute_perplexity(
                    data_loader, apply_deactivation=True
                )
            else:
                print(f"Mask not found: {mask_path}")
                continue
            
            results["ratios"][f"{int(ratio*100)}%"] = {
                "ratio": ratio,
                **ppl_results
            }
            
            print(f"Deactivation {int(ratio*100)}%: PPL = {ppl_results['perplexity']:.2f}")
        
        return results
    
    def save_results(self, output_file: str):
        """Save experiment results to JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to {output_file}")

def plot_perplexity_changes(results: Dict):
    """
    Create a simple text-based visualization of perplexity changes.
    
    Args:
        results: Dictionary of experiment results
    """
    print("\n" + "="*60)
    print("Perplexity Impact Matrix")
    print("="*60)
    print("Rows: Test language | Columns: Deactivated language neurons")
    print("-"*60)
    
    languages = list(results.keys())
    
    # Header
    print(f"{'Test Lang':<10}", end="")
    for lang in languages:
        print(f"{lang:>8}", end="")
    print(f"{'Baseline':>10}")
    print("-"*60)
    
    # Data rows
    for test_lang in languages:
        print(f"{test_lang:<10}", end="")
        
        baseline_ppl = results[test_lang]["baseline"]["perplexity"]
        
        for deact_lang in languages:
            if deact_lang in results[test_lang]["deactivation_experiments"]:
                ppl = results[test_lang]["deactivation_experiments"][deact_lang]["perplexity"]
                change = (ppl - baseline_ppl) / baseline_ppl * 100
                print(f"{change:>+7.1f}%", end="")
            else:
                print(f"{'N/A':>8}", end="")
        
        print(f"{baseline_ppl:>10.2f}")

def main():
    parser = argparse.ArgumentParser(description="Compute perplexity with neuron deactivation")
    parser.add_argument("-m", "--model", type=str, required=True,
                       help="Model name or path")
    parser.add_argument("-d", "--data", type=str, required=True,
                       help="Path to tokenized data file or directory")
    parser.add_argument("-a", "--activation-mask", type=str,
                       help="Path to activation mask file")
    parser.add_argument("--languages", nargs="+", 
                       default=["en", "zh", "fr", "es", "vi", "id", "ja"],
                       help="Languages to test")
    parser.add_argument("--progressive", action="store_true",
                       help="Run progressive deactivation experiment")
    parser.add_argument("-o", "--output", type=str, default="perplexity_results.json",
                       help="Output file for results")
    
    args = parser.parse_args()
    
    try:
        if args.progressive:
            # Progressive deactivation experiment
            experiment = PerplexityExperiment(args.model, ["test"])
            ratios = [0.0, 0.25, 0.5, 0.75, 1.0]
            
            results = experiment.run_progressive_deactivation(
                args.data,
                args.activation_mask.replace(".pth", "_{ratio}.pth"),
                ratios
            )
            
            print("\nProgressive Deactivation Results:")
            print("-"*40)
            for ratio_key, ratio_results in results["ratios"].items():
                print(f"{ratio_key}: Perplexity = {ratio_results['perplexity']:.2f}")
        
        else:
            # Standard perplexity calculation
            if Path(args.data).is_dir():
                # Run comparison across languages
                experiment = PerplexityExperiment(args.model, args.languages)
                experiment.run_language_comparison(
                    args.data, 
                    Path(args.activation_mask).parent if args.activation_mask else "activation_mask",
                    args.output
                )
                
                # Visualize results
                if experiment.results:
                    plot_perplexity_changes(experiment.results)
            else:
                # Single file perplexity
                dataset = TokenizedDataset(args.data)
                data_loader = DataLoader(dataset, batch_size=4, shuffle=False)
                
                calculator = PerplexityCalculator(args.model)
                
                if args.activation_mask:
                    calculator.load_activation_masks(args.activation_mask)
                
                results = calculator.compute_perplexity(
                    data_loader,
                    apply_deactivation=(args.activation_mask is not None)
                )
                
                print(f"\nPerplexity: {results['perplexity']:.2f}")
                print(f"Average Loss: {results['avg_loss']:.4f}")
                print(f"Total Tokens: {results['total_tokens']:,}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

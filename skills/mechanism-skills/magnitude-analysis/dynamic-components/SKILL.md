---
name: dynamic-components
description: Identify and manipulate language-specific neurons in multilingual Large Language Models (LLMs) to understand and control language-specific behaviors in models like LLaMA-2, BLOOM, OPT, Mistral, and Phi-2
---

## Demo Scripts

### `scripts/compute_perplexity.py`

```python
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
```

### `scripts/deactivate_neurons.py`

```python
#!/usr/bin/env python3
"""
Deactivate Language-Specific Neurons and Analyze Model Behavior

This script demonstrates how to create activation masks to deactivate specific
language neurons and analyze the resulting model behavior changes.

Requires: pip install torch numpy
"""

import torch
import numpy as np
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class NeuronMaskGenerator:
    """Generate activation masks for deactivating specific neurons."""
    
    def __init__(self, model_config: Dict):
        """
        Initialize the mask generator with model configuration.
        
        Args:
            model_config: Dictionary containing model dimensions
                         {num_layers, hidden_size, intermediate_size}
        """
        self.num_layers = model_config.get("num_layers", 32)
        self.hidden_size = model_config.get("hidden_size", 4096)
        self.intermediate_size = model_config.get("intermediate_size", 11008)
    
    def create_activation_mask(self, 
                              neurons_to_deactivate: List[List[torch.LongTensor]],
                              mask_type: str = "mlp") -> Dict[int, torch.Tensor]:
        """
        Create activation masks for deactivating specific neurons.
        
        Args:
            neurons_to_deactivate: List of neuron indices per layer
            mask_type: Type of mask ("mlp" for MLP layers, "attention" for attention)
        
        Returns:
            Dictionary mapping layer indices to activation masks
        """
        masks = {}
        
        for layer_idx, neuron_indices in enumerate(neurons_to_deactivate):
            if mask_type == "mlp":
                # Create mask for MLP/FFN neurons
                mask = torch.ones(self.intermediate_size, dtype=torch.float32)
                if len(neuron_indices) > 0:
                    mask[neuron_indices] = 0.0
                masks[layer_idx] = mask
            elif mask_type == "attention":
                # Create mask for attention heads (simplified)
                mask = torch.ones(self.hidden_size, dtype=torch.float32)
                if len(neuron_indices) > 0:
                    # Map neuron indices to attention dimensions
                    attention_dims = neuron_indices % self.hidden_size
                    mask[attention_dims] = 0.0
                masks[layer_idx] = mask
        
        return masks
    
    def save_masks(self, masks: Dict[int, torch.Tensor], output_path: str):
        """Save activation masks to file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(masks, output_path)
        print(f"Saved activation masks to {output_path}")
    
    def load_masks(self, mask_path: str) -> Dict[int, torch.Tensor]:
        """Load activation masks from file."""
        if not Path(mask_path).exists():
            raise FileNotFoundError(f"Mask file not found: {mask_path}")
        return torch.load(mask_path, map_location='cpu')

class NeuronAnalyzer:
    """Analyze the effects of neuron deactivation."""
    
    def __init__(self, neuron_file: str):
        """
        Initialize analyzer with pre-identified neurons.
        
        Args:
            neuron_file: Path to .neuron.pth file
        """
        self.neurons = torch.load(neuron_file, map_location='cpu')
        self.lang_map = {"en": 0, "zh": 1, "fr": 2, "es": 3, "vi": 4, "id": 5, "ja": 6}
    
    def get_language_neurons(self, language: str) -> List[torch.LongTensor]:
        """Get all neurons for a specific language."""
        if language not in self.lang_map:
            raise ValueError(f"Invalid language: {language}")
        return self.neurons[self.lang_map[language]]
    
    def create_deactivation_experiment(self, 
                                      target_language: str,
                                      deactivation_ratio: float = 1.0) -> List[List[int]]:
        """
        Create an experiment by selecting neurons to deactivate.
        
        Args:
            target_language: Language whose neurons to deactivate
            deactivation_ratio: Fraction of neurons to deactivate (0-1)
        
        Returns:
            List of neuron indices per layer to deactivate
        """
        lang_neurons = self.get_language_neurons(target_language)
        deactivation_list = []
        
        for layer_neurons in lang_neurons:
            num_neurons = len(layer_neurons)
            num_to_deactivate = int(num_neurons * deactivation_ratio)
            
            if num_to_deactivate > 0:
                # Randomly select neurons to deactivate
                indices = torch.randperm(num_neurons)[:num_to_deactivate]
                selected_neurons = layer_neurons[indices]
                deactivation_list.append(selected_neurons)
            else:
                deactivation_list.append(torch.LongTensor([]))
        
        return deactivation_list
    
    def analyze_cross_lingual_impact(self, 
                                    source_language: str,
                                    target_languages: List[str]) -> Dict:
        """
        Analyze how deactivating one language's neurons affects others.
        
        Args:
            source_language: Language whose neurons to deactivate
            target_languages: Languages to test impact on
        
        Returns:
            Analysis results
        """
        source_neurons = self.get_language_neurons(source_language)
        results = {
            "source_language": source_language,
            "impacts": {}
        }
        
        # Convert source neurons to sets for efficient lookup
        source_sets = [set(layer.tolist()) for layer in source_neurons]
        
        for target_lang in target_languages:
            if target_lang == source_language:
                continue
            
            target_neurons = self.get_language_neurons(target_lang)
            
            # Calculate overlap
            total_overlap = 0
            total_target = 0
            layer_overlaps = []
            
            for layer_idx, (source_set, target_layer) in enumerate(zip(source_sets, target_neurons)):
                target_set = set(target_layer.tolist())
                overlap = len(source_set & target_set)
                total_overlap += overlap
                total_target += len(target_set)
                
                layer_overlaps.append({
                    "layer": layer_idx,
                    "overlap": overlap,
                    "target_total": len(target_set),
                    "impact_ratio": overlap / len(target_set) if target_set else 0
                })
            
            results["impacts"][target_lang] = {
                "total_overlap": total_overlap,
                "total_target_neurons": total_target,
                "overall_impact": total_overlap / total_target if total_target > 0 else 0,
                "layer_details": layer_overlaps
            }
        
        return results

def get_model_config(model_name: str) -> Dict:
    """Get model configuration based on model name."""
    configs = {
        "llama-7b": {"num_layers": 32, "hidden_size": 4096, "intermediate_size": 11008},
        "llama-13b": {"num_layers": 40, "hidden_size": 5120, "intermediate_size": 13824},
        "llama-70b": {"num_layers": 80, "hidden_size": 8192, "intermediate_size": 28672},
        "bloom-7b": {"num_layers": 30, "hidden_size": 4096, "intermediate_size": 16384},
        "opt-6.7b": {"num_layers": 32, "hidden_size": 4096, "intermediate_size": 16384},
        "mistral-7b": {"num_layers": 32, "hidden_size": 4096, "intermediate_size": 14336},
        "phi-2": {"num_layers": 32, "hidden_size": 2560, "intermediate_size": 10240}
    }
    return configs.get(model_name, configs["llama-7b"])

def create_progressive_deactivation(analyzer: NeuronAnalyzer, 
                                   language: str,
                                   ratios: List[float]) -> Dict:
    """
    Create masks for progressive deactivation experiments.
    
    Args:
        analyzer: NeuronAnalyzer instance
        language: Target language
        ratios: List of deactivation ratios to test
    
    Returns:
        Dictionary of deactivation experiments
    """
    experiments = {}
    
    for ratio in ratios:
        neurons_to_deactivate = analyzer.create_deactivation_experiment(language, ratio)
        experiments[f"{int(ratio*100)}%"] = {
            "ratio": ratio,
            "neurons": neurons_to_deactivate,
            "total_deactivated": sum(len(layer) for layer in neurons_to_deactivate)
        }
    
    return experiments

def main():
    parser = argparse.ArgumentParser(description="Create and analyze neuron deactivation masks")
    parser.add_argument("-n", "--neuron-file", type=str, required=True,
                       help="Path to .neuron.pth file")
    parser.add_argument("-m", "--model", type=str, default="llama-7b",
                       help="Model name for configuration")
    parser.add_argument("-l", "--language", type=str, default="zh",
                       help="Language to deactivate (en, zh, fr, es, vi, id, ja)")
    parser.add_argument("-r", "--ratio", type=float, default=1.0,
                       help="Deactivation ratio (0-1)")
    parser.add_argument("-o", "--output", type=str, default="activation_mask/experiment.pth",
                       help="Output path for activation mask")
    parser.add_argument("--analyze-impact", action="store_true",
                       help="Analyze cross-lingual impact")
    parser.add_argument("--progressive", action="store_true",
                       help="Create progressive deactivation experiments")
    
    args = parser.parse_args()
    
    try:
        # Initialize components
        model_config = get_model_config(args.model)
        mask_generator = NeuronMaskGenerator(model_config)
        analyzer = NeuronAnalyzer(args.neuron_file)
        
        if args.progressive:
            # Create progressive deactivation experiments
            ratios = [0.1, 0.25, 0.5, 0.75, 1.0]
            experiments = create_progressive_deactivation(analyzer, args.language, ratios)
            
            print(f"\nProgressive Deactivation for {args.language}:")
            print("-" * 50)
            for name, exp in experiments.items():
                print(f"{name}: {exp['total_deactivated']} neurons deactivated")
                
                # Create and save mask for each ratio
                masks = mask_generator.create_activation_mask(exp['neurons'])
                output_path = args.output.replace('.pth', f'_{args.language}_{name}.pth')
                mask_generator.save_masks(masks, output_path)
        
        elif args.analyze_impact:
            # Analyze cross-lingual impact
            all_languages = ["en", "zh", "fr", "es", "vi", "id", "ja"]
            target_languages = [l for l in all_languages if l != args.language]
            
            impact_analysis = analyzer.analyze_cross_lingual_impact(
                args.language, target_languages
            )
            
            print(f"\nCross-lingual Impact Analysis")
            print(f"Deactivating: {impact_analysis['source_language']}")
            print("-" * 50)
            
            for lang, impact in impact_analysis["impacts"].items():
                print(f"\nImpact on {lang}:")
                print(f"  Total overlap: {impact['total_overlap']} neurons")
                print(f"  Overall impact: {impact['overall_impact']:.2%}")
                
                # Show top impacted layers
                top_layers = sorted(impact['layer_details'], 
                                  key=lambda x: x['impact_ratio'], 
                                  reverse=True)[:3]
                print("  Most impacted layers:")
                for layer in top_layers:
                    print(f"    Layer {layer['layer']}: {layer['impact_ratio']:.2%} affected")
        
        else:
            # Standard deactivation
            neurons_to_deactivate = analyzer.create_deactivation_experiment(
                args.language, args.ratio
            )
            
            # Create activation masks
            masks = mask_generator.create_activation_mask(neurons_to_deactivate)
            
            # Save masks
            mask_generator.save_masks(masks, args.output)
            
            # Print statistics
            total_neurons = sum(len(layer) for layer in neurons_to_deactivate)
            print(f"\nDeactivation Summary:")
            print(f"  Language: {args.language}")
            print(f"  Deactivation ratio: {args.ratio:.1%}")
            print(f"  Total neurons deactivated: {total_neurons}")
            print(f"  Masks saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

### `scripts/load_neurons.py`

```python
#!/usr/bin/env python3
"""
Load and Analyze Pre-identified Language-Specific Neurons

This script demonstrates how to load and analyze the pre-identified language-specific
neurons for various multilingual models including LLaMA-2, BLOOM, OPT, Mistral, and Phi-2.

Requires: pip install torch
"""

import torch
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Language mapping
LANGUAGE_MAPPING = {
    0: "en (English)",
    1: "zh (Chinese)",
    2: "fr (French)",
    3: "es (Spanish)",
    4: "vi (Vietnamese)",
    5: "id (Indonesian)",
    6: "ja (Japanese)"
}

# Available model files
MODEL_FILES = {
    "llama-7b": "LLaMA-2-7B.neuron.pth",
    "llama-13b": "LLaMA-2-13B.neuron.pth",
    "llama-70b": "LLaMA-2-70B.neuron.pth",
    "bloom-7b": "BLOOM-7B.neuron.pth",
    "opt-6.7b": "OPT-6.7B.neuron.pth",
    "mistral-7b": "Mistral-7B.neuron.pth",
    "phi-2": "Phi-2-2.7B.neuron.pth"
}

def load_neurons(file_path: str) -> List[List[torch.LongTensor]]:
    """
    Load pre-identified language-specific neurons from a .pth file.
    
    Args:
        file_path: Path to the .neuron.pth file
    
    Returns:
        A nested list where neurons[lang_idx][layer_idx] contains neuron indices
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Neuron file not found: {file_path}")
    
    neurons = torch.load(file_path, map_location='cpu')
    return neurons

def analyze_neurons(neurons: List[List[torch.LongTensor]], model_name: str) -> Dict:
    """
    Analyze the distribution of language-specific neurons across layers.
    
    Args:
        neurons: Loaded neuron data
        model_name: Name of the model for reporting
    
    Returns:
        Dictionary containing analysis results
    """
    analysis = {
        "model": model_name,
        "num_languages": len(neurons),
        "num_layers": len(neurons[0]) if neurons else 0,
        "language_stats": {}
    }
    
    for lang_idx, lang_neurons in enumerate(neurons):
        lang_name = LANGUAGE_MAPPING.get(lang_idx, f"Unknown ({lang_idx})")
        
        total_neurons = sum(len(layer_neurons) for layer_neurons in lang_neurons)
        neurons_per_layer = [len(layer_neurons) for layer_neurons in lang_neurons]
        
        analysis["language_stats"][lang_name] = {
            "total_neurons": total_neurons,
            "neurons_per_layer": neurons_per_layer,
            "avg_neurons_per_layer": total_neurons / len(lang_neurons) if lang_neurons else 0,
            "max_neurons_in_layer": max(neurons_per_layer) if neurons_per_layer else 0,
            "min_neurons_in_layer": min(neurons_per_layer) if neurons_per_layer else 0
        }
    
    return analysis

def get_specific_neurons(neurons: List[List[torch.LongTensor]], 
                        language: str, 
                        layer: int) -> Optional[torch.LongTensor]:
    """
    Get neuron indices for a specific language and layer.
    
    Args:
        neurons: Loaded neuron data
        language: Language code (en, zh, fr, es, vi, id, ja)
        layer: Layer index
    
    Returns:
        Tensor of neuron indices or None if not found
    """
    # Map language code to index
    lang_map = {"en": 0, "zh": 1, "fr": 2, "es": 3, "vi": 4, "id": 5, "ja": 6}
    
    if language not in lang_map:
        print(f"Invalid language code: {language}")
        return None
    
    lang_idx = lang_map[language]
    
    if lang_idx >= len(neurons):
        print(f"Language index {lang_idx} out of range")
        return None
    
    if layer >= len(neurons[lang_idx]):
        print(f"Layer {layer} out of range for language {language}")
        return None
    
    return neurons[lang_idx][layer]

def compare_language_overlap(neurons: List[List[torch.LongTensor]], 
                            lang1: str, 
                            lang2: str) -> Dict:
    """
    Compare neuron overlap between two languages across all layers.
    
    Args:
        neurons: Loaded neuron data
        lang1: First language code
        lang2: Second language code
    
    Returns:
        Dictionary with overlap statistics
    """
    lang_map = {"en": 0, "zh": 1, "fr": 2, "es": 3, "vi": 4, "id": 5, "ja": 6}
    
    if lang1 not in lang_map or lang2 not in lang_map:
        return {"error": "Invalid language codes"}
    
    idx1, idx2 = lang_map[lang1], lang_map[lang2]
    
    overlap_stats = {
        "language_pair": f"{lang1}-{lang2}",
        "layer_overlaps": []
    }
    
    for layer_idx in range(len(neurons[idx1])):
        neurons1 = set(neurons[idx1][layer_idx].tolist())
        neurons2 = set(neurons[idx2][layer_idx].tolist())
        
        intersection = neurons1 & neurons2
        union = neurons1 | neurons2
        
        overlap_stats["layer_overlaps"].append({
            "layer": layer_idx,
            "overlap_count": len(intersection),
            "jaccard_similarity": len(intersection) / len(union) if union else 0,
            f"{lang1}_unique": len(neurons1 - neurons2),
            f"{lang2}_unique": len(neurons2 - neurons1)
        })
    
    return overlap_stats

def print_analysis(analysis: Dict):
    """Pretty print the analysis results."""
    print(f"\n{'='*60}")
    print(f"Model: {analysis['model']}")
    print(f"Number of Languages: {analysis['num_languages']}")
    print(f"Number of Layers: {analysis['num_layers']}")
    print(f"{'='*60}\n")
    
    for lang, stats in analysis["language_stats"].items():
        print(f"{lang}:")
        print(f"  Total neurons: {stats['total_neurons']}")
        print(f"  Average per layer: {stats['avg_neurons_per_layer']:.2f}")
        print(f"  Max in a layer: {stats['max_neurons_in_layer']}")
        print(f"  Min in a layer: {stats['min_neurons_in_layer']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Load and analyze language-specific neurons")
    parser.add_argument("-m", "--model", type=str, default="llama-7b",
                       choices=list(MODEL_FILES.keys()),
                       help="Model to analyze")
    parser.add_argument("-f", "--file", type=str, default=None,
                       help="Custom path to neuron file (overrides --model)")
    parser.add_argument("--compare", nargs=2, metavar=('LANG1', 'LANG2'),
                       help="Compare neuron overlap between two languages")
    parser.add_argument("--get-neurons", nargs=2, metavar=('LANG', 'LAYER'),
                       help="Get specific neurons for a language and layer")
    
    args = parser.parse_args()
    
    # Determine file path
    if args.file:
        file_path = args.file
        model_name = Path(file_path).stem
    else:
        file_path = MODEL_FILES[args.model]
        model_name = args.model
    
    try:
        # Load neurons
        print(f"Loading neurons from {file_path}...")
        neurons = load_neurons(file_path)
        print(f"Successfully loaded neurons for {len(neurons)} languages")
        
        # Perform analysis
        analysis = analyze_neurons(neurons, model_name)
        print_analysis(analysis)
        
        # Compare languages if requested
        if args.compare:
            lang1, lang2 = args.compare
            overlap = compare_language_overlap(neurons, lang1, lang2)
            if "error" not in overlap:
                print(f"\nOverlap Analysis: {overlap['language_pair']}")
                print("-" * 40)
                for layer_stat in overlap["layer_overlaps"][:5]:  # Show first 5 layers
                    print(f"Layer {layer_stat['layer']}: "
                          f"{layer_stat['overlap_count']} shared neurons, "
                          f"Jaccard: {layer_stat['jaccard_similarity']:.3f}")
        
        # Get specific neurons if requested
        if args.get_neurons:
            lang, layer = args.get_neurons[0], int(args.get_neurons[1])
            specific_neurons = get_specific_neurons(neurons, lang, layer)
            if specific_neurons is not None:
                print(f"\nNeurons for {lang} in layer {layer}:")
                print(f"Count: {len(specific_neurons)}")
                print(f"Indices: {specific_neurons.tolist()[:10]}{'...' if len(specific_neurons) > 10 else ''}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

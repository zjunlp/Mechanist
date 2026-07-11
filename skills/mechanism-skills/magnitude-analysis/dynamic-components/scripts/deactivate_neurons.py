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

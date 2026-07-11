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

#!/usr/bin/env python3
"""
Compute Key-Value Agreement in Transformer Feed-Forward Layers

This script demonstrates the key-value agreement analysis for transformer
feed-forward layers, showing how values correspond to their associated keys.

Requirements:
- ff-layers installed
- Pre-extracted trigger examples (textual format)
- ~150GB RAM for full analysis
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Add ff-layers to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_memory_requirements():
    """
    Check if system has sufficient memory for analysis.
    """
    import psutil
    
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    available_gb = mem.available / (1024 ** 3)
    
    print(f"System Memory Status:")
    print(f"  Total: {total_gb:.1f} GB")
    print(f"  Available: {available_gb:.1f} GB")
    
    if total_gb < 150:
        print("WARNING: Full key-value agreement analysis requires ~150GB RAM")
        print("Consider using a subset of data or a machine with more memory")
        return False
    
    return True

def compute_agreement(
    model_dir: str,
    data_dir: str,
    output_base: str
) -> None:
    """
    Compute agreement between keys and values.
    
    Args:
        model_dir: Path to model checkpoint directory
        data_dir: Directory with trigger examples (textual format)
        output_base: Base name for output files (will create .tsv and .json)
    """
    
    cmd_parts = [
        'python', 'analysis/key_value_agreement.py',
        '--model_dir', model_dir,
        '--data_dir', data_dir,
        '--output_base', output_base
    ]
    
    import subprocess
    print(f"Computing key-value agreement...")
    print(f"This may take significant time and memory...")
    
    try:
        result = subprocess.run(
            cmd_parts,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Agreement computation completed!")
        print(f"Output files: {output_base}.tsv and {output_base}.json")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during computation: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        raise

def analyze_agreement_results(tsv_file: str) -> Dict:
    """
    Analyze key-value agreement results from TSV file.
    
    Args:
        tsv_file: Path to TSV file with agreement results
    
    Returns:
        Dictionary with analysis statistics
    """
    
    try:
        # Load TSV file
        df = pd.read_csv(tsv_file, sep='\t')
        
        stats = {
            'total_keys': len(df),
            'mean_agreement': df['agreement'].mean() if 'agreement' in df.columns else 0,
            'std_agreement': df['agreement'].std() if 'agreement' in df.columns else 0,
            'layers': df['layer'].unique().tolist() if 'layer' in df.columns else [],
        }
        
        # Find keys with highest agreement
        if 'agreement' in df.columns:
            top_keys = df.nlargest(10, 'agreement')[['layer', 'dimension', 'agreement']]
            stats['top_agreement_keys'] = top_keys.to_dict('records')
        
        return stats
        
    except FileNotFoundError:
        print(f"File not found: {tsv_file}")
        return {}
    except Exception as e:
        print(f"Error analyzing results: {e}")
        return {}

def create_subset_data(
    input_dir: str,
    output_dir: str,
    max_keys: int = 100
) -> str:
    """
    Create a subset of trigger example data for testing.
    
    Args:
        input_dir: Directory with full trigger examples
        output_dir: Directory for subset output
        max_keys: Maximum number of keys to include
    
    Returns:
        Path to subset directory
    """
    
    import shutil
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get list of files
    input_path = Path(input_dir)
    files = list(input_path.glob('*.txt'))[:max_keys]
    
    print(f"Creating subset with {len(files)} keys...")
    
    for file in files:
        dest = Path(output_dir) / file.name
        shutil.copy2(file, dest)
    
    print(f"Subset created in: {output_dir}")
    return output_dir

def visualize_agreement(json_file: str, output_plot: str = None):
    """
    Create visualization of key-value agreement patterns.
    
    Args:
        json_file: Path to JSON file with agreement data
        output_plot: Path to save plot (optional)
    """
    
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract agreement scores per layer
        layer_agreements = {}
        for key, value in data.items():
            if isinstance(value, dict) and 'layer' in value:
                layer = value['layer']
                agreement = value.get('agreement', 0)
                
                if layer not in layer_agreements:
                    layer_agreements[layer] = []
                layer_agreements[layer].append(agreement)
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        layers = sorted(layer_agreements.keys())
        agreements = [layer_agreements[l] for l in layers]
        
        # Box plot
        bp = ax.boxplot(agreements, labels=layers)
        ax.set_xlabel('Layer')
        ax.set_ylabel('Agreement Score')
        ax.set_title('Key-Value Agreement Across Layers')
        ax.grid(True, alpha=0.3)
        
        if output_plot:
            plt.savefig(output_plot, dpi=150, bbox_inches='tight')
            print(f"Plot saved to: {output_plot}")
        else:
            plt.show()
            
    except ImportError:
        print("Matplotlib not installed. Skipping visualization.")
    except Exception as e:
        print(f"Error creating visualization: {e}")

def main():
    """
    Main function for key-value agreement analysis.
    """
    
    parser = argparse.ArgumentParser(
        description='Compute key-value agreement in transformer FF layers'
    )
    parser.add_argument(
        '--model-dir',
        type=str,
        default='checkpoints/adaptive_lm_wiki103.v2/',
        help='Path to model checkpoint directory'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        help='Directory with trigger examples (textual format)'
    )
    parser.add_argument(
        '--output-base',
        type=str,
        default='key_value_agreement',
        help='Base name for output files'
    )
    parser.add_argument(
        '--analyze-only',
        type=str,
        help='Only analyze existing TSV file'
    )
    parser.add_argument(
        '--subset',
        type=int,
        help='Create and use subset with N keys (for testing)'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Create visualization of results'
    )
    
    args = parser.parse_args()
    
    if args.analyze_only:
        # Analyze existing results
        stats = analyze_agreement_results(args.analyze_only)
        print("\n=== Key-Value Agreement Analysis ===")
        print(f"Total keys: {stats.get('total_keys', 0)}")
        print(f"Mean agreement: {stats.get('mean_agreement', 0):.4f}")
        print(f"Std agreement: {stats.get('std_agreement', 0):.4f}")
        print(f"Number of layers: {len(stats.get('layers', []))}")
        
        if 'top_agreement_keys' in stats:
            print("\nTop 10 Keys by Agreement:")
            for key in stats['top_agreement_keys']:
                print(f"  Layer {key['layer']}, Dim {key['dimension']}: {key['agreement']:.4f}")
        
        if args.visualize:
            json_file = args.analyze_only.replace('.tsv', '.json')
            if os.path.exists(json_file):
                visualize_agreement(json_file, 'agreement_plot.png')
    
    else:
        # Check memory requirements
        if not check_memory_requirements():
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                return
        
        # Handle subset creation if requested
        data_dir = args.data_dir
        if args.subset and data_dir:
            subset_dir = f"{data_dir}_subset_{args.subset}"
            data_dir = create_subset_data(data_dir, subset_dir, args.subset)
        
        if not data_dir:
            print("Error: --data-dir is required")
            return
        
        # Compute agreement
        compute_agreement(
            model_dir=args.model_dir,
            data_dir=data_dir,
            output_base=args.output_base
        )
        
        # Analyze results
        tsv_file = f"{args.output_base}.tsv"
        if os.path.exists(tsv_file):
            stats = analyze_agreement_results(tsv_file)
            print("\n=== Results Summary ===")
            print(f"Mean agreement: {stats.get('mean_agreement', 0):.4f}")
            
            if args.visualize:
                json_file = f"{args.output_base}.json"
                if os.path.exists(json_file):
                    visualize_agreement(json_file, f"{args.output_base}_plot.png")

if __name__ == "__main__":
    main()

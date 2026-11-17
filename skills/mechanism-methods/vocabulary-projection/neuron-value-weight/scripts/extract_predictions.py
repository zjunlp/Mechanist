#!/usr/bin/env python3
"""
Extract Layer and Value Predictions from Transformer Feed-Forward Layers

This script demonstrates extraction of predictions at both dimension and
layer levels from transformer models, useful for analyzing the memory-like
behavior of feed-forward layers.

Requirements:
- ff-layers installed
- Model checkpoint and preprocessed data
"""

import argparse
import pickle
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Add ff-layers to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_ffn_predictions(
    data_file: str,
    model_dir: str,
    output_file: str,
    extract_mode: str = 'layer',
    max_sentences: int = 1000
) -> None:
    """
    Extract FFN predictions from transformer model.
    
    Args:
        data_file: Path to tokenized data file
        model_dir: Path to model checkpoint directory
        output_file: Path for output pickle file
        extract_mode: 'dim' for dimension-level, 'layer' for layer-level
        max_sentences: Number of sentences to process (-1 for all)
    """
    
    cmd_parts = [
        'python', 'analysis/generate_outputs.py',
        '--data_file', data_file,
        '--model_dir', model_dir,
        '--extract_ffn_info',
        '--max_sentences', str(max_sentences),
        '--extract_mode', extract_mode,
        '--output_file', output_file
    ]
    
    import subprocess
    print(f"Extracting {extract_mode}-level predictions...")
    print(f"Processing {max_sentences if max_sentences > 0 else 'all'} sentences")
    
    # Estimate running time
    if extract_mode == 'dim' and max_sentences > 0:
        estimated_hours = (max_sentences / 1000) * 4.2
        print(f"Estimated time: ~{estimated_hours:.1f} hours")
    elif extract_mode == 'layer' and max_sentences == -1:
        print(f"Estimated time: ~9.8 hours for full validation set")
    
    try:
        result = subprocess.run(
            cmd_parts,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Extraction completed!")
        print(f"Output saved to: {output_file}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during extraction: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        raise

def analyze_predictions(pickle_file: str) -> Dict:
    """
    Analyze extracted predictions from pickle file.
    
    Args:
        pickle_file: Path to pickle file with predictions
    
    Returns:
        Dictionary with analysis statistics
    """
    
    try:
        # Load pickle file
        with open(pickle_file, 'rb') as f:
            df = pickle.load(f)
        
        print(f"Loaded DataFrame with shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        stats = {
            'num_samples': len(df),
            'columns': df.columns.tolist(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024)
        }
        
        # Analyze predictions if available
        if 'predictions' in df.columns:
            # Get unique predictions
            all_preds = []
            for pred_list in df['predictions']:
                if isinstance(pred_list, list):
                    all_preds.extend(pred_list)
            
            unique_preds = len(set(all_preds))
            stats['unique_predictions'] = unique_preds
        
        # Analyze by layer if available
        if 'layer' in df.columns:
            layer_counts = df['layer'].value_counts().to_dict()
            stats['samples_per_layer'] = layer_counts
            stats['num_layers'] = len(layer_counts)
        
        # Analyze activations if available
        if 'activations' in df.columns:
            activation_shapes = []
            for act in df['activations'].dropna()[:5]:  # Sample first 5
                if isinstance(act, np.ndarray):
                    activation_shapes.append(act.shape)
            stats['sample_activation_shapes'] = activation_shapes
        
        return stats
        
    except FileNotFoundError:
        print(f"File not found: {pickle_file}")
        return {}
    except Exception as e:
        print(f"Error analyzing predictions: {e}")
        return {}

def export_predictions_to_csv(
    pickle_file: str,
    output_csv: str,
    max_rows: Optional[int] = None
) -> None:
    """
    Export predictions from pickle to CSV for easier analysis.
    
    Args:
        pickle_file: Path to pickle file
        output_csv: Path for output CSV file
        max_rows: Maximum rows to export (None for all)
    """
    
    try:
        with open(pickle_file, 'rb') as f:
            df = pickle.load(f)
        
        # Limit rows if specified
        if max_rows:
            df = df.head(max_rows)
        
        # Convert complex columns to strings for CSV
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column contains lists/arrays
                first_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if isinstance(first_val, (list, np.ndarray)):
                    df[col] = df[col].apply(lambda x: str(x) if x is not None else '')
        
        # Export to CSV
        df.to_csv(output_csv, index=False)
        print(f"Exported {len(df)} rows to: {output_csv}")
        
    except Exception as e:
        print(f"Error exporting to CSV: {e}")

def compare_extraction_modes(
    dim_pickle: str,
    layer_pickle: str
) -> None:
    """
    Compare results from dimension-level and layer-level extractions.
    
    Args:
        dim_pickle: Path to dimension-level pickle file
        layer_pickle: Path to layer-level pickle file
    """
    
    try:
        # Load both files
        with open(dim_pickle, 'rb') as f:
            df_dim = pickle.load(f)
        with open(layer_pickle, 'rb') as f:
            df_layer = pickle.load(f)
        
        print("\n=== Extraction Mode Comparison ===")
        print(f"\nDimension-level extraction:")
        print(f"  Shape: {df_dim.shape}")
        print(f"  Memory: {df_dim.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
        
        print(f"\nLayer-level extraction:")
        print(f"  Shape: {df_layer.shape}")
        print(f"  Memory: {df_layer.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
        
        # Compare information density
        if 'layer' in df_dim.columns and 'layer' in df_layer.columns:
            dim_layers = df_dim['layer'].nunique()
            layer_layers = df_layer['layer'].nunique()
            print(f"\nUnique layers:")
            print(f"  Dimension-level: {dim_layers}")
            print(f"  Layer-level: {layer_layers}")
        
    except Exception as e:
        print(f"Error comparing modes: {e}")

def create_sample_analysis(
    data_file: str,
    model_dir: str,
    output_dir: str,
    num_sentences: int = 100
) -> Tuple[str, str]:
    """
    Create sample analysis with both extraction modes.
    
    Args:
        data_file: Path to data file
        model_dir: Path to model directory
        output_dir: Output directory for results
        num_sentences: Number of sentences to analyze
    
    Returns:
        Tuple of (dim_pickle_path, layer_pickle_path)
    """
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract dimension-level predictions
    dim_output = os.path.join(output_dir, f'dim_{num_sentences}sent.pkl')
    extract_ffn_predictions(
        data_file=data_file,
        model_dir=model_dir,
        output_file=dim_output,
        extract_mode='dim',
        max_sentences=num_sentences
    )
    
    # Extract layer-level predictions
    layer_output = os.path.join(output_dir, f'layer_{num_sentences}sent.pkl')
    extract_ffn_predictions(
        data_file=data_file,
        model_dir=model_dir,
        output_file=layer_output,
        extract_mode='layer',
        max_sentences=num_sentences
    )
    
    return dim_output, layer_output

def main():
    """
    Main function for prediction extraction and analysis.
    """
    
    parser = argparse.ArgumentParser(
        description='Extract predictions from transformer FF layers'
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='examples/language_model/wikitext-103/wiki.valid.tokens',
        help='Path to tokenized data file'
    )
    parser.add_argument(
        '--model-dir',
        type=str,
        default='checkpoints/adaptive_lm_wiki103.v2/',
        help='Path to model checkpoint directory'
    )
    parser.add_argument(
        '--extract-mode',
        type=str,
        choices=['dim', 'layer'],
        default='layer',
        help='Extraction mode: dim (detailed) or layer (aggregated)'
    )
    parser.add_argument(
        '--max-sentences',
        type=int,
        default=100,
        help='Maximum sentences to process (-1 for all)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output pickle file path'
    )
    parser.add_argument(
        '--analyze',
        type=str,
        help='Analyze existing pickle file'
    )
    parser.add_argument(
        '--export-csv',
        type=str,
        help='Export pickle to CSV'
    )
    parser.add_argument(
        '--compare',
        nargs=2,
        metavar=('DIM_PKL', 'LAYER_PKL'),
        help='Compare dim and layer extraction results'
    )
    parser.add_argument(
        '--sample-analysis',
        action='store_true',
        help='Run sample analysis with both modes'
    )
    
    args = parser.parse_args()
    
    if args.analyze:
        # Analyze existing file
        stats = analyze_predictions(args.analyze)
        print("\n=== Prediction Analysis ===")
        print(f"Samples: {stats.get('num_samples', 0)}")
        print(f"Memory usage: {stats.get('memory_usage_mb', 0):.1f} MB")
        print(f"Unique predictions: {stats.get('unique_predictions', 'N/A')}")
        print(f"Number of layers: {stats.get('num_layers', 'N/A')}")
        
        if 'sample_activation_shapes' in stats:
            print(f"Sample activation shapes: {stats['sample_activation_shapes']}")
        
        if args.export_csv:
            export_predictions_to_csv(args.analyze, args.export_csv, max_rows=1000)
    
    elif args.compare:
        # Compare two extraction modes
        compare_extraction_modes(args.compare[0], args.compare[1])
    
    elif args.sample_analysis:
        # Run sample analysis
        print("=== Running Sample Analysis ===")
        output_dir = 'sample_predictions'
        
        dim_pkl, layer_pkl = create_sample_analysis(
            data_file=args.data_file,
            model_dir=args.model_dir,
            output_dir=output_dir,
            num_sentences=50
        )
        
        # Analyze both
        print("\n--- Dimension-level Results ---")
        dim_stats = analyze_predictions(dim_pkl)
        print(f"Unique predictions: {dim_stats.get('unique_predictions', 'N/A')}")
        
        print("\n--- Layer-level Results ---")
        layer_stats = analyze_predictions(layer_pkl)
        print(f"Samples per layer: {layer_stats.get('samples_per_layer', {})}")
        
        # Compare
        compare_extraction_modes(dim_pkl, layer_pkl)
    
    else:
        # Extract predictions
        if not args.output_file:
            args.output_file = f"{args.extract_mode}_{args.max_sentences}sent.pkl"
        
        extract_ffn_predictions(
            data_file=args.data_file,
            model_dir=args.model_dir,
            output_file=args.output_file,
            extract_mode=args.extract_mode,
            max_sentences=args.max_sentences
        )
        
        # Quick analysis
        if os.path.exists(args.output_file):
            stats = analyze_predictions(args.output_file)
            print(f"\nExtracted {stats.get('num_samples', 0)} samples")

if __name__ == "__main__":
    main()

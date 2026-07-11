---
name: neuron-value-weight
description: Analyze transformer feed-forward layers as key-value memories, extract activations, identify trigger examples, and compute key-value agreement in transformer language models
---

## Demo Scripts

### `scripts/compute_key_value_agreement.py`

```python
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
```

### `scripts/extract_predictions.py`

```python
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
```

### `scripts/extract_trigger_examples.py`

```python
#!/usr/bin/env python3
"""
Extract Trigger Examples from Transformer Feed-Forward Layers

This script demonstrates how to use the ff-layers library to identify
trigger examples for keys in transformer neural networks.

Requirements:
- ff-layers installed (pip install --editable .)
- Downloaded model: transformer_lm.wiki103.adaptive
- Preprocessed WikiText-103 data
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add ff-layers to path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_paths():
    """
    Set up default paths for model and data.
    Modify these paths based on your installation.
    """
    paths = {
        'model_dir': 'checkpoints/adaptive_lm_wiki103.v2/',
        'data_file': 'examples/language_model/wikitext-103/wiki.train.tokens',
        'output_dir': 'analysis_output/'
    }
    
    # Create output directory if it doesn't exist
    Path(paths['output_dir']).mkdir(parents=True, exist_ok=True)
    
    return paths

def extract_trigger_examples(
    data_file: str,
    model_dir: str,
    output_file: str,
    max_sentences: int = 1000,
    top_k: int = 50,
    dims: Optional[List[int]] = None,
    extract_mode: str = 'layer-raw'
) -> None:
    """
    Extract trigger examples for transformer keys.
    
    Args:
        data_file: Path to tokenized data file
        model_dir: Path to model checkpoint directory
        output_file: Path for output JSONL file
        max_sentences: Number of sentences to process (-1 for all)
        top_k: Number of top trigger examples per key
        dims: Specific dimensions to analyze (None for all)
        extract_mode: Extraction mode ('layer-raw', 'dim', 'layer')
    """
    
    # Build command
    cmd_parts = [
        'python', 'analysis/generate_outputs.py',
        '--data_file', data_file,
        '--model_dir', model_dir,
        '--get_trigger_examples',
        '--max_sentences', str(max_sentences),
        '--top_k_trigger_examples', str(top_k),
        '--extract_mode', extract_mode,
        '--output_file', output_file
    ]
    
    # Add specific dimensions if provided
    if dims:
        cmd_parts.extend(['--dims_for_analysis'] + [str(d) for d in dims])
    
    # Execute command
    import subprocess
    print(f"Executing: {' '.join(cmd_parts)}")
    
    try:
        result = subprocess.run(
            cmd_parts,
            check=True,
            capture_output=True,
            text=True
        )
        print("Extraction completed successfully!")
        print(f"Output saved to: {output_file}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during extraction: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        raise

def convert_to_textual(
    input_jsonl: str,
    model_dir: str,
    output_dir: str
) -> None:
    """
    Convert JSONL output to readable text files.
    
    Args:
        input_jsonl: Path to input JSONL file
        model_dir: Path to model checkpoint directory
        output_dir: Directory for text output files
    """
    
    cmd_parts = [
        'python', 'analysis/trigger_examples_jsonl_to_textual.py',
        '--input_file', input_jsonl,
        '--model_dir', model_dir,
        '--output_dir', output_dir
    ]
    
    import subprocess
    print(f"Converting to textual format...")
    
    try:
        result = subprocess.run(
            cmd_parts,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Conversion completed! Output in: {output_dir}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        raise

def analyze_trigger_examples(jsonl_file: str) -> Dict[str, Any]:
    """
    Analyze extracted trigger examples from JSONL file.
    
    Args:
        jsonl_file: Path to JSONL file with trigger examples
    
    Returns:
        Dictionary with analysis statistics
    """
    
    stats = {
        'total_keys': 0,
        'layers': set(),
        'dimensions': set(),
        'examples_per_key': []
    }
    
    try:
        with open(jsonl_file, 'r') as f:
            for line in f:
                data = json.loads(line)
                stats['total_keys'] += 1
                
                # Extract layer and dimension info
                if 'layer' in data:
                    stats['layers'].add(data['layer'])
                if 'dimension' in data:
                    stats['dimensions'].add(data['dimension'])
                if 'examples' in data:
                    stats['examples_per_key'].append(len(data['examples']))
        
        # Convert sets to lists for JSON serialization
        stats['layers'] = sorted(list(stats['layers']))
        stats['dimensions'] = sorted(list(stats['dimensions']))
        
        # Calculate average examples per key
        if stats['examples_per_key']:
            stats['avg_examples'] = sum(stats['examples_per_key']) / len(stats['examples_per_key'])
        
        return stats
        
    except FileNotFoundError:
        print(f"File not found: {jsonl_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return {}

def main():
    """
    Main function to demonstrate trigger example extraction.
    """
    
    parser = argparse.ArgumentParser(
        description='Extract trigger examples from transformer FF layers'
    )
    parser.add_argument(
        '--quick-demo',
        action='store_true',
        help='Run a quick demonstration with small dataset'
    )
    parser.add_argument(
        '--analyze-only',
        type=str,
        help='Only analyze existing JSONL file'
    )
    
    args = parser.parse_args()
    
    # Setup paths
    paths = setup_paths()
    
    if args.analyze_only:
        # Analyze existing file
        stats = analyze_trigger_examples(args.analyze_only)
        print("\n=== Trigger Examples Analysis ===")
        print(f"Total keys analyzed: {stats.get('total_keys', 0)}")
        print(f"Layers: {stats.get('layers', [])}")
        print(f"Number of unique dimensions: {len(stats.get('dimensions', []))}")
        print(f"Average examples per key: {stats.get('avg_examples', 0):.2f}")
        
    elif args.quick_demo:
        # Run quick demonstration
        print("=== Running Quick Demonstration ===")
        print("Extracting trigger examples for first 100 sentences...")
        
        demo_output = os.path.join(paths['output_dir'], 'demo_triggers.jsonl')
        demo_text_dir = os.path.join(paths['output_dir'], 'demo_triggers_text')
        
        # Extract trigger examples
        extract_trigger_examples(
            data_file=paths['data_file'],
            model_dir=paths['model_dir'],
            output_file=demo_output,
            max_sentences=100,
            top_k=10,
            dims=[222, 1001],  # Analyze specific dimensions as example
            extract_mode='layer-raw'
        )
        
        # Convert to textual format
        convert_to_textual(
            input_jsonl=demo_output,
            model_dir=paths['model_dir'],
            output_dir=demo_text_dir
        )
        
        # Analyze results
        stats = analyze_trigger_examples(demo_output)
        print("\n=== Analysis Results ===")
        print(f"Extracted triggers for {stats.get('total_keys', 0)} keys")
        
    else:
        print("Use --quick-demo for a demonstration or --analyze-only <file> to analyze existing results")
        print("\nExample commands:")
        print("  python extract_trigger_examples.py --quick-demo")
        print("  python extract_trigger_examples.py --analyze-only output.jsonl")

if __name__ == "__main__":
    main()
```

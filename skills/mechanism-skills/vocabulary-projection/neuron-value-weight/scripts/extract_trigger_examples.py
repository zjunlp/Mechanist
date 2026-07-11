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

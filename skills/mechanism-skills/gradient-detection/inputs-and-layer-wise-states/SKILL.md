---
name: inputs-and-layer-wise-states
description: Analyze and visualize layer-wise gradient behaviors in LLMs during fine-tuning for fast vs slow thinking tasks, calculate gradient statistics, and understand training patterns across different model layers
---

## Demo Scripts

### `scripts/calculate_gradients.py`

```python
#!/usr/bin/env python3
"""
Calculate Layer-wise Gradient Statistics for LLM Fine-tuning

This script demonstrates how to calculate gradient statistics for each layer
when fine-tuning LLMs on different types of responses (fast vs slow thinking).
"""

import json
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
import argparse
from pathlib import Path


def load_training_data(data_path: str) -> List[Dict]:
    """
    Load training data from JSON file.
    
    Args:
        data_path: Path to the JSON data file
        
    Returns:
        List of training examples
    """
    with open(data_path, 'r') as f:
        data = json.load(f)
    return data


def prepare_model_and_tokenizer(
    model_name_or_path: str,
    device: str = "cuda"
) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    Load and prepare model and tokenizer for gradient calculation.
    
    Args:
        model_name_or_path: Hugging Face model identifier or local path
        device: Device to load model on
        
    Returns:
        Tuple of (model, tokenizer)
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
    
    # Add padding token if not present
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    model.eval()
    return model, tokenizer


def calculate_layer_gradients(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    text: str,
    max_length: int = 1024
) -> Dict[str, float]:
    """
    Calculate gradient norms for each layer of the model.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        text: Input text for gradient calculation
        max_length: Maximum sequence length
        
    Returns:
        Dictionary mapping layer names to gradient norms
    """
    # Tokenize input
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
        padding=True
    ).to(model.device)
    
    # Enable gradient calculation
    model.zero_grad()
    
    # Forward pass with gradient calculation
    with torch.enable_grad():
        outputs = model(**inputs, labels=inputs["input_ids"])
        loss = outputs.loss
        
        # Backward pass
        loss.backward()
    
    # Collect gradient norms for each layer
    gradient_norms = {}
    
    for name, param in model.named_parameters():
        if param.grad is not None:
            # Calculate L2 norm of gradients
            grad_norm = torch.norm(param.grad, p=2).item()
            gradient_norms[name] = grad_norm
    
    return gradient_norms


def calculate_svd_vectors(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    text: str,
    num_components: int = 10
) -> Dict[str, np.ndarray]:
    """
    Calculate SVD vectors for gradient analysis.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        text: Input text
        num_components: Number of SVD components to compute
        
    Returns:
        Dictionary mapping layer names to SVD components
    """
    # Get gradients
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(model.device)
    
    model.zero_grad()
    with torch.enable_grad():
        outputs = model(**inputs, labels=inputs["input_ids"])
        outputs.loss.backward()
    
    svd_results = {}
    
    for name, param in model.named_parameters():
        if param.grad is not None and len(param.grad.shape) >= 2:
            # Flatten gradient tensor for SVD
            grad_flat = param.grad.view(param.grad.shape[0], -1).cpu().numpy()
            
            # Compute SVD
            try:
                U, S, Vt = np.linalg.svd(grad_flat, full_matrices=False)
                # Store top components
                svd_results[name] = {
                    'singular_values': S[:num_components].tolist(),
                    'top_component_variance': (S[0]**2 / np.sum(S**2)).item()
                }
            except:
                svd_results[name] = None
                
    return svd_results


def analyze_gradient_patterns(
    gradient_norms: Dict[str, float],
    layer_groups: Optional[Dict[str, List[str]]] = None
) -> Dict[str, float]:
    """
    Analyze gradient patterns across layers.
    
    Args:
        gradient_norms: Dictionary of layer gradient norms
        layer_groups: Optional grouping of layers (e.g., early, middle, late)
        
    Returns:
        Dictionary of gradient statistics
    """
    norms = list(gradient_norms.values())
    
    stats = {
        'mean_norm': np.mean(norms),
        'std_norm': np.std(norms),
        'max_norm': np.max(norms),
        'min_norm': np.min(norms),
        'coefficient_of_variation': np.std(norms) / np.mean(norms) if np.mean(norms) > 0 else 0
    }
    
    # Calculate layer-wise differences
    if len(norms) > 1:
        differences = [abs(norms[i+1] - norms[i]) for i in range(len(norms)-1)]
        stats['mean_layer_difference'] = np.mean(differences)
        stats['max_layer_difference'] = np.max(differences)
    
    # Analyze by layer groups if provided
    if layer_groups:
        for group_name, layer_names in layer_groups.items():
            group_norms = [gradient_norms[name] for name in layer_names if name in gradient_norms]
            if group_norms:
                stats[f'{group_name}_mean'] = np.mean(group_norms)
                stats[f'{group_name}_std'] = np.std(group_norms)
    
    return stats


def process_dataset(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    data: List[Dict],
    output_path: str,
    max_samples: int = None
):
    """
    Process entire dataset and save gradient statistics.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        data: List of training examples
        output_path: Path to save results
        max_samples: Maximum number of samples to process
    """
    results = []
    
    if max_samples:
        data = data[:max_samples]
    
    for idx, example in enumerate(data):
        print(f"Processing example {idx+1}/{len(data)}")
        
        # Prepare text (combine instruction and response)
        if 'instruction' in example and 'response' in example:
            text = f"{example['instruction']}\n{example['response']}"
        elif 'text' in example:
            text = example['text']
        else:
            continue
        
        # Calculate gradients
        gradient_norms = calculate_layer_gradients(model, tokenizer, text)
        
        # Calculate statistics
        stats = analyze_gradient_patterns(gradient_norms)
        
        # Store results
        result = {
            'example_id': idx,
            'gradient_norms': gradient_norms,
            'statistics': stats
        }
        
        results.append(result)
        
        # Save incrementally
        if (idx + 1) % 10 == 0:
            with open(output_path, 'w') as f:
                for res in results:
                    f.write(json.dumps(res) + '\n')
    
    # Final save
    with open(output_path, 'w') as f:
        for res in results:
            f.write(json.dumps(res) + '\n')
    
    print(f"Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Calculate layer-wise gradient statistics")
    parser.add_argument("--data_path", type=str, required=True, help="Path to training data")
    parser.add_argument("--model_name_or_path", type=str, required=True, help="Model identifier")
    parser.add_argument("--output_path", type=str, required=True, help="Output path for results")
    parser.add_argument("--max_samples", type=int, default=None, help="Maximum samples to process")
    parser.add_argument("--max_length", type=int, default=1024, help="Maximum sequence length")
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.data_path}")
    data = load_training_data(args.data_path)
    
    # Load model and tokenizer
    print(f"Loading model: {args.model_name_or_path}")
    model, tokenizer = prepare_model_and_tokenizer(args.model_name_or_path)
    
    # Process dataset
    process_dataset(
        model=model,
        tokenizer=tokenizer,
        data=data,
        output_path=args.output_path,
        max_samples=args.max_samples
    )


if __name__ == "__main__":
    main()
```

### `scripts/visualize_gradients.py`

```python
#!/usr/bin/env python3
"""
Visualize Layer-wise Gradient Statistics

This script provides visualization capabilities for gradient statistics
calculated during LLM fine-tuning, comparing fast vs slow thinking patterns.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple
import seaborn as sns
from pathlib import Path
import pandas as pd


def load_gradient_results(jsonl_path: str) -> List[Dict]:
    """
    Load gradient results from JSONL file.
    
    Args:
        jsonl_path: Path to JSONL file containing gradient statistics
        
    Returns:
        List of gradient result dictionaries
    """
    results = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            results.append(json.loads(line.strip()))
    return results


def extract_layer_gradients(results: List[Dict]) -> pd.DataFrame:
    """
    Extract and organize layer gradients into a DataFrame.
    
    Args:
        results: List of gradient results
        
    Returns:
        DataFrame with layer gradients
    """
    data = []
    
    for result in results:
        gradient_norms = result.get('gradient_norms', {})
        for layer_name, norm in gradient_norms.items():
            # Extract layer number from name
            layer_num = extract_layer_number(layer_name)
            data.append({
                'example_id': result.get('example_id', 0),
                'layer_name': layer_name,
                'layer_num': layer_num,
                'gradient_norm': norm
            })
    
    return pd.DataFrame(data)


def extract_layer_number(layer_name: str) -> int:
    """
    Extract layer number from layer name.
    
    Args:
        layer_name: Name of the layer
        
    Returns:
        Layer number (0 if not found)
    """
    import re
    match = re.search(r'layers\.(\d+)', layer_name)
    if match:
        return int(match.group(1))
    return 0


def calculate_mad_statistics(values: List[float], num_sections: int = 3) -> Dict[str, float]:
    """
    Calculate Mean Absolute Difference (MAD) statistics in sections.
    
    Args:
        values: List of gradient values
        num_sections: Number of sections to divide the data
        
    Returns:
        Dictionary with MAD statistics for each section
    """
    mad_stats = {}
    section_size = len(values) // num_sections
    
    for i in range(num_sections):
        start = i * section_size
        end = (i + 1) * section_size if i < num_sections - 1 else len(values)
        section = values[start:end]
        
        if len(section) > 1:
            # Calculate MAD
            mean = np.mean(section)
            mad = np.mean([abs(x - mean) for x in section])
            mad_stats[f'section_{i+1}_mad'] = mad
            mad_stats[f'section_{i+1}_mean'] = mean
    
    return mad_stats


def plot_layer_gradient_comparison(
    df_fast: pd.DataFrame,
    df_slow: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot comparison of gradient norms between fast and slow thinking.
    
    Args:
        df_fast: DataFrame with fast thinking gradients
        df_slow: DataFrame with slow thinking gradients
        save_path: Optional path to save the figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Average gradient norms by layer
    ax = axes[0]
    
    # Group by layer and calculate mean
    fast_mean = df_fast.groupby('layer_num')['gradient_norm'].mean()
    slow_mean = df_slow.groupby('layer_num')['gradient_norm'].mean()
    
    ax.plot(fast_mean.index, fast_mean.values, label='Fast Thinking', marker='o', linewidth=2)
    ax.plot(slow_mean.index, slow_mean.values, label='Slow Thinking', marker='s', linewidth=2)
    
    ax.set_xlabel('Layer Number', fontsize=12)
    ax.set_ylabel('Average Gradient Norm', fontsize=12)
    ax.set_title('Layer-wise Gradient Norms: Fast vs Slow Thinking', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Gradient variation across layers
    ax = axes[1]
    
    fast_std = df_fast.groupby('layer_num')['gradient_norm'].std()
    slow_std = df_slow.groupby('layer_num')['gradient_norm'].std()
    
    ax.bar(fast_std.index - 0.2, fast_std.values, width=0.4, label='Fast Thinking', alpha=0.7)
    ax.bar(slow_std.index + 0.2, slow_std.values, width=0.4, label='Slow Thinking', alpha=0.7)
    
    ax.set_xlabel('Layer Number', fontsize=12)
    ax.set_ylabel('Gradient Norm Std Dev', fontsize=12)
    ax.set_title('Gradient Variation Across Layers', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()


def plot_gradient_heatmap(
    df: pd.DataFrame,
    title: str = "Gradient Norms Heatmap",
    save_path: Optional[str] = None
):
    """
    Create a heatmap of gradient norms across examples and layers.
    
    Args:
        df: DataFrame with gradient data
        title: Title for the heatmap
        save_path: Optional path to save the figure
    """
    # Pivot data for heatmap
    pivot_data = df.pivot_table(
        index='example_id',
        columns='layer_num',
        values='gradient_norm',
        aggfunc='mean'
    )
    
    plt.figure(figsize=(20, 10))
    
    # Create heatmap
    sns.heatmap(
        pivot_data,
        cmap='viridis',
        cbar_kws={'label': 'Gradient Norm'},
        xticklabels=5,
        yticklabels=20
    )
    
    plt.xlabel('Layer Number', fontsize=12)
    plt.ylabel('Example ID', fontsize=12)
    plt.title(title, fontsize=14)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Heatmap saved to {save_path}")
    
    plt.show()


def calculate_relative_differences(
    values1: List[float],
    values2: List[float]
) -> List[float]:
    """
    Calculate relative differences between two lists of values.
    
    Args:
        values1: First list of values
        values2: Second list of values
        
    Returns:
        List of relative differences
    """
    differences = []
    for v1, v2 in zip(values1, values2):
        if v2 != 0:
            diff = abs(v1 - v2) / abs(v2)
        else:
            diff = abs(v1) if v1 != 0 else 0
        differences.append(diff)
    
    return differences


def generate_comparison_table(
    fast_results: List[Dict],
    slow_results: List[Dict]
) -> pd.DataFrame:
    """
    Generate a comparison table of gradient statistics.
    
    Args:
        fast_results: Results from fast thinking
        slow_results: Results from slow thinking
        
    Returns:
        DataFrame with comparison statistics
    """
    fast_stats = aggregate_statistics(fast_results)
    slow_stats = aggregate_statistics(slow_results)
    
    comparison = {
        'Metric': [],
        'Fast Thinking': [],
        'Slow Thinking': [],
        'Relative Difference': []
    }
    
    for metric in fast_stats.keys():
        comparison['Metric'].append(metric)
        comparison['Fast Thinking'].append(fast_stats[metric])
        comparison['Slow Thinking'].append(slow_stats[metric])
        
        # Calculate relative difference
        if slow_stats[metric] != 0:
            rel_diff = abs(fast_stats[metric] - slow_stats[metric]) / abs(slow_stats[metric])
        else:
            rel_diff = 0
        comparison['Relative Difference'].append(rel_diff)
    
    return pd.DataFrame(comparison)


def aggregate_statistics(results: List[Dict]) -> Dict[str, float]:
    """
    Aggregate statistics across all examples.
    
    Args:
        results: List of gradient results
        
    Returns:
        Dictionary of aggregated statistics
    """
    all_stats = {}
    
    for result in results:
        stats = result.get('statistics', {})
        for key, value in stats.items():
            if key not in all_stats:
                all_stats[key] = []
            all_stats[key].append(value)
    
    # Calculate means
    aggregated = {}
    for key, values in all_stats.items():
        aggregated[key] = np.mean(values)
    
    return aggregated


def visualize_layer_sections(
    df: pd.DataFrame,
    num_sections: int = 3,
    save_path: Optional[str] = None
):
    """
    Visualize gradient statistics in layer sections (early, middle, late).
    
    Args:
        df: DataFrame with gradient data
        num_sections: Number of sections to divide layers
        save_path: Optional path to save figure
    """
    max_layer = df['layer_num'].max()
    section_size = (max_layer + 1) // num_sections
    
    # Assign sections
    df['section'] = df['layer_num'].apply(
        lambda x: min(x // section_size, num_sections - 1)
    )
    
    # Calculate statistics by section
    section_stats = df.groupby('section')['gradient_norm'].agg(['mean', 'std', 'min', 'max'])
    
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Plot 1: Mean gradient by section
    ax = axes[0, 0]
    ax.bar(section_stats.index, section_stats['mean'])
    ax.set_xlabel('Layer Section')
    ax.set_ylabel('Mean Gradient Norm')
    ax.set_title('Mean Gradient Norm by Layer Section')
    ax.set_xticks(range(num_sections))
    ax.set_xticklabels(['Early', 'Middle', 'Late'][:num_sections])
    
    # Plot 2: Std deviation by section
    ax = axes[0, 1]
    ax.bar(section_stats.index, section_stats['std'], color='orange')
    ax.set_xlabel('Layer Section')
    ax.set_ylabel('Std Dev of Gradient Norm')
    ax.set_title('Gradient Variation by Layer Section')
    ax.set_xticks(range(num_sections))
    ax.set_xticklabels(['Early', 'Middle', 'Late'][:num_sections])
    
    # Plot 3: Box plot by section
    ax = axes[1, 0]
    df.boxplot(column='gradient_norm', by='section', ax=ax)
    ax.set_xlabel('Layer Section')
    ax.set_ylabel('Gradient Norm')
    ax.set_title('Gradient Distribution by Layer Section')
    ax.set_xticklabels(['Early', 'Middle', 'Late'][:num_sections])
    plt.sca(ax)
    plt.xticks(range(1, num_sections + 1), ['Early', 'Middle', 'Late'][:num_sections])
    
    # Plot 4: Violin plot
    ax = axes[1, 1]
    positions = sorted(df['section'].unique())
    parts = ax.violinplot(
        [df[df['section'] == s]['gradient_norm'].values for s in positions],
        positions=positions,
        showmeans=True,
        showmedians=True
    )
    ax.set_xlabel('Layer Section')
    ax.set_ylabel('Gradient Norm')
    ax.set_title('Gradient Distribution (Violin Plot)')
    ax.set_xticks(range(num_sections))
    ax.set_xticklabels(['Early', 'Middle', 'Late'][:num_sections])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Section analysis saved to {save_path}")
    
    plt.show()


def main():
    """
    Main function to demonstrate gradient visualization capabilities.
    """
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualize gradient statistics")
    parser.add_argument("--fast_gradients", type=str, required=True,
                       help="Path to fast thinking gradient results")
    parser.add_argument("--slow_gradients", type=str, required=True,
                       help="Path to slow thinking gradient results")
    parser.add_argument("--output_dir", type=str, default="./visualizations",
                       help="Directory to save visualizations")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load results
    print("Loading gradient results...")
    fast_results = load_gradient_results(args.fast_gradients)
    slow_results = load_gradient_results(args.slow_gradients)
    
    # Extract DataFrames
    df_fast = extract_layer_gradients(fast_results)
    df_slow = extract_layer_gradients(slow_results)
    
    # Generate visualizations
    print("Generating comparison plots...")
    plot_layer_gradient_comparison(
        df_fast, df_slow,
        save_path=output_dir / "gradient_comparison.png"
    )
    
    print("Generating heatmaps...")
    plot_gradient_heatmap(
        df_fast,
        title="Fast Thinking Gradient Heatmap",
        save_path=output_dir / "fast_thinking_heatmap.png"
    )
    
    plot_gradient_heatmap(
        df_slow,
        title="Slow Thinking Gradient Heatmap",
        save_path=output_dir / "slow_thinking_heatmap.png"
    )
    
    print("Generating section analysis...")
    visualize_layer_sections(
        df_fast,
        save_path=output_dir / "fast_thinking_sections.png"
    )
    
    visualize_layer_sections(
        df_slow,
        save_path=output_dir / "slow_thinking_sections.png"
    )
    
    # Generate comparison table
    print("Generating comparison table...")
    comparison_table = generate_comparison_table(fast_results, slow_results)
    comparison_table.to_csv(output_dir / "comparison_statistics.csv", index=False)
    print(comparison_table)
    
    print(f"All visualizations saved to {output_dir}")


if __name__ == "__main__":
    main()
```

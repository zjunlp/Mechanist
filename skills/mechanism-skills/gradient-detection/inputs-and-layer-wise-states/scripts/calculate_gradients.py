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

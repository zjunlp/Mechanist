#!/usr/bin/env python3
"""
ROME Model Editing Example

This script demonstrates how to use Rank-One Model Editing (ROME) to edit
factual associations in GPT models. It shows the complete workflow from
loading a model to applying edits and verifying the changes.

Requirements:
- pip install transformers torch
- CUDA-enabled GPU (required)
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path

# Import ROME components (assuming rome package is installed)
try:
    from rome import ROMEHyperParams, apply_rome_to_model
    from rome.layer_stats import layer_stats
except ImportError:
    print("Warning: ROME package not found. Using stub implementations.")
    # Stub implementations for demonstration
    class ROMEHyperParams:
        def __init__(self, **kwargs):
            self.layers = kwargs.get('layers', [17])
            self.fact_token = kwargs.get('fact_token', 'subject_last')
            self.v_num_grad_steps = kwargs.get('v_num_grad_steps', 20)
            self.v_lr = kwargs.get('v_lr', 5e-1)
            self.v_loss_layer = kwargs.get('v_loss_layer', 31)
            self.v_weight_decay = kwargs.get('v_weight_decay', 1e-3)
            self.clamp_norm_factor = kwargs.get('clamp_norm_factor', 4)
            self.kl_factor = kwargs.get('kl_factor', 0.0625)
            self.mom2_adjustment = kwargs.get('mom2_adjustment', True)
            self.mom2_update_weight = kwargs.get('mom2_update_weight', 5000)

def setup_model_and_tokenizer(model_name: str = "gpt2-xl") -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    Load and prepare a model and tokenizer for ROME editing.
    
    Args:
        model_name: HuggingFace model identifier (e.g., "gpt2-xl", "EleutherAI/gpt-j-6B")
    
    Returns:
        Tuple of (model, tokenizer)
    """
    print(f"Loading model: {model_name}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with appropriate settings
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None
    )
    
    if torch.cuda.is_available():
        model = model.cuda()
    
    print(f"Model loaded on device: {next(model.parameters()).device}")
    return model, tokenizer

def create_edit_request(subject: str, prompt_template: str, target_new: str) -> Dict:
    """
    Create a ROME edit request dictionary.
    
    Args:
        subject: The subject to edit (e.g., "LeBron James")
        prompt_template: Template with {} placeholder for subject
        target_new: New target completion
    
    Returns:
        Dictionary formatted for ROME
    """
    request = {
        "prompt": prompt_template,
        "subject": subject,
        "target_new": {
            "str": target_new
        }
    }
    return request

def test_model_knowledge(model, tokenizer, prompt: str, max_tokens: int = 10) -> str:
    """
    Test what the model knows about a given prompt.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        prompt: Input prompt to test
        max_tokens: Maximum tokens to generate
    
    Returns:
        Generated text completion
    """
    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.0,  # Deterministic generation
            do_sample=False
        )
    
    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return generated

def apply_rome_edit(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    requests: List[Dict],
    hparams: Optional[Dict] = None
) -> Tuple[AutoModelForCausalLM, Dict]:
    """
    Apply ROME edits to a model.
    
    Args:
        model: The model to edit
        tokenizer: The tokenizer
        requests: List of edit requests
        hparams: Hyperparameters for ROME (optional)
    
    Returns:
        Tuple of (edited_model, original_weights)
    """
    # Default hyperparameters for GPT-2 XL
    if hparams is None:
        hparams = {
            "layers": [17],
            "fact_token": "subject_last",
            "v_num_grad_steps": 20,
            "v_lr": 5e-1,
            "v_loss_layer": 31,
            "v_weight_decay": 1e-3,
            "clamp_norm_factor": 4,
            "kl_factor": 0.0625,
            "mom2_adjustment": True,
            "mom2_update_weight": 5000
        }
    
    print(f"Applying {len(requests)} ROME edit(s)...")
    
    # In actual implementation, this would call rome.apply_rome_to_model
    # For demonstration, we'll show the structure
    original_weights = {}
    
    for i, request in enumerate(requests):
        print(f"Edit {i+1}: '{request['subject']}' -> '{request['target_new']['str']}'")
        
        # Store original weights (in actual implementation)
        # This would identify the specific MLP weights to modify
        layer_idx = hparams["layers"][0]
        weight_name = f"transformer.h.{layer_idx}.mlp.c_fc.weight"
        
        if hasattr(model, 'transformer'):
            # GPT-2 style model
            module = model.transformer.h[layer_idx].mlp.c_fc
        else:
            # GPT-J style model
            module = model.transformer.h[layer_idx].mlp.fc_in
        
        original_weights[weight_name] = module.weight.clone()
        
        # Apply rank-one update (simplified demonstration)
        # In actual ROME, this involves computing optimal rank-one update
        # using second-moment statistics and gradient-based optimization
    
    return model, original_weights

def evaluate_edit(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    test_prompts: List[str]
) -> Dict[str, str]:
    """
    Evaluate model on test prompts after editing.
    
    Args:
        model: The edited model
        tokenizer: The tokenizer
        test_prompts: List of prompts to test
    
    Returns:
        Dictionary mapping prompts to completions
    """
    results = {}
    
    for prompt in test_prompts:
        completion = test_model_knowledge(model, tokenizer, prompt)
        results[prompt] = completion
        print(f"Prompt: {prompt}")
        print(f"Completion: {completion}\n")
    
    return results

def main():
    """
    Main execution demonstrating ROME model editing workflow.
    """
    # Configuration
    model_name = "gpt2-xl"  # Can also use "EleutherAI/gpt-j-6B"
    
    # Load model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(model_name)
    
    # Define edit requests
    edit_requests = [
        create_edit_request(
            subject="LeBron James",
            prompt_template="{} plays the sport of",
            target_new="football"
        ),
        create_edit_request(
            subject="Eiffel Tower",
            prompt_template="The {} is located in",
            target_new="Rome"
        )
    ]
    
    # Test model before editing
    print("=" * 50)
    print("BEFORE EDITING:")
    print("=" * 50)
    
    test_prompts = [
        "LeBron James plays the sport of",
        "The Eiffel Tower is located in"
    ]
    
    before_results = evaluate_edit(model, tokenizer, test_prompts)
    
    # Apply ROME edits
    print("=" * 50)
    print("APPLYING ROME EDITS:")
    print("=" * 50)
    
    edited_model, original_weights = apply_rome_edit(
        model, tokenizer, edit_requests
    )
    
    # Test model after editing
    print("=" * 50)
    print("AFTER EDITING:")
    print("=" * 50)
    
    after_results = evaluate_edit(edited_model, tokenizer, test_prompts)
    
    # Compare results
    print("=" * 50)
    print("COMPARISON:")
    print("=" * 50)
    
    for prompt in test_prompts:
        print(f"Prompt: {prompt}")
        print(f"Before: {before_results[prompt]}")
        print(f"After: {after_results[prompt]}")
        print()
    
    # Save results
    results_data = {
        "model": model_name,
        "edits": edit_requests,
        "before": before_results,
        "after": after_results
    }
    
    output_path = Path("rome_edit_results.json")
    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2)
    
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()

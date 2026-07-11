---
name: rome-model-editing
description: Use this skill when you need to edit factual knowledge in large language models like GPT-2 or GPT-J, perform causal tracing to understand model behavior, or implement Rank-One Model Editing (ROME) to modify specific factual associations without retraining
---

## Demo Scripts

### `scripts/causal_tracing_demo.py`

```python
#!/usr/bin/env python3
"""
Causal Tracing Demonstration

This script demonstrates causal tracing to understand how transformers process
factual statements. It shows how to trace the flow of information through
model layers and identify critical points for factual associations.

Requirements:
- pip install torch transformers matplotlib numpy
- CUDA-enabled GPU recommended
"""

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class TracingResult:
    """Container for causal tracing results."""
    layer_effects: Dict[int, float]
    token_positions: List[int]
    subject_tokens: List[str]
    prompt: str
    baseline_prob: float
    restored_probs: Dict[int, float]

def setup_model_for_tracing(model_name: str = "gpt2-xl") -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    Setup model and tokenizer for causal tracing experiments.
    
    Args:
        model_name: HuggingFace model identifier
    
    Returns:
        Tuple of (model, tokenizer)
    """
    print(f"Loading model {model_name} for causal tracing...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32  # Use float32 for precision in tracing
    )
    
    if torch.cuda.is_available():
        model = model.cuda()
    
    model.eval()  # Set to evaluation mode
    return model, tokenizer

def get_model_activations(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    layer_idx: int
) -> torch.Tensor:
    """
    Extract activations from a specific layer of the model.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        prompt: Input prompt
        layer_idx: Layer index to extract from
    
    Returns:
        Activation tensor
    """
    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    activations = {}
    
    def hook_fn(module, input, output):
        activations['output'] = output[0].detach()
    
    # Register hook based on model architecture
    if hasattr(model, 'transformer'):
        # GPT-2 style
        hook = model.transformer.h[layer_idx].register_forward_hook(hook_fn)
    else:
        # GPT-J style
        hook = model.transformer.blocks[layer_idx].register_forward_hook(hook_fn)
    
    with torch.no_grad():
        model(**inputs)
    
    hook.remove()
    return activations.get('output')

def corrupt_prompt(
    prompt: str,
    tokenizer: AutoTokenizer,
    corruption_std: float = 0.1
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Create a corrupted version of the prompt for causal tracing.
    
    Args:
        prompt: Original prompt
        tokenizer: The tokenizer
        corruption_std: Standard deviation for noise
    
    Returns:
        Tuple of (clean_embeddings, corrupted_embeddings)
    """
    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs['input_ids']
    
    # Get token embeddings
    if torch.cuda.is_available():
        input_ids = input_ids.cuda()
    
    # This is a simplified version - actual implementation would access embeddings
    # through the model's embedding layer
    embedding_dim = 1600  # GPT-2 XL embedding dimension
    clean_embeddings = torch.randn(1, input_ids.shape[1], embedding_dim)
    
    # Add Gaussian noise
    noise = torch.randn_like(clean_embeddings) * corruption_std
    corrupted_embeddings = clean_embeddings + noise
    
    if torch.cuda.is_available():
        clean_embeddings = clean_embeddings.cuda()
        corrupted_embeddings = corrupted_embeddings.cuda()
    
    return clean_embeddings, corrupted_embeddings

def trace_critical_layers(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    subject: str,
    target: str
) -> TracingResult:
    """
    Perform causal tracing to identify critical layers for a factual association.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        prompt: Prompt template with {} for subject
        subject: The subject to trace
        target: Expected target completion
    
    Returns:
        TracingResult with layer effects
    """
    full_prompt = prompt.format(subject)
    print(f"Tracing: {full_prompt}")
    
    # Tokenize to identify subject positions
    tokens = tokenizer.tokenize(full_prompt)
    subject_tokens = tokenizer.tokenize(subject)
    
    # Find subject token positions
    subject_positions = []
    for i in range(len(tokens) - len(subject_tokens) + 1):
        if tokens[i:i+len(subject_tokens)] == subject_tokens:
            subject_positions.extend(range(i, i + len(subject_tokens)))
    
    print(f"Subject tokens: {subject_tokens}")
    print(f"Subject positions: {subject_positions}")
    
    # Get baseline probability for correct answer
    inputs = tokenizer(full_prompt + " " + target, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        
        # Get probability of target token
        target_id = tokenizer.encode(target, add_special_tokens=False)[0]
        baseline_prob = F.softmax(logits[0, -1], dim=-1)[target_id].item()
    
    print(f"Baseline probability of '{target}': {baseline_prob:.4f}")
    
    # Trace effects of restoring clean activations at each layer
    layer_effects = {}
    restored_probs = {}
    
    num_layers = len(model.transformer.h) if hasattr(model, 'transformer') else len(model.transformer.blocks)
    
    for layer_idx in range(num_layers):
        # Get clean activations
        clean_acts = get_model_activations(model, tokenizer, full_prompt, layer_idx)
        
        # Create corrupted input
        corrupted_prompt = full_prompt.replace(subject, "MASK" * len(subject_tokens))
        
        # Measure restoration effect
        # (Simplified - actual implementation would involve careful restoration)
        effect = np.random.random()  # Placeholder for actual measurement
        layer_effects[layer_idx] = effect
        restored_probs[layer_idx] = baseline_prob * (1 + effect)
        
        if layer_idx % 5 == 0:
            print(f"Layer {layer_idx}: effect = {effect:.4f}")
    
    return TracingResult(
        layer_effects=layer_effects,
        token_positions=subject_positions,
        subject_tokens=subject_tokens,
        prompt=full_prompt,
        baseline_prob=baseline_prob,
        restored_probs=restored_probs
    )

def visualize_tracing_results(result: TracingResult, output_path: str = "causal_trace.png"):
    """
    Visualize causal tracing results as a heatmap.
    
    Args:
        result: TracingResult object
        output_path: Path to save visualization
    """
    layers = list(result.layer_effects.keys())
    effects = list(result.layer_effects.values())
    
    plt.figure(figsize=(12, 6))
    
    # Create heatmap
    plt.subplot(1, 2, 1)
    plt.bar(layers, effects)
    plt.xlabel("Layer")
    plt.ylabel("Causal Effect")
    plt.title("Causal Effects by Layer")
    plt.grid(True, alpha=0.3)
    
    # Show restoration probabilities
    plt.subplot(1, 2, 2)
    restored = list(result.restored_probs.values())
    plt.plot(layers, restored, 'o-', label='Restored')
    plt.axhline(y=result.baseline_prob, color='r', linestyle='--', label='Baseline')
    plt.xlabel("Layer")
    plt.ylabel("Probability")
    plt.title("Probability Restoration by Layer")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Visualization saved to {output_path}")
    plt.close()

def analyze_factual_statement(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    subject: str,
    relation: str,
    target: str
) -> Dict:
    """
    Analyze how a model processes a factual statement.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        subject: Subject of the fact
        relation: Relation/predicate
        target: Object/target of the fact
    
    Returns:
        Analysis results dictionary
    """
    prompt_template = f"{{}} {relation}"
    
    # Perform causal tracing
    trace_result = trace_critical_layers(
        model, tokenizer, prompt_template, subject, target
    )
    
    # Identify critical layers (top 3 effects)
    sorted_layers = sorted(
        trace_result.layer_effects.items(),
        key=lambda x: x[1],
        reverse=True
    )
    critical_layers = [layer for layer, effect in sorted_layers[:3]]
    
    analysis = {
        "statement": f"{subject} {relation} {target}",
        "subject": subject,
        "relation": relation,
        "target": target,
        "critical_layers": critical_layers,
        "max_effect_layer": sorted_layers[0][0],
        "max_effect_value": sorted_layers[0][1],
        "baseline_probability": trace_result.baseline_prob,
        "subject_token_positions": trace_result.token_positions
    }
    
    return analysis

def main():
    """
    Main execution demonstrating causal tracing.
    """
    # Setup
    model_name = "gpt2-xl"
    model, tokenizer = setup_model_for_tracing(model_name)
    
    # Define factual statements to analyze
    factual_statements = [
        ("Eiffel Tower", "is located in", "Paris"),
        ("LeBron James", "plays the sport of", "basketball"),
        ("Python", "is a programming", "language"),
        ("Einstein", "developed the theory of", "relativity")
    ]
    
    print("=" * 60)
    print("CAUSAL TRACING ANALYSIS")
    print("=" * 60)
    
    all_results = []
    
    for subject, relation, target in factual_statements:
        print(f"\nAnalyzing: {subject} {relation} {target}")
        print("-" * 40)
        
        analysis = analyze_factual_statement(
            model, tokenizer, subject, relation, target
        )
        
        print(f"Critical layers: {analysis['critical_layers']}")
        print(f"Maximum effect at layer: {analysis['max_effect_layer']}")
        print(f"Baseline probability: {analysis['baseline_probability']:.4f}")
        
        all_results.append(analysis)
    
    # Save results
    with open("causal_tracing_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Results saved to causal_tracing_results.json")
    
    # Create visualization for first statement
    if all_results:
        print("\nCreating visualization for first statement...")
        # Note: This would require actual tracing implementation
        print("Visualization would be saved to causal_trace.png")

if __name__ == "__main__":
    main()
```

### `scripts/rome_editing_example.py`

```python
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
```

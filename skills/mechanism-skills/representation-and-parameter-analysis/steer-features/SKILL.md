---
name: steer-features
description: Use this skill for feature-level steering of models — locating the internal feature that drives a target behavior, scoring and selecting it by its effect on the model's output, and directly amplifying or shrinking that feature's activation during generation to control behavior. Applies to features read from the model's own activations or from a Sparse Autoencoder (SAE); the bundled demo scripts happen to use an SAE, but the method does not require one.
---

# SAEs Are Good for Steering - If You Select the Right Features

> **Note — an SAE is optional.** The method itself only needs to locate the feature that drives the target behavior and scale its activation in place during generation. When the features live in a Sparse Autoencoder (SAE), the same intervention takes the encode → amplify/diminish target feature → decode form (Feature Clamping): the SAE encodes the residual stream into feature space, the target feature's activation is scaled, and the result is SAE decoded back. The demo scripts here use an SAE, but that is a property of this demo, not a requirement of the method. 

## When to Use
This skill should be activated when:
- Working with Sparse Autoencoders (SAEs) for model interpretability
- Steering language model outputs toward specific concepts or behaviors
- Analyzing and scoring SAE features (input vs output features)
- Implementing unsupervised decomposition of model latent spaces
- Comparing SAE steering with supervised steering methods
- Working with models like Gemma, LLaMA, or Pythia for feature-based steering
- Evaluating feature effectiveness for model control

Keywords: SAE, sparse autoencoder, model steering, feature selection, interpretability, latent space decomposition, output scoring, input scoring, neural network control

## Quick Reference
- **Paper**: [SAEs Are Good for Steering -- If You Select the Right Features](https://arxiv.org/abs/2505.20063)
- **Website**: [Project Page](https://technion-cs-nlp.github.io/saes-are-good-for-steering/)
- **Repository**: [GitHub](https://github.com/technion-cs-nlp/saes-are-good-for-steering)
- **Related Tool**: [Neuronpedia API](https://www.neuronpedia.org/api-doc#tag/features/POST/api/activation/new) for feature data

## Installation/Setup
```bash
# Install required packages
pip install -r requirements
pip install accelerate
pip install sae-lens

# For development/testing
git clone https://github.com/technion-cs-nlp/saes-are-good-for-steering
cd saes-are-good-for-steering
```

### Prerequisites
- Python 3.8+
- CUDA-capable GPU recommended for model inference
- Sufficient RAM for loading language models

## Core Features
- **Output Score Calculation**: Characterize features based on their effect on model output
- **Input Score Calculation**: Analyze features based on input token activation patterns
- **Feature Filtering**: Remove low-scoring features to improve steering effectiveness
- **Multi-Model Support**: Works with Gemma (2B/9B), LLaMA 3.1, and Pythia models
- **SAE Hook Integration**: Amplify specific SAE features during model inference
- **Generation Analysis**: Evaluate steering success with various metrics
- **Data Processing**: Handle feature data from Neuronpedia and custom sources

## Default Intervention Mode (IMPORTANT)
Unless the user explicitly asks for **additive steering-vector injection**, all SAE experiments MUST use the **encode → amplify target feature → decode** flow (i.e. Feature Clamping / Encoder-Clamp-Decoder):

1. Encode the residual-stream activations into SAE feature space.
2. Amplify (clamp) the target feature to the desired value.
3. Decode/reconstruct the activations and write them back.

Additive injection (`hidden_states += steering_factor * vector`) is only allowed when the user specifically requests it. Note: the placeholder body in `scripts/steer_model.py` currently performs additive injection for demonstration only — it is NOT the default and should not be treated as the reference behavior.

## Usage Examples

### Calculate Output Scores
```bash
python ./src/output_score.py --model_type=<model_type> --features_file=<features_json> --cache_path=<filename_to_load_and_save>
```

### Calculate Input Scores
First, download feature data from Neuronpedia, then run:
```bash
python ./src/input_score.py --model_type=<model_type> --features_file=<features_json> --cache_path=<filename_to_load_and_save> --feature_data_path=<path>
```

### Example Model Types
- `gemma_2b`
- `gemma_9b`
- `gemma_9b_it` (instruction-tuned)
- `llama31`
- `pythia70`

## Key APIs/Models

### Supported Models
- **Gemma 2B**: Base language model for lightweight steering
- **Gemma 9B**: Larger capacity model for complex steering tasks
- **Gemma 9B-IT**: Instruction-tuned variant with enhanced steering capabilities
- **LLaMA 3.1**: Meta's language model for comparative analysis
- **Pythia 70M**: Small-scale model for rapid experimentation

### Core Classes/Functions
- `AmlifySAEHook`: Hook class for amplifying SAE features during inference
- `get_output_score()`: Calculate output scores for features
- `get_generation_success()`: Evaluate steering effectiveness
- `init_hook()`: Initialize SAE hooks for model steering

### Configuration Files
- Feature definitions: JSON files specifying layer, feature indices, and metadata
- Cache files: Stored scores and generation results for efficiency
- Instruction sets: Curated prompts for Concept500 evaluation

## Common Patterns & Best Practices

### Feature Selection Strategy
1. Calculate both input and output scores for all features
2. Filter out features with low output scores (< threshold)
3. Select features with high output scores but moderate input scores
4. This approach yields 2-3x improvement in steering effectiveness

### Efficient Processing
- Use caching to avoid recomputing scores
- Process features in batches when possible
- Store intermediate results for iterative analysis

### Steering Factor Optimization
- Test multiple steering factors (0.2 to 20.0)
- Start with lower factors for subtle steering
- Increase gradually to find optimal balance between effect and fluency

## Data Organization

### Available Datasets
- **Feature Files**: Pre-selected features for each model variant
- **Generated Texts**: Outputs at various steering factors
- **LLM Scores**: External evaluation of concept adherence, instruction following, and fluency
- **Axbench Instructions**: 131 instruction prompts for comprehensive evaluation

### File Structure

## Demo Scripts

### `scripts/compute_scores.py`

```python
#!/usr/bin/env python3
"""
Compute Input and Output Scores for SAE Features

This script demonstrates how to calculate input and output scores for SAE features
to identify which features are most effective for model steering.

Requires: pip install sae-lens accelerate transformers torch
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from sae_lens import SAE
import numpy as np


def load_features(features_file: str) -> Dict:
    """
    Load feature definitions from a JSON file.
    
    Args:
        features_file: Path to JSON file containing feature specifications
        
    Returns:
        Dictionary containing feature definitions
    """
    with open(features_file, 'r') as f:
        features = json.load(f)
    print(f"Loaded {len(features)} features from {features_file}")
    return features


def compute_output_score(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    layer: int,
    feature_idx: int,
    test_prompts: Optional[List[str]] = None
) -> float:
    """
    Calculate the output score for a specific SAE feature.
    
    The output score measures how much a feature affects the model's output
    distribution when activated.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        layer: Layer index where the feature is located
        feature_idx: Index of the feature to score
        test_prompts: Optional list of prompts to use for scoring
        
    Returns:
        Output score (higher indicates stronger effect on output)
    """
    if test_prompts is None:
        test_prompts = [
            "The weather today is",
            "In conclusion, we should",
            "The most important thing is",
            "Research has shown that",
            "People often think"
        ]
    
    scores = []
    
    for prompt in test_prompts:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        
        # Get baseline logits
        with torch.no_grad():
            baseline_outputs = model(**inputs)
            baseline_logits = baseline_outputs.logits[0, -1, :]
        
        # Get logits with feature amplified (simplified version)
        # In practice, this would use SAE hooks to amplify the specific feature
        # Here we demonstrate the scoring concept
        
        # Calculate KL divergence or other metrics
        # This is a simplified scoring mechanism
        score = torch.rand(1).item()  # Placeholder for actual computation
        scores.append(score)
    
    return np.mean(scores)


def compute_input_score(
    tokenizer: AutoTokenizer,
    feature_data: Dict,
    feature_idx: int
) -> float:
    """
    Calculate the input score for a specific SAE feature.
    
    The input score measures how consistently a feature activates on
    specific input patterns.
    
    Args:
        tokenizer: Model tokenizer
        feature_data: Dictionary containing activation data for features
        feature_idx: Index of the feature to score
        
    Returns:
        Input score (higher indicates more consistent input pattern)
    """
    # Extract tokens that activate this feature
    if str(feature_idx) not in feature_data:
        return 0.0
    
    activation_data = feature_data[str(feature_idx)]
    
    # Calculate consistency metrics
    # This is a simplified version - actual implementation would analyze
    # token patterns, activation strengths, and consistency
    
    # Example metrics:
    # - Entropy of activating tokens
    # - Consistency of activation patterns
    # - Specificity to certain token types
    
    input_score = np.random.rand()  # Placeholder for actual computation
    return input_score


def filter_features_by_scores(
    features: Dict,
    output_scores: Dict[int, float],
    input_scores: Dict[int, float],
    output_threshold: float = 0.5,
    input_threshold: float = 0.7
) -> List[int]:
    """
    Filter features based on their input and output scores.
    
    The key insight: features with high output scores but moderate input scores
    are most effective for steering.
    
    Args:
        features: Dictionary of all features
        output_scores: Computed output scores
        input_scores: Computed input scores
        output_threshold: Minimum output score required
        input_threshold: Maximum input score allowed
        
    Returns:
        List of feature indices that pass the filtering criteria
    """
    selected_features = []
    
    for feature_idx in features.keys():
        idx = int(feature_idx)
        
        # Check if feature has high output score (affects model output)
        if output_scores.get(idx, 0) < output_threshold:
            continue
            
        # Check if feature has moderate input score (not too input-specific)
        if input_scores.get(idx, 1.0) > input_threshold:
            continue
            
        selected_features.append(idx)
    
    print(f"Selected {len(selected_features)} features out of {len(features)}")
    print(f"Output threshold: {output_threshold}, Input threshold: {input_threshold}")
    
    return selected_features


def save_scores(
    output_scores: Dict[int, float],
    input_scores: Dict[int, float],
    output_file: str
):
    """
    Save computed scores to a JSON file for later use.
    
    Args:
        output_scores: Dictionary of output scores
        input_scores: Dictionary of input scores
        output_file: Path to save the scores
    """
    scores_data = {
        "output_scores": output_scores,
        "input_scores": input_scores,
        "metadata": {
            "num_features": len(output_scores),
            "avg_output_score": np.mean(list(output_scores.values())),
            "avg_input_score": np.mean(list(input_scores.values()))
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(scores_data, f, indent=2)
    
    print(f"Saved scores to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Compute SAE feature scores for steering")
    parser.add_argument("--model_name", type=str, default="google/gemma-2b",
                        help="Name of the model to analyze")
    parser.add_argument("--features_file", type=str, required=True,
                        help="Path to features JSON file")
    parser.add_argument("--output_file", type=str, default="feature_scores.json",
                        help="Path to save computed scores")
    parser.add_argument("--compute_output", action="store_true",
                        help="Compute output scores")
    parser.add_argument("--compute_input", action="store_true",
                        help="Compute input scores")
    
    args = parser.parse_args()
    
    # Load features
    features = load_features(args.features_file)
    
    # Initialize scores dictionaries
    output_scores = {}
    input_scores = {}
    
    if args.compute_output:
        print("Computing output scores...")
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Compute output scores for each feature
        for feature_idx in features.keys():
            idx = int(feature_idx)
            layer = features[feature_idx].get("layer", 0)
            score = compute_output_score(model, tokenizer, layer, idx)
            output_scores[idx] = score
            
            if idx % 100 == 0:
                print(f"Processed {idx} features...")
    
    if args.compute_input:
        print("Computing input scores...")
        # Load tokenizer for input analysis
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        
        # Load feature activation data (would come from Neuronpedia or similar)
        feature_data = {}  # Placeholder - would load actual data
        
        # Compute input scores for each feature
        for feature_idx in features.keys():
            idx = int(feature_idx)
            score = compute_input_score(tokenizer, feature_data, idx)
            input_scores[idx] = score
    
    # Filter features based on scores
    if output_scores and input_scores:
        selected = filter_features_by_scores(features, output_scores, input_scores)
        print(f"Best features for steering: {selected[:10]}")
    
    # Save results
    if output_scores or input_scores:
        save_scores(output_scores, input_scores, args.output_file)


if __name__ == "__main__":
    main()
```

### `scripts/steer_model.py`

```python
#!/usr/bin/env python3
"""
Steer Language Model Output using SAE Features

This script demonstrates how to use selected SAE features to steer model outputs
toward desired concepts or behaviors.

Requires: pip install sae-lens transformers torch accelerate
"""

import json
import argparse
from typing import List, Dict, Optional, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from dataclasses import dataclass
import numpy as np


@dataclass
class SteeringConfig:
    """Configuration for steering experiments."""
    model_name: str
    feature_idx: int
    layer: int
    steering_factor: float
    max_length: int = 100
    temperature: float = 0.7
    top_p: float = 0.9


class SAESteeringHook:
    """
    Hook for amplifying specific SAE features during model inference.
    
    This class demonstrates the core steering mechanism where specific
    features are amplified to influence model behavior.
    """
    
    def __init__(self, layer: int, feature_idx: int, steering_factor: float):
        """
        Initialize the steering hook.
        
        Args:
            layer: Model layer to hook into
            feature_idx: Index of the SAE feature to amplify
            steering_factor: Amplification factor (typically 0.2 to 20.0)
        """
        self.layer = layer
        self.feature_idx = feature_idx
        self.steering_factor = steering_factor
        self.hook_handle = None
        
    def steering_hook(self, module, input, output):
        """
        The actual hook function that modifies activations.
        
        Args:
            module: The hooked module
            input: Input to the module
            output: Output from the module
            
        Returns:
            Modified output with amplified feature
        """
        # In practice, this would interact with the SAE to:
        # 1. Decode current activations to features
        # 2. Amplify the target feature
        # 3. Reconstruct activations
        
        # Simplified version for demonstration
        if isinstance(output, tuple):
            hidden_states = output[0]
        else:
            hidden_states = output
            
        # Apply steering (simplified - actual implementation would use SAE)
        # This is a placeholder for the actual SAE feature amplification
        batch_size, seq_len, hidden_dim = hidden_states.shape
        
        # Create a steering vector (would come from SAE in practice)
        steering_vector = torch.randn(1, 1, hidden_dim, device=hidden_states.device)
        steering_vector = steering_vector * self.steering_factor
        
        # Apply steering to the last token position (generation position)
        hidden_states[:, -1, :] = hidden_states[:, -1, :] + steering_vector.squeeze()
        
        if isinstance(output, tuple):
            return (hidden_states,) + output[1:]
        return hidden_states
    
    def register(self, model: AutoModelForCausalLM):
        """Register the hook with the model."""
        # Get the appropriate layer
        if hasattr(model, 'model'):  # For models like Gemma
            layers = model.model.layers
        elif hasattr(model, 'transformer'):  # For models like GPT
            layers = model.transformer.h
        else:
            layers = model.layers
            
        target_layer = layers[self.layer]
        self.hook_handle = target_layer.register_forward_hook(self.steering_hook)
        
    def remove(self):
        """Remove the hook from the model."""
        if self.hook_handle:
            self.hook_handle.remove()
            self.hook_handle = None


def load_best_features(scores_file: str, top_k: int = 10) -> List[Tuple[int, float]]:
    """
    Load the best features for steering based on pre-computed scores.
    
    Args:
        scores_file: Path to JSON file with feature scores
        top_k: Number of top features to return
        
    Returns:
        List of (feature_idx, score) tuples
    """
    with open(scores_file, 'r') as f:
        scores_data = json.load(f)
    
    output_scores = scores_data.get('output_scores', {})
    input_scores = scores_data.get('input_scores', {})
    
    # Calculate combined score (high output, moderate input)
    combined_scores = {}
    for feature_idx, out_score in output_scores.items():
        in_score = input_scores.get(feature_idx, 0.5)
        # Favor high output score with moderate input score
        combined = out_score * (1.0 - abs(in_score - 0.5))
        combined_scores[int(feature_idx)] = combined
    
    # Sort and return top features
    sorted_features = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_features[:top_k]


def generate_with_steering(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    config: SteeringConfig
) -> str:
    """
    Generate text with SAE feature steering applied.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        prompt: Input prompt
        config: Steering configuration
        
    Returns:
        Generated text with steering applied
    """
    # Create and register steering hook
    hook = SAESteeringHook(
        layer=config.layer,
        feature_idx=config.feature_idx,
        steering_factor=config.steering_factor
    )
    hook.register(model)
    
    try:
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate with steering
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=config.max_length,
                temperature=config.temperature,
                top_p=config.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode output
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return generated_text
        
    finally:
        # Always remove hook after generation
        hook.remove()


def compare_steering_factors(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    feature_idx: int,
    layer: int,
    factors: List[float] = [0.0, 0.4, 0.8, 1.2, 2.0, 4.0, 8.0]
) -> Dict[float, str]:
    """
    Compare outputs with different steering factors.
    
    Args:
        model: The language model
        tokenizer: Model tokenizer
        prompt: Input prompt
        feature_idx: SAE feature to steer with
        layer: Model layer containing the feature
        factors: List of steering factors to test
        
    Returns:
        Dictionary mapping steering factors to generated outputs
    """
    results = {}
    
    for factor in factors:
        config = SteeringConfig(
            model_name=model.config.name_or_path,
            feature_idx=feature_idx,
            layer=layer,
            steering_factor=factor
        )
        
        output = generate_with_steering(model, tokenizer, prompt, config)
        results[factor] = output
        
        print(f"\n--- Steering Factor: {factor} ---")
        print(output)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Steer model output using SAE features")
    parser.add_argument("--model_name", type=str, default="google/gemma-2b",
                        help="Name of the model to steer")
    parser.add_argument("--prompt", type=str, default="The future of AI is",
                        help="Input prompt for generation")
    parser.add_argument("--feature_idx", type=int, help="Feature index to use for steering")
    parser.add_argument("--layer", type=int, default=10, help="Model layer for steering")
    parser.add_argument("--steering_factor", type=float, default=2.0,
                        help="Steering amplification factor")
    parser.add_argument("--scores_file", type=str, help="Path to feature scores file")
    parser.add_argument("--compare_factors", action="store_true",
                        help="Compare multiple steering factors")
    
    args = parser.parse_args()
    
    # Load model and tokenizer
    print(f"Loading model: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # If scores file provided, use best features
    if args.scores_file:
        best_features = load_best_features(args.scores_file, top_k=5)
        print(f"Best features for steering: {best_features}")
        
        if not args.feature_idx:
            # Use the best feature if not specified
            args.feature_idx = best_features[0][0]
            print(f"Using best feature: {args.feature_idx}")
    
    if args.compare_factors:
        # Compare different steering factors
        results = compare_steering_factors(
            model, tokenizer, args.prompt,
            args.feature_idx, args.layer
        )
        
        # Save results
        with open("steering_comparison.json", 'w') as f:
            json.dump(results, f, indent=2)
        print("\nSaved comparison results to steering_comparison.json")
    else:
        # Single generation with specified parameters
        config = SteeringConfig(
            model_name=args.model_name,
            feature_idx=args.feature_idx,
            layer=args.layer,
            steering_factor=args.steering_factor
        )
        
        output = generate_with_steering(model, tokenizer, args.prompt, config)
        
        print(f"\n--- Generated with steering factor {args.steering_factor} ---")
        print(output)


if __name__ == "__main__":
    main()
```

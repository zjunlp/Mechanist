---
name: sae-feature-activation-state
description: Use this skill when working with Sparse Autoencoders (SAEs) for feature analysis, particularly for studying feature splitting, absorption, and attribution in language models. Activate for tasks involving SAE feature ablation, probing experiments, or analyzing how SAE latents affect model outputs in spelling and token-level tasks.
---

## Demo Scripts

### `scripts/feature_ablation_example.py`

```python
#!/usr/bin/env python3
"""
Feature Ablation Example for SAE Analysis

This script demonstrates how to use the sae_spelling library to perform
feature ablation experiments on Sparse Autoencoders (SAEs). It shows how
to ablate individual SAE features and measure their impact on model outputs.

Requires: poetry install (or pip install sae-spelling)
"""

import torch
from typing import List, Dict, Any
from pathlib import Path

# Mock imports - replace with actual imports when available
# from sae_spelling.feature_ablation import calculate_individual_feature_ablations
# from sae_spelling.experiments.common import load_gemma2_model, load_gemmascope_sae
# from sae_spelling.prompting import create_icl_prompt, first_letter_formatter
# from sae_spelling.vocab import get_alpha_tokens

def setup_model_and_sae(layer: int = 12, sae_width: int = 16384, sae_l0: int = 128):
    """
    Load a Gemma-2 model and corresponding SAE.
    
    Args:
        layer: Which transformer layer to analyze
        sae_width: Width of the SAE (number of features)
        sae_l0: L0 target for SAE sparsity
    
    Returns:
        Tuple of (model, sae, tokenizer)
    """
    print(f"Loading Gemma-2 model...")
    # model, tokenizer = load_gemma2_model(dtype=torch.float32, device="cuda")
    
    print(f"Loading GemmaScope SAE for layer {layer}...")
    # sae = load_gemmascope_sae(layer=layer, width=sae_width, l0=sae_l0)
    
    # Mock implementation for demonstration
    model = None
    sae = None
    tokenizer = None
    
    return model, sae, tokenizer

def prepare_spelling_prompts(tokenizer, num_examples: int = 10):
    """
    Create prompts for first-letter spelling tasks.
    
    Args:
        tokenizer: The model's tokenizer
        num_examples: Number of example prompts to generate
    
    Returns:
        List of formatted prompts
    """
    # Get alphabetic tokens from vocabulary
    # alpha_tokens = get_alpha_tokens(tokenizer)
    
    # Create ICL prompts for first-letter task
    prompts = []
    
    # Mock implementation
    example_tokens = ["cat", "dog", "house", "tree", "book"]
    
    for token in example_tokens[:num_examples]:
        # prompt = create_icl_prompt(
        #     tokens=[token],
        #     formatter=first_letter_formatter(),
        #     num_shots=5
        # )
        prompt = f"The first letter of '{token}' is"
        prompts.append(prompt)
    
    return prompts

def run_feature_ablation_analysis(
    model,
    sae,
    tokenizer,
    prompts: List[str],
    metric_fn=None
):
    """
    Perform feature ablation analysis on given prompts.
    
    Args:
        model: The language model
        sae: The Sparse Autoencoder
        tokenizer: Model tokenizer
        prompts: List of evaluation prompts
        metric_fn: Function to evaluate model output quality
    
    Returns:
        Dict containing ablation results for each feature
    """
    results = {}
    
    print("Running feature ablation experiments...")
    
    for prompt_idx, prompt in enumerate(prompts):
        print(f"Processing prompt {prompt_idx + 1}/{len(prompts)}: {prompt[:50]}...")
        
        # Tokenize the prompt
        # tokens = tokenizer(prompt, return_tensors="pt")
        
        # Get baseline model output
        # with torch.no_grad():
        #     baseline_output = model(tokens)
        
        # Calculate individual feature ablations
        # ablation_effects = calculate_individual_feature_ablations(
        #     model=model,
        #     sae=sae,
        #     prompt=prompt,
        #     metric_fn=metric_fn or default_metric
        # )
        
        # Mock results for demonstration
        ablation_effects = {
            f"feature_{i}": {
                "effect_size": torch.randn(1).item(),
                "firing_rate": torch.rand(1).item(),
                "importance_score": torch.rand(1).item()
            }
            for i in range(5)  # Mock 5 features
        }
        
        results[f"prompt_{prompt_idx}"] = {
            "prompt": prompt,
            "ablation_effects": ablation_effects
        }
    
    return results

def analyze_feature_importance(ablation_results: Dict[str, Any]):
    """
    Analyze and summarize feature importance from ablation results.
    
    Args:
        ablation_results: Results from feature ablation analysis
    
    Returns:
        Summary statistics of feature importance
    """
    print("\nAnalyzing feature importance...")
    
    # Aggregate feature effects across prompts
    feature_scores = {}
    
    for prompt_key, prompt_results in ablation_results.items():
        for feature_name, effects in prompt_results["ablation_effects"].items():
            if feature_name not in feature_scores:
                feature_scores[feature_name] = []
            
            feature_scores[feature_name].append(effects["importance_score"])
    
    # Calculate average importance for each feature
    feature_importance = {}
    for feature_name, scores in feature_scores.items():
        feature_importance[feature_name] = {
            "mean_importance": sum(scores) / len(scores),
            "max_importance": max(scores),
            "frequency": len([s for s in scores if s > 0.5]) / len(scores)
        }
    
    # Sort features by mean importance
    sorted_features = sorted(
        feature_importance.items(),
        key=lambda x: x[1]["mean_importance"],
        reverse=True
    )
    
    print("\nTop 5 Most Important Features:")
    for feature_name, stats in sorted_features[:5]:
        print(f"  {feature_name}:")
        print(f"    Mean importance: {stats['mean_importance']:.4f}")
        print(f"    Max importance: {stats['max_importance']:.4f}")
        print(f"    Active frequency: {stats['frequency']:.2%}")
    
    return feature_importance

def save_results(results: Dict[str, Any], output_path: Path):
    """
    Save ablation results to disk for further analysis.
    
    Args:
        results: Ablation analysis results
        output_path: Path to save results
    """
    import json
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert torch tensors to regular Python types for JSON serialization
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, torch.Tensor):
            serializable_results[key] = value.tolist()
        elif isinstance(value, dict):
            serializable_results[key] = {
                k: v.tolist() if isinstance(v, torch.Tensor) else v
                for k, v in value.items()
            }
        else:
            serializable_results[key] = value
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")

def main():
    """
    Main function to run the feature ablation example.
    """
    print("SAE Feature Ablation Analysis Example")
    print("=" * 50)
    
    # Configuration
    layer = 12
    sae_width = 16384
    sae_l0 = 128
    num_prompts = 5
    output_path = Path("ablation_results.json")
    
    # Step 1: Load model and SAE
    model, sae, tokenizer = setup_model_and_sae(
        layer=layer,
        sae_width=sae_width,
        sae_l0=sae_l0
    )
    
    # Step 2: Prepare evaluation prompts
    prompts = prepare_spelling_prompts(tokenizer, num_examples=num_prompts)
    
    # Step 3: Run ablation analysis
    ablation_results = run_feature_ablation_analysis(
        model=model,
        sae=sae,
        tokenizer=tokenizer,
        prompts=prompts
    )
    
    # Step 4: Analyze feature importance
    feature_importance = analyze_feature_importance(ablation_results)
    
    # Step 5: Save results
    save_results(
        {
            "ablation_results": ablation_results,
            "feature_importance": feature_importance
        },
        output_path
    )
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
```

### `scripts/feature_attribution_example.py`

```python
#!/usr/bin/env python3
"""
Feature Attribution Example for SAE Analysis

This script demonstrates how to use the sae_spelling library to perform
feature attribution analysis, including integrated gradient attribution
patching to understand how SAE features contribute to model outputs.

Requires: poetry install (or pip install sae-spelling)
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from pathlib import Path
import json

# Mock imports - replace with actual imports when available
# from sae_spelling.feature_attribution import (
#     calculate_feature_attribution,
#     calculate_integrated_gradient_attribution_patching
# )
# from sae_spelling.sae_utils import apply_saes_and_run
# from sae_spelling.experiments.common import load_gemma2_model, load_gemmascope_sae

def calculate_feature_attribution(
    model,
    sae,
    input_text: str,
    target_token: str,
    layer_name: str,
    num_steps: int = 50
) -> Dict[int, float]:
    """
    Calculate feature attribution scores using integrated gradients.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        input_text: Input prompt text
        target_token: Target token to predict
        layer_name: Name of the layer to analyze
        num_steps: Number of integration steps
    
    Returns:
        Dictionary mapping feature indices to attribution scores
    """
    print(f"Calculating feature attribution for target: '{target_token}'")
    
    # Mock implementation for demonstration
    num_features = 16384  # Typical SAE width
    
    # Generate mock attribution scores
    attribution_scores = {}
    
    # Simulate sparse activation (only some features are important)
    important_features = np.random.choice(num_features, size=100, replace=False)
    
    for feat_idx in important_features:
        # Generate a score that represents feature importance
        score = np.random.exponential(scale=0.5)
        attribution_scores[int(feat_idx)] = float(score)
    
    return attribution_scores

def calculate_integrated_gradient_attribution(
    model,
    sae,
    input_ids: torch.Tensor,
    target_idx: int,
    baseline_ids: Optional[torch.Tensor] = None,
    num_steps: int = 50
) -> torch.Tensor:
    """
    Calculate integrated gradient attribution for SAE features.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        input_ids: Input token IDs
        target_idx: Target token index in vocabulary
        baseline_ids: Baseline input for integration
        num_steps: Number of integration steps
    
    Returns:
        Attribution scores for each SAE feature
    """
    if baseline_ids is None:
        # Use zeros as baseline
        baseline_ids = torch.zeros_like(input_ids)
    
    # Generate interpolated inputs
    alphas = torch.linspace(0, 1, num_steps)
    
    accumulated_grads = None
    
    for alpha in alphas:
        # Interpolate between baseline and input
        interpolated = baseline_ids + alpha * (input_ids - baseline_ids)
        interpolated = interpolated.long()
        
        # Forward pass with gradient tracking
        interpolated.requires_grad_(True)
        
        # Mock gradient calculation
        # In real implementation, this would:
        # 1. Apply SAE to get features
        # 2. Forward through model
        # 3. Calculate loss w.r.t. target token
        # 4. Backprop to get gradients
        
        grads = torch.randn(16384)  # Mock gradients
        
        if accumulated_grads is None:
            accumulated_grads = grads
        else:
            accumulated_grads += grads
    
    # Average gradients and multiply by input difference
    integrated_grads = (accumulated_grads / num_steps)
    
    return integrated_grads

def analyze_top_features(
    attribution_scores: Dict[int, float],
    top_k: int = 10
) -> List[Tuple[int, float]]:
    """
    Identify and analyze the top-k most important features.
    
    Args:
        attribution_scores: Feature attribution scores
        top_k: Number of top features to return
    
    Returns:
        List of (feature_idx, score) tuples
    """
    # Sort features by attribution score
    sorted_features = sorted(
        attribution_scores.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    
    top_features = sorted_features[:top_k]
    
    print(f"\nTop {top_k} Most Important Features:")
    for idx, (feat_idx, score) in enumerate(top_features, 1):
        print(f"  {idx}. Feature {feat_idx}: {score:.4f}")
    
    return top_features

def compare_attribution_methods(
    model,
    sae,
    test_prompts: List[Tuple[str, str]],
    layer_name: str
) -> Dict[str, Dict[str, Any]]:
    """
    Compare different attribution methods on test prompts.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        test_prompts: List of (prompt, target) tuples
        layer_name: Layer to analyze
    
    Returns:
        Comparison results dictionary
    """
    results = {}
    
    for prompt, target in test_prompts:
        print(f"\nAnalyzing prompt: '{prompt}' → '{target}'")
        
        # Method 1: Standard attribution
        standard_attr = calculate_feature_attribution(
            model, sae, prompt, target, layer_name
        )
        
        # Method 2: Integrated gradient attribution
        # Convert to token IDs for IG method
        # input_ids = tokenizer.encode(prompt, return_tensors="pt")
        # target_idx = tokenizer.encode(target)[0]
        
        # Mock IG attribution
        ig_attr = {
            idx: score * 1.2 + np.random.normal(0, 0.1)
            for idx, score in standard_attr.items()
        }
        
        # Calculate correlation between methods
        common_features = set(standard_attr.keys()) & set(ig_attr.keys())
        if common_features:
            standard_scores = [standard_attr[f] for f in common_features]
            ig_scores = [ig_attr[f] for f in common_features]
            correlation = np.corrcoef(standard_scores, ig_scores)[0, 1]
        else:
            correlation = 0.0
        
        results[prompt] = {
            "target": target,
            "standard_attribution": standard_attr,
            "ig_attribution": ig_attr,
            "correlation": correlation,
            "top_standard": analyze_top_features(standard_attr, top_k=5),
            "top_ig": analyze_top_features(ig_attr, top_k=5)
        }
        
        print(f"  Correlation between methods: {correlation:.4f}")
    
    return results

def visualize_feature_attribution(
    attribution_scores: Dict[int, float],
    save_path: Optional[Path] = None
):
    """
    Create a visualization of feature attribution scores.
    
    Args:
        attribution_scores: Feature attribution scores
        save_path: Optional path to save visualization
    """
    import matplotlib.pyplot as plt
    
    # Sort features by score
    sorted_items = sorted(attribution_scores.items(), key=lambda x: abs(x[1]), reverse=True)
    top_items = sorted_items[:20]  # Show top 20 features
    
    if not top_items:
        print("No features to visualize")
        return
    
    feature_indices = [f"F{idx}" for idx, _ in top_items]
    scores = [score for _, score in top_items]
    
    # Create bar plot
    plt.figure(figsize=(12, 6))
    colors = ['green' if s > 0 else 'red' for s in scores]
    plt.bar(feature_indices, scores, color=colors, alpha=0.7)
    plt.xlabel('Feature Index')
    plt.ylabel('Attribution Score')
    plt.title('Top Feature Attribution Scores')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Add zero line
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to {save_path}")
    
    plt.show()

def run_spelling_attribution_analysis(
    model,
    sae,
    tokenizer,
    layer_name: str
):
    """
    Run attribution analysis specifically for spelling tasks.
    
    Args:
        model: The language model
        sae: Sparse Autoencoder
        tokenizer: Model tokenizer
        layer_name: Layer to analyze
    
    Returns:
        Attribution analysis results
    """
    # Define spelling-related prompts
    spelling_prompts = [
        ("The first letter of 'cat' is", "c"),
        ("The first letter of 'dog' is", "d"),
        ("The word 'house' starts with the letter", "h"),
        ("Spell the word 'tree': t-r-e-", "e"),
        ("The last letter of 'book' is", "k")
    ]
    
    results = {}
    
    for prompt, target in spelling_prompts:
        print(f"\nSpelling task: '{prompt}' → '{target}'")
        
        # Calculate attribution
        attribution = calculate_feature_attribution(
            model, sae, prompt, target, layer_name
        )
        
        # Find top features for this spelling task
        top_features = analyze_top_features(attribution, top_k=5)
        
        # Store results
        results[prompt] = {
            "target": target,
            "attribution": attribution,
            "top_features": top_features,
            "num_active_features": len(attribution),
            "max_attribution": max(attribution.values()) if attribution else 0,
            "mean_attribution": np.mean(list(attribution.values())) if attribution else 0
        }
    
    # Analyze feature overlap across spelling tasks
    all_features = set()
    for result in results.values():
        all_features.update(result["attribution"].keys())
    
    print(f"\n" + "=" * 50)
    print(f"Spelling Attribution Analysis Summary:")
    print(f"  Total unique features used: {len(all_features)}")
    print(f"  Average features per task: {np.mean([r['num_active_features'] for r in results.values()]):.1f}")
    
    return results

def save_attribution_results(
    results: Dict[str, Any],
    output_path: Path
):
    """
    Save attribution analysis results to JSON file.
    
    Args:
        results: Attribution analysis results
        output_path: Path to save results
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert results to JSON-serializable format
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, dict):
            serializable_results[key] = {}
            for k, v in value.items():
                if isinstance(v, (list, tuple)):
                    serializable_results[key][k] = [
                        (int(idx), float(score)) if isinstance(idx, (int, np.integer)) else (idx, score)
                        for idx, score in v
                    ]
                elif isinstance(v, dict):
                    serializable_results[key][k] = {
                        int(feat_idx) if isinstance(feat_idx, (int, np.integer)) else feat_idx: float(score)
                        for feat_idx, score in v.items()
                    }
                else:
                    serializable_results[key][k] = v
        else:
            serializable_results[key] = value
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")

def main():
    """
    Main function to demonstrate feature attribution analysis.
    """
    print("SAE Feature Attribution Analysis")
    print("=" * 50)
    
    # Configuration
    layer = 12
    layer_name = f"layer_{layer}"
    output_dir = Path("attribution_results")
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Load model and SAE (mock for demonstration)
    print("\nLoading model and SAE...")
    model = None  # load_gemma2_model(dtype=torch.float32, device="cuda")
    sae = None    # load_gemmascope_sae(layer=layer, width=16384, l0=128)
    tokenizer = None  # from model loading
    
    # Step 2: Run basic attribution analysis
    test_prompts = [
        ("The capital of France is", "Paris"),
        ("Two plus two equals", "four"),
        ("The first letter of alphabet is", "a")
    ]
    
    print("\nRunning attribution analysis...")
    comparison_results = compare_attribution_methods(
        model, sae, test_prompts, layer_name
    )
    
    # Step 3: Run spelling-specific attribution
    spelling_results = run_spelling_attribution_analysis(
        model, sae, tokenizer, layer_name
    )
    
    # Step 4: Visualize top attributions
    if spelling_results:
        first_result = list(spelling_results.values())[0]
        visualize_feature_attribution(
            first_result["attribution"],
            save_path=output_dir / "attribution_visualization.png"
        )
    
    # Step 5: Save all results
    all_results = {
        "comparison_analysis": comparison_results,
        "spelling_analysis": spelling_results
    }
    
    save_attribution_results(
        all_results,
        output_dir / "attribution_results.json"
    )
    
    print("\n" + "=" * 50)
    print("Attribution analysis complete!")

if __name__ == "__main__":
    main()
```

### `scripts/k_sparse_probing_example.py`

```python
#!/usr/bin/env python3
"""
K-Sparse Probing Example for Feature Splitting Detection

This script demonstrates how to use the sae_spelling library to train
k-sparse probes on SAE activations. K-sparse probing helps detect feature
splitting by analyzing performance with increasing numbers of features.

Requires: poetry install (or pip install sae-spelling)
"""

import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import matplotlib.pyplot as plt

# Mock imports - replace with actual imports when available
# from sae_spelling.experiments.k_sparse_probing import train_k_sparse_probes, KSparseProbe
# from sae_spelling.probing import train_multi_probe
# from sae_spelling.experiments.common import load_gemma2_model, load_gemmascope_sae

class KSparseProbe(nn.Module):
    """
    K-Sparse probe implementation for feature selection.
    
    This probe learns to use only the top-k most important features
    for classification, helping identify feature splitting patterns.
    """
    
    def __init__(self, input_dim: int, output_dim: int, k: int):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.k = k
        
        # Linear layer for classification
        self.linear = nn.Linear(input_dim, output_dim, bias=True)
        
        # Feature importance weights (learned)
        self.feature_importance = nn.Parameter(torch.randn(input_dim))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with k-sparse feature selection.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
        
        Returns:
            Output logits of shape (batch_size, output_dim)
        """
        # Select top-k features based on importance
        topk_indices = torch.topk(self.feature_importance.abs(), self.k).indices
        
        # Create sparse mask
        mask = torch.zeros_like(x)
        mask[:, topk_indices] = 1.0
        
        # Apply mask and compute output
        sparse_x = x * mask
        return self.linear(sparse_x)

def generate_synthetic_sae_data(
    num_samples: int = 1000,
    num_features: int = 16384,
    num_classes: int = 26,  # For alphabet tasks
    feature_sparsity: float = 0.01
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Generate synthetic SAE activation data for testing.
    
    Args:
        num_samples: Number of samples to generate
        num_features: Number of SAE features
        num_classes: Number of output classes
        feature_sparsity: Fraction of active features per sample
    
    Returns:
        Tuple of (activations, labels)
    """
    # Generate sparse activations
    activations = torch.zeros(num_samples, num_features)
    
    for i in range(num_samples):
        # Randomly select active features
        num_active = int(num_features * feature_sparsity)
        active_indices = torch.randperm(num_features)[:num_active]
        
        # Set random activation values
        activations[i, active_indices] = torch.randn(num_active).abs()
    
    # Generate random labels
    labels = torch.randint(0, num_classes, (num_samples,))
    
    return activations, labels

def train_k_sparse_probe(
    train_activations: torch.Tensor,
    train_labels: torch.Tensor,
    k: int,
    num_epochs: int = 100,
    learning_rate: float = 0.01,
    l1_penalty: float = 0.001
) -> KSparseProbe:
    """
    Train a k-sparse probe on SAE activations.
    
    Args:
        train_activations: Training activations
        train_labels: Training labels
        k: Number of features to use
        num_epochs: Training epochs
        learning_rate: Learning rate
        l1_penalty: L1 regularization strength
    
    Returns:
        Trained k-sparse probe
    """
    input_dim = train_activations.shape[1]
    num_classes = len(torch.unique(train_labels))
    
    # Initialize probe
    probe = KSparseProbe(input_dim, num_classes, k)
    
    # Setup training
    optimizer = torch.optim.Adam(probe.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()
    
    print(f"Training {k}-sparse probe...")
    
    for epoch in range(num_epochs):
        # Forward pass
        outputs = probe(train_activations)
        loss = criterion(outputs, train_labels)
        
        # Add L1 regularization
        l1_loss = l1_penalty * probe.feature_importance.abs().sum()
        total_loss = loss + l1_loss
        
        # Backward pass
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 20 == 0:
            accuracy = (outputs.argmax(dim=1) == train_labels).float().mean()
            print(f"  Epoch {epoch+1}/{num_epochs}, Loss: {loss:.4f}, Accuracy: {accuracy:.4f}")
    
    return probe

def evaluate_probe(
    probe: KSparseProbe,
    test_activations: torch.Tensor,
    test_labels: torch.Tensor
) -> Dict[str, float]:
    """
    Evaluate a trained probe on test data.
    
    Args:
        probe: Trained probe model
        test_activations: Test activations
        test_labels: Test labels
    
    Returns:
        Dictionary of evaluation metrics
    """
    probe.eval()
    
    with torch.no_grad():
        outputs = probe(test_activations)
        predictions = outputs.argmax(dim=1)
        
        accuracy = (predictions == test_labels).float().mean().item()
        
        # Calculate per-class accuracy
        per_class_acc = []
        for class_idx in torch.unique(test_labels):
            class_mask = test_labels == class_idx
            if class_mask.sum() > 0:
                class_acc = (predictions[class_mask] == test_labels[class_mask]).float().mean().item()
                per_class_acc.append(class_acc)
    
    return {
        "accuracy": accuracy,
        "mean_per_class_accuracy": np.mean(per_class_acc) if per_class_acc else 0.0,
        "min_per_class_accuracy": np.min(per_class_acc) if per_class_acc else 0.0,
        "max_per_class_accuracy": np.max(per_class_acc) if per_class_acc else 0.0
    }

def run_k_sparse_analysis(
    train_activations: torch.Tensor,
    train_labels: torch.Tensor,
    test_activations: torch.Tensor,
    test_labels: torch.Tensor,
    k_values: List[int] = None
) -> Dict[int, Dict[str, float]]:
    """
    Run k-sparse probing analysis for multiple k values.
    
    Args:
        train_activations: Training SAE activations
        train_labels: Training labels
        test_activations: Test SAE activations
        test_labels: Test labels
        k_values: List of k values to test
    
    Returns:
        Dictionary mapping k to evaluation metrics
    """
    if k_values is None:
        k_values = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
    
    results = {}
    
    print("\nRunning k-sparse probing analysis...")
    print("=" * 50)
    
    for k in k_values:
        print(f"\nTraining probe with k={k}")
        
        # Train probe
        probe = train_k_sparse_probe(
            train_activations,
            train_labels,
            k=k,
            num_epochs=100
        )
        
        # Evaluate probe
        metrics = evaluate_probe(probe, test_activations, test_labels)
        results[k] = metrics
        
        print(f"  Test Accuracy: {metrics['accuracy']:.4f}")
        print(f"  Mean Per-Class Accuracy: {metrics['mean_per_class_accuracy']:.4f}")
    
    return results

def plot_k_sparse_results(results: Dict[int, Dict[str, float]], save_path: Optional[Path] = None):
    """
    Plot k-sparse probing results to visualize feature splitting.
    
    Args:
        results: Dictionary of k values to metrics
        save_path: Optional path to save the plot
    """
    k_values = sorted(results.keys())
    accuracies = [results[k]["accuracy"] for k in k_values]
    per_class_accs = [results[k]["mean_per_class_accuracy"] for k in k_values]
    
    plt.figure(figsize=(10, 6))
    
    # Plot accuracy vs k
    plt.subplot(1, 2, 1)
    plt.semilogx(k_values, accuracies, 'b-o', label='Overall Accuracy')
    plt.semilogx(k_values, per_class_accs, 'r--s', label='Mean Per-Class Accuracy')
    plt.xlabel('Number of Features (k)')
    plt.ylabel('Accuracy')
    plt.title('K-Sparse Probe Performance')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot accuracy improvement (derivative)
    plt.subplot(1, 2, 2)
    acc_improvements = [0] + [accuracies[i] - accuracies[i-1] for i in range(1, len(accuracies))]
    plt.bar(range(len(k_values)), acc_improvements)
    plt.xticks(range(len(k_values)), [str(k) for k in k_values], rotation=45)
    plt.xlabel('Number of Features (k)')
    plt.ylabel('Accuracy Improvement')
    plt.title('Marginal Accuracy Gain')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to {save_path}")
    
    plt.show()

def detect_feature_splitting(results: Dict[int, Dict[str, float]], threshold: float = 0.01) -> int:
    """
    Detect potential feature splitting based on k-sparse results.
    
    Feature splitting is indicated when multiple features are needed
    to achieve good performance, suggesting the information is distributed.
    
    Args:
        results: K-sparse probing results
        threshold: Minimum accuracy improvement to consider significant
    
    Returns:
        Estimated number of split features
    """
    k_values = sorted(results.keys())
    accuracies = [results[k]["accuracy"] for k in k_values]
    
    # Find the k where accuracy plateaus
    splitting_k = 1
    for i in range(1, len(accuracies)):
        improvement = accuracies[i] - accuracies[i-1]
        if improvement < threshold:
            splitting_k = k_values[i-1]
            break
    
    print(f"\nFeature Splitting Analysis:")
    print(f"  Estimated number of split features: {splitting_k}")
    print(f"  Accuracy with 1 feature: {results[k_values[0]]['accuracy']:.4f}")
    print(f"  Accuracy with {splitting_k} features: {results[splitting_k]['accuracy']:.4f}")
    
    return splitting_k

def main():
    """
    Main function to demonstrate k-sparse probing for feature splitting detection.
    """
    print("K-Sparse Probing for Feature Splitting Detection")
    print("=" * 50)
    
    # Configuration
    num_train_samples = 1000
    num_test_samples = 200
    num_features = 16384  # Typical SAE width
    num_classes = 26  # Alphabet classification task
    
    # Step 1: Generate synthetic data (replace with real SAE activations)
    print("\nGenerating synthetic SAE activation data...")
    train_activations, train_labels = generate_synthetic_sae_data(
        num_samples=num_train_samples,
        num_features=num_features,
        num_classes=num_classes
    )
    
    test_activations, test_labels = generate_synthetic_sae_data(
        num_samples=num_test_samples,
        num_features=num_features,
        num_classes=num_classes
    )
    
    print(f"  Training samples: {train_activations.shape}")
    print(f"  Test samples: {test_activations.shape}")
    
    # Step 2: Run k-sparse analysis
    k_values = [1, 2, 4, 8, 16, 32, 64, 128, 256]
    results = run_k_sparse_analysis(
        train_activations=train_activations,
        train_labels=train_labels,
        test_activations=test_activations,
        test_labels=test_labels,
        k_values=k_values
    )
    
    # Step 3: Detect feature splitting
    splitting_k = detect_feature_splitting(results)
    
    # Step 4: Visualize results
    plot_path = Path("k_sparse_results.png")
    plot_k_sparse_results(results, save_path=plot_path)
    
    # Step 5: Summary
    print("\n" + "=" * 50)
    print("Analysis Complete!")
    print(f"Feature splitting detected: {splitting_k > 1}")
    if splitting_k > 1:
        print(f"Information appears to be split across ~{splitting_k} features")
    else:
        print("No significant feature splitting detected")

if __name__ == "__main__":
    main()
```

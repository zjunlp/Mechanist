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

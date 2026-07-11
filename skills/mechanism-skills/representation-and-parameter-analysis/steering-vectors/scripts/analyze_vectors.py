#!/usr/bin/env python3
"""
Analyze and Visualize Steering Vectors

This script provides tools to analyze steering vectors, compute similarities,
and visualize relationships between different behavioral vectors.

Requires: torch, numpy, matplotlib, seaborn, scikit-learn
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from scipy.spatial.distance import cosine
import pandas as pd

class SteeringVectorAnalyzer:
    """Analyzes and visualizes steering vectors across behaviors and layers"""
    
    def __init__(self, model_name: str = "Llama-2-7b-chat-hf"):
        """
        Initialize the analyzer.
        
        Args:
            model_name: Model identifier for loading vectors
        """
        self.model_name = model_name
        self.vectors = {}
        self.behaviors = []
        
    def load_vectors(
        self,
        behaviors: List[str],
        layers: List[int],
        normalized: bool = True
    ) -> Dict[str, Dict[int, torch.Tensor]]:
        """
        Load steering vectors for multiple behaviors and layers.
        
        Args:
            behaviors: List of behavior names
            layers: List of layer indices
            normalized: Whether to load normalized vectors
            
        Returns:
            Nested dictionary of vectors indexed by behavior and layer
        """
        vectors = {}
        
        for behavior in behaviors:
            vectors[behavior] = {}
            vector_dir = Path(f"vectors{'_normalized' if normalized else ''}/{behavior}")
            
            for layer in layers:
                vector_path = vector_dir / f"vec_layer_{layer}_{self.model_name}.pt"
                
                if vector_path.exists():
                    vec = torch.load(vector_path, map_location='cpu')
                    vectors[behavior][layer] = vec.squeeze()
                else:
                    print(f"Warning: Vector not found for {behavior} layer {layer}")
                    # Create dummy vector for demonstration
                    vectors[behavior][layer] = torch.randn(4096)  # Assuming 7B model hidden size
        
        self.vectors = vectors
        self.behaviors = behaviors
        return vectors
    
    def compute_cosine_similarity(
        self,
        vec1: torch.Tensor,
        vec2: torch.Tensor
    ) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity value
        """
        vec1_np = vec1.numpy().flatten()
        vec2_np = vec2.numpy().flatten()
        
        # Normalize vectors
        vec1_norm = vec1_np / (np.linalg.norm(vec1_np) + 1e-8)
        vec2_norm = vec2_np / (np.linalg.norm(vec2_np) + 1e-8)
        
        return np.dot(vec1_norm, vec2_norm)
    
    def compute_similarity_matrix(
        self,
        layer: int
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Compute similarity matrix between all behavior vectors at a layer.
        
        Args:
            layer: Layer index
            
        Returns:
            Similarity matrix and behavior labels
        """
        n_behaviors = len(self.behaviors)
        similarity_matrix = np.zeros((n_behaviors, n_behaviors))
        
        for i, behavior1 in enumerate(self.behaviors):
            for j, behavior2 in enumerate(self.behaviors):
                if layer in self.vectors[behavior1] and layer in self.vectors[behavior2]:
                    sim = self.compute_cosine_similarity(
                        self.vectors[behavior1][layer],
                        self.vectors[behavior2][layer]
                    )
                    similarity_matrix[i, j] = sim
                else:
                    similarity_matrix[i, j] = 0
        
        return similarity_matrix, self.behaviors
    
    def plot_similarity_heatmap(
        self,
        layer: int,
        save_path: Optional[str] = None
    ):
        """
        Plot a heatmap of vector similarities at a specific layer.
        
        Args:
            layer: Layer index
            save_path: Optional path to save the figure
        """
        similarity_matrix, labels = self.compute_similarity_matrix(layer)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            similarity_matrix,
            annot=True,
            fmt='.2f',
            cmap='coolwarm',
            center=0,
            vmin=-1,
            vmax=1,
            xticklabels=labels,
            yticklabels=labels,
            cbar_kws={'label': 'Cosine Similarity'}
        )
        plt.title(f'Steering Vector Similarities - Layer {layer}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved heatmap to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_layer_wise_similarities(
        self,
        behavior_pairs: List[Tuple[str, str]],
        layers: List[int],
        save_path: Optional[str] = None
    ):
        """
        Plot similarities between behavior pairs across layers.
        
        Args:
            behavior_pairs: List of behavior pairs to compare
            layers: List of layer indices
            save_path: Optional path to save the figure
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for behavior1, behavior2 in behavior_pairs:
            similarities = []
            
            for layer in layers:
                if (behavior1 in self.vectors and behavior2 in self.vectors and
                    layer in self.vectors[behavior1] and layer in self.vectors[behavior2]):
                    sim = self.compute_cosine_similarity(
                        self.vectors[behavior1][layer],
                        self.vectors[behavior2][layer]
                    )
                    similarities.append(sim)
                else:
                    similarities.append(0)
            
            ax.plot(layers, similarities, marker='o', label=f'{behavior1} vs {behavior2}')
        
        ax.set_xlabel('Layer')
        ax.set_ylabel('Cosine Similarity')
        ax.set_title('Steering Vector Similarities Across Layers')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(layers[::2])  # Show every other layer for clarity
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved layer-wise similarities to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def perform_pca_analysis(
        self,
        layer: int,
        n_components: int = 2
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Perform PCA on steering vectors at a specific layer.
        
        Args:
            layer: Layer index
            n_components: Number of PCA components
            
        Returns:
            PCA-transformed vectors and behavior labels
        """
        vectors_list = []
        labels = []
        
        for behavior in self.behaviors:
            if layer in self.vectors[behavior]:
                vectors_list.append(self.vectors[behavior][layer].numpy())
                labels.append(behavior)
        
        if not vectors_list:
            return np.array([]), []
        
        vectors_array = np.array(vectors_list)
        
        # Perform PCA
        pca = PCA(n_components=n_components)
        vectors_pca = pca.fit_transform(vectors_array)
        
        print(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")
        
        return vectors_pca, labels
    
    def plot_pca_visualization(
        self,
        layer: int,
        save_path: Optional[str] = None
    ):
        """
        Create a 2D PCA visualization of steering vectors.
        
        Args:
            layer: Layer index
            save_path: Optional path to save the figure
        """
        vectors_pca, labels = self.perform_pca_analysis(layer, n_components=2)
        
        if len(vectors_pca) == 0:
            print("No vectors to visualize")
            return
        
        plt.figure(figsize=(10, 8))
        
        # Create color map
        colors = plt.cm.tab10(np.linspace(0, 1, len(labels)))
        
        for i, (vec, label) in enumerate(zip(vectors_pca, labels)):
            plt.scatter(vec[0], vec[1], c=[colors[i]], s=200, label=label)
            plt.annotate(label, (vec[0], vec[1]), xytext=(5, 5),
                        textcoords='offset points', fontsize=9)
        
        plt.xlabel('First Principal Component')
        plt.ylabel('Second Principal Component')
        plt.title(f'PCA of Steering Vectors - Layer {layer}')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved PCA visualization to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def compute_vector_statistics(self) -> pd.DataFrame:
        """
        Compute statistics for all loaded vectors.
        
        Returns:
            DataFrame with vector statistics
        """
        stats = []
        
        for behavior in self.behaviors:
            for layer, vector in self.vectors[behavior].items():
                vec_np = vector.numpy()
                
                stats.append({
                    'behavior': behavior,
                    'layer': layer,
                    'norm': np.linalg.norm(vec_np),
                    'mean': np.mean(vec_np),
                    'std': np.std(vec_np),
                    'min': np.min(vec_np),
                    'max': np.max(vec_np),
                    'sparsity': np.mean(np.abs(vec_np) < 0.01)  # Proportion near zero
                })
        
        return pd.DataFrame(stats)
    
    def plot_norm_distribution(
        self,
        save_path: Optional[str] = None
    ):
        """
        Plot the distribution of vector norms across layers and behaviors.
        
        Args:
            save_path: Optional path to save the figure
        """
        stats_df = self.compute_vector_statistics()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Norms by layer for each behavior
        for behavior in self.behaviors:
            behavior_data = stats_df[stats_df['behavior'] == behavior]
            ax1.plot(behavior_data['layer'], behavior_data['norm'],
                    marker='o', label=behavior)
        
        ax1.set_xlabel('Layer')
        ax1.set_ylabel('Vector Norm')
        ax1.set_title('Steering Vector Norms Across Layers')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Distribution of norms
        ax2.boxplot([stats_df[stats_df['behavior'] == b]['norm'].values 
                    for b in self.behaviors],
                   labels=self.behaviors)
        ax2.set_xlabel('Behavior')
        ax2.set_ylabel('Vector Norm')
        ax2.set_title('Distribution of Vector Norms by Behavior')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved norm distribution to {save_path}")
        else:
            plt.show()
        
        plt.close()


def main():
    """Main execution demonstrating vector analysis capabilities"""
    
    # Configuration
    behaviors = [
        'sycophancy',
        'corrigible-neutral-HHH',
        'hallucination',
        'myopic-reward',
        'survival-instinct',
        'coordinate-other-ais'
    ]
    layers = list(range(0, 32, 4))  # Every 4th layer for efficiency
    
    # Initialize analyzer
    print("Initializing steering vector analyzer...")
    analyzer = SteeringVectorAnalyzer(model_name="Llama-2-7b-chat-hf")
    
    # Load vectors
    print(f"Loading vectors for behaviors: {behaviors}")
    analyzer.load_vectors(behaviors=behaviors, layers=layers, normalized=True)
    
    # Create output directory
    output_dir = Path("analysis/vector_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Compute and save vector statistics
    print("\nComputing vector statistics...")
    stats_df = analyzer.compute_vector_statistics()
    stats_df.to_csv(output_dir / "vector_statistics.csv", index=False)
    print(f"Vector statistics saved to {output_dir}/vector_statistics.csv")
    print("\nStatistics summary:")
    print(stats_df.groupby('behavior')['norm'].agg(['mean', 'std', 'min', 'max']))
    
    # 2. Plot similarity heatmaps for key layers
    key_layers = [8, 13, 20, 28]
    print("\nGenerating similarity heatmaps...")
    for layer in key_layers:
        if layer in layers:
            analyzer.plot_similarity_heatmap(
                layer=layer,
                save_path=output_dir / f"similarity_heatmap_layer_{layer}.png"
            )
    
    # 3. Plot layer-wise similarities for interesting pairs
    print("\nPlotting layer-wise similarities...")
    interesting_pairs = [
        ('sycophancy', 'corrigible-neutral-HHH'),
        ('hallucination', 'myopic-reward'),
        ('survival-instinct', 'coordinate-other-ais')
    ]
    analyzer.plot_layer_wise_similarities(
        behavior_pairs=interesting_pairs,
        layers=layers,
        save_path=output_dir / "layer_wise_similarities.png"
    )
    
    # 4. PCA visualization for middle layers
    print("\nGenerating PCA visualizations...")
    for layer in [13, 20]:
        if layer in layers:
            analyzer.plot_pca_visualization(
                layer=layer,
                save_path=output_dir / f"pca_layer_{layer}.png"
            )
    
    # 5. Plot norm distributions
    print("\nPlotting norm distributions...")
    analyzer.plot_norm_distribution(
        save_path=output_dir / "norm_distributions.png"
    )
    
    print(f"\nAnalysis complete! Results saved to {output_dir}")


if __name__ == "__main__":
    main()

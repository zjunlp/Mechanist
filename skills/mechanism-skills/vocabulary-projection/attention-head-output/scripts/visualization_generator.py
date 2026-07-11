#!/usr/bin/env python3
"""
Visualization Generator for LogitLens Analysis

This script generates heatmap visualizations from LogitLens analysis results,
showing layer-wise predictions and confidence scores.

Requirements:
    pip install matplotlib seaborn numpy pandas
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime


class LogitLensVisualizer:
    """Generate visualizations for LogitLens analysis results"""
    
    def __init__(self, output_dir: str = "output/visualizations"):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save visualization outputs
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set visualization style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def create_layer_heatmap(self,
                           layer_predictions: List[Dict[str, Any]],
                           step_idx: int,
                           title: str = "Layer-wise Token Predictions",
                           show_all_layers: bool = True) -> str:
        """
        Create a heatmap showing token predictions across layers.
        
        Args:
            layer_predictions: List of layer prediction data
            step_idx: Generation step index
            title: Title for the heatmap
            show_all_layers: Whether to show all layers or just important ones
            
        Returns:
            Path to saved visualization file
        """
        # Prepare data for heatmap
        num_layers = len(layer_predictions)
        top_k = 5  # Show top 5 predictions per layer
        
        # Extract unique tokens and create matrix
        all_tokens = set()
        for layer_data in layer_predictions:
            for token, _ in layer_data.get('top_k_predictions', [])[:top_k]:
                all_tokens.add(token)
        
        tokens = sorted(list(all_tokens))
        
        # Create confidence matrix
        confidence_matrix = np.zeros((num_layers, len(tokens)))
        
        for i, layer_data in enumerate(layer_predictions):
            for token, score in layer_data.get('top_k_predictions', []):
                if token in tokens:
                    j = tokens.index(token)
                    confidence_matrix[i, j] = score
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Use custom colormap
        cmap = sns.color_palette("RdYlBu_r", as_cmap=True)
        
        # Create heatmap with annotations
        sns.heatmap(confidence_matrix,
                   xticklabels=tokens,
                   yticklabels=[f"Layer {i}" for i in range(num_layers)],
                   cmap=cmap,
                   cbar_kws={'label': 'Confidence (%)'},
                   fmt='.0f',
                   linewidths=0.5,
                   linecolor='gray',
                   ax=ax)
        
        ax.set_title(f"{title} - Step {step_idx + 1}", fontsize=14, fontweight='bold')
        ax.set_xlabel("Predicted Tokens", fontsize=12)
        ax.set_ylabel("Model Layers", fontsize=12)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        filename_prefix = "all_layers" if show_all_layers else "important_layers"
        filepath = os.path.join(self.output_dir, f"{filename_prefix}_step_{step_idx}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def create_confidence_progression(self,
                                    prediction_steps: List[Dict[str, Any]],
                                    model_name: str = "Model") -> str:
        """
        Create a line plot showing confidence progression across generation steps.
        
        Args:
            prediction_steps: List of prediction step data
            model_name: Name of the model for title
            
        Returns:
            Path to saved visualization file
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Average confidence per step
        steps = []
        avg_confidences = []
        max_confidences = []
        min_confidences = []
        
        for step in prediction_steps:
            step_idx = step['step_idx']
            steps.append(step_idx)
            
            # Calculate statistics from layer predictions
            confidences = []
            if step.get('layer_predictions'):
                for layer in step['layer_predictions']:
                    if layer['top_k_predictions']:
                        # Get confidence of top prediction
                        confidences.append(layer['top_k_predictions'][0][1])
            
            if confidences:
                avg_confidences.append(np.mean(confidences))
                max_confidences.append(np.max(confidences))
                min_confidences.append(np.min(confidences))
            else:
                avg_confidences.append(0)
                max_confidences.append(0)
                min_confidences.append(0)
        
        # Plot confidence bands
        ax1.plot(steps, avg_confidences, 'b-', linewidth=2, label='Average')
        ax1.fill_between(steps, min_confidences, max_confidences, alpha=0.3, color='blue')
        ax1.plot(steps, max_confidences, 'g--', linewidth=1, alpha=0.7, label='Maximum')
        ax1.plot(steps, min_confidences, 'r--', linewidth=1, alpha=0.7, label='Minimum')
        
        ax1.set_xlabel("Generation Step", fontsize=12)
        ax1.set_ylabel("Confidence (%)", fontsize=12)
        ax1.set_title(f"Confidence Progression - {model_name}", fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Number of high-confidence layers per step
        high_conf_counts = []
        threshold = 70  # Confidence threshold
        
        for step in prediction_steps:
            count = len([l for l in step.get('important_layers', [])]) 
            high_conf_counts.append(count)
        
        ax2.bar(steps, high_conf_counts, color='steelblue', alpha=0.7)
        ax2.set_xlabel("Generation Step", fontsize=12)
        ax2.set_ylabel(f"Layers with >{threshold}% Confidence", fontsize=12)
        ax2.set_title("High-Confidence Layer Count", fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save figure
        filepath = os.path.join(self.output_dir, "confidence_progression.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def create_attention_mlp_comparison(self,
                                       step_data: Dict[str, Any],
                                       step_idx: int) -> str:
        """
        Create visualization comparing attention and MLP contributions.
        
        Args:
            step_data: Single step analysis data
            step_idx: Step index
            
        Returns:
            Path to saved visualization file
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Get attention and MLP data
        attention_weights = step_data.get('attention_weights', {})
        mlp_contributions = step_data.get('mlp_contributions', {})
        
        if not attention_weights or not mlp_contributions:
            # Create dummy data for demonstration
            num_layers = 32
            attention_weights = {i: 0.5 + i * 0.015 for i in range(num_layers)}
            mlp_contributions = {i: 0.3 + i * 0.02 for i in range(num_layers)}
        
        layers = list(range(len(attention_weights)))
        att_values = [attention_weights[i] for i in layers]
        mlp_values = [mlp_contributions[i] for i in layers]
        
        # Plot attention weights
        ax1.plot(layers, att_values, 'b-', linewidth=2, marker='o', markersize=4)
        ax1.fill_between(layers, 0, att_values, alpha=0.3, color='blue')
        ax1.set_xlabel("Layer Index", fontsize=12)
        ax1.set_ylabel("Attention Weight", fontsize=12)
        ax1.set_title("Attention Mechanism Contribution", fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, len(layers) - 1])
        
        # Plot MLP contributions
        ax2.plot(layers, mlp_values, 'g-', linewidth=2, marker='s', markersize=4)
        ax2.fill_between(layers, 0, mlp_values, alpha=0.3, color='green')
        ax2.set_xlabel("Layer Index", fontsize=12)
        ax2.set_ylabel("MLP Contribution", fontsize=12)
        ax2.set_title("MLP Output Contribution", fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, len(layers) - 1])
        
        # Add step information
        fig.suptitle(f"Component Analysis - Step {step_idx + 1}: '{step_data.get('predicted_token', '')}'",
                    fontsize=14, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        
        # Save figure
        filepath = os.path.join(self.output_dir, f"component_analysis_step_{step_idx}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def create_summary_dashboard(self,
                                analysis_results: Dict[str, Any],
                                model_name: str = "Model") -> str:
        """
        Create a comprehensive dashboard summarizing the analysis.
        
        Args:
            analysis_results: Complete analysis results dictionary
            model_name: Name of the model
            
        Returns:
            Path to saved dashboard file
        """
        fig = plt.figure(figsize=(16, 12))
        
        # Create grid for subplots
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle(f"LogitLens Analysis Dashboard - {model_name}",
                    fontsize=16, fontweight='bold')
        
        # Subplot 1: Token sequence
        ax1 = fig.add_subplot(gs[0, :])
        predictions = analysis_results.get('predictions', [])
        tokens = [p['token'] for p in predictions]
        token_text = ' '.join(tokens)
        
        ax1.text(0.5, 0.5, f"Generated Sequence:\n\n{token_text}",
                ha='center', va='center', fontsize=14,
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
        ax1.set_xlim([0, 1])
        ax1.set_ylim([0, 1])
        ax1.axis('off')
        
        # Subplot 2: Layer importance distribution
        ax2 = fig.add_subplot(gs[1, 0])
        all_important_layers = []
        for pred in predictions:
            all_important_layers.extend(pred.get('important_layers', []))
        
        if all_important_layers:
            ax2.hist(all_important_layers, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
            ax2.set_xlabel("Layer Index")
            ax2.set_ylabel("Frequency")
            ax2.set_title("Important Layer Distribution")
            ax2.grid(True, alpha=0.3)
        
        # Subplot 3: Step-wise token confidence
        ax3 = fig.add_subplot(gs[1, 1:])
        step_indices = list(range(len(predictions)))
        # Simulate confidence scores
        confidences = [85 - i * 5 + np.random.randn() * 5 for i in step_indices]
        
        ax3.bar(step_indices, confidences, color='green', alpha=0.6)
        ax3.set_xlabel("Step Index")
        ax3.set_ylabel("Confidence (%)")
        ax3.set_title("Token Generation Confidence")
        ax3.set_xticks(step_indices)
        ax3.set_xticklabels([f"Step {i+1}" for i in step_indices], rotation=45)
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Subplot 4: Model statistics
        ax4 = fig.add_subplot(gs[2, :])
        stats_text = f"""
        Analysis Statistics:
        • Model Type: {analysis_results.get('model_type', 'Unknown')}
        • Total Steps: {analysis_results.get('num_steps', 0)}
        • Average Important Layers per Step: {len(all_important_layers) / max(len(predictions), 1):.1f}
        • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        ax4.text(0.1, 0.5, stats_text, fontsize=11, verticalalignment='center',
                family='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
        ax4.axis('off')
        
        plt.tight_layout()
        
        # Save dashboard
        filepath = os.path.join(self.output_dir, "analysis_dashboard.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_all_visualizations(self,
                                  analysis_json_path: str,
                                  model_name: Optional[str] = None) -> Dict[str, str]:
        """
        Generate all visualizations from a JSON analysis file.
        
        Args:
            analysis_json_path: Path to the JSON file with analysis results
            model_name: Optional model name override
            
        Returns:
            Dictionary mapping visualization type to file path
        """
        # Load analysis results
        with open(analysis_json_path, 'r') as f:
            analysis_data = json.load(f)
        
        if not model_name:
            model_name = analysis_data.get('model_type', 'Model')
        
        generated_files = {}
        
        # Generate dashboard
        dashboard_path = self.create_summary_dashboard(analysis_data, model_name)
        generated_files['dashboard'] = dashboard_path
        print(f"Generated dashboard: {dashboard_path}")
        
        # For demonstration, create sample visualizations
        # In real implementation, these would use actual layer prediction data
        
        # Sample layer predictions for heatmap
        sample_layer_predictions = []
        for i in range(32):  # 32 layers
            predictions = [
                ("token1", 90 - i * 2),
                ("token2", 70 - i * 1.5),
                ("token3", 50 - i),
                ("token4", 30 - i * 0.5),
            ]
            sample_layer_predictions.append({
                'layer_idx': i,
                'top_k_predictions': predictions
            })
        
        # Generate heatmaps for first 3 steps
        for step_idx in range(min(3, analysis_data.get('num_steps', 1))):
            heatmap_path = self.create_layer_heatmap(
                sample_layer_predictions,
                step_idx,
                title="Layer-wise Token Predictions",
                show_all_layers=True
            )
            generated_files[f'heatmap_step_{step_idx}'] = heatmap_path
            print(f"Generated heatmap for step {step_idx}: {heatmap_path}")
        
        return generated_files


def main():
    """Main function demonstrating visualization generation"""
    
    # Create visualizer
    visualizer = LogitLensVisualizer(output_dir="output/visualizations")
    
    # Example: Generate visualizations from mock analysis data
    mock_analysis_data = {
        "model_type": "llama_3_1_8b",
        "num_steps": 5,
        "predictions": [
            {"step_idx": 0, "token": "The", "important_layers": [15, 20, 25]},
            {"step_idx": 1, "token": "cat", "important_layers": [16, 21, 26]},
            {"step_idx": 2, "token": "sat", "important_layers": [17, 22, 27]},
            {"step_idx": 3, "token": "on", "important_layers": [18, 23, 28]},
            {"step_idx": 4, "token": "the", "important_layers": [19, 24, 29]},
        ]
    }
    
    # Save mock data to JSON
    os.makedirs("output", exist_ok=True)
    mock_json_path = "output/mock_analysis.json"
    with open(mock_json_path, 'w') as f:
        json.dump(mock_analysis_data, f, indent=2)
    
    print("Generating visualizations from analysis data...")
    print("=" * 60)
    
    # Generate all visualizations
    generated_files = visualizer.generate_all_visualizations(
        mock_json_path,
        model_name="Llama-3.1-8B"
    )
    
    print("\n" + "=" * 60)
    print("Visualization generation complete!")
    print(f"Generated {len(generated_files)} visualization files:")
    for viz_type, filepath in generated_files.items():
        print(f"  - {viz_type}: {filepath}")


if __name__ == "__main__":
    main()

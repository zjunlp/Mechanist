---
name: residual-stream-state
description: Use this skill when working with transformer model interpretability, analyzing layer-by-layer predictions, training tuned lenses to understand intermediate representations, or peeking into iterative computations of transformers
---

## Demo Scripts

### `scripts/analyze_predictions.py`

```python
#!/usr/bin/env python3
"""
Analyze Layer-wise Predictions using Tuned Lens

This script demonstrates how to use a tuned lens to analyze how predictions
evolve through the layers of a transformer model, providing insights into
the model's iterative computation process.

Requires: pip install tuned-lens torch transformers matplotlib
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class PredictionTrajectory:
    """
    Represents the evolution of predictions through transformer layers.
    """
    text: str
    tokens: List[str]
    layer_predictions: Dict[int, np.ndarray]  # layer_idx -> probabilities
    final_prediction: np.ndarray
    top_k_tokens: Dict[int, List[Tuple[str, float]]]  # layer_idx -> [(token, prob)]


class TunedLensAnalyzer:
    """
    Analyzer for understanding transformer predictions using tuned lenses.
    """
    
    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Initialize the analyzer with a model.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run analysis on
        """
        self.device = device
        self.model_name = model_name
        
        # Load model and tokenizer
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Get model configuration
        self.n_layers = (
            self.model.config.n_layer 
            if hasattr(self.model.config, 'n_layer') 
            else self.model.config.num_hidden_layers
        )
        self.hidden_size = self.model.config.hidden_size
        self.vocab_size = self.model.config.vocab_size
        
        # We'll use the unembedding matrix as a simple lens for demonstration
        # In practice, you would load trained tuned lens translators
        self.use_simple_lens = True
        
    def get_unembedding_matrix(self) -> torch.Tensor:
        """
        Get the unembedding matrix from the model.
        
        Returns:
            Unembedding weight matrix
        """
        if hasattr(self.model, 'lm_head'):
            return self.model.lm_head.weight
        elif hasattr(self.model, 'embed_out'):
            return self.model.embed_out.weight
        else:
            # For GPT-2, the embedding and unembedding matrices are tied
            return self.model.transformer.wte.weight.T
    
    def apply_lens(
        self,
        hidden_state: torch.Tensor,
        layer_idx: int
    ) -> torch.Tensor:
        """
        Apply lens (tuned or simple) to hidden state.
        
        Args:
            hidden_state: Hidden state from layer
            layer_idx: Index of the layer
            
        Returns:
            Logits after applying lens
        """
        if self.use_simple_lens:
            # Simple logit lens: directly unembed
            unembedding = self.get_unembedding_matrix()
            
            # Handle dimension mismatch if necessary
            if hidden_state.shape[-1] != unembedding.shape[1]:
                # Project to correct dimension (simplified)
                logits = torch.matmul(hidden_state, unembedding[:hidden_state.shape[-1]].T)
            else:
                logits = torch.matmul(hidden_state, unembedding.T)
        else:
            # Here you would apply trained tuned lens translators
            # logits = self.translators[layer_idx](hidden_state)
            raise NotImplementedError("Load trained translators for tuned lens")
            
        return logits
    
    def analyze_text(
        self,
        text: str,
        top_k: int = 5
    ) -> PredictionTrajectory:
        """
        Analyze how predictions evolve through layers for given text.
        
        Args:
            text: Input text to analyze
            top_k: Number of top predictions to track
            
        Returns:
            PredictionTrajectory object with analysis results
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors='pt').to(self.device)
        input_ids = inputs['input_ids']
        
        # Get all hidden states
        with torch.no_grad():
            outputs = self.model(
                input_ids,
                output_hidden_states=True,
                return_dict=True
            )
        
        hidden_states = outputs.hidden_states[1:]  # Skip embedding layer
        final_logits = outputs.logits
        
        # Decode tokens
        tokens = [self.tokenizer.decode([tid]) for tid in input_ids[0]]
        
        # Analyze predictions at each layer
        layer_predictions = {}
        top_k_tokens = {}
        
        for layer_idx, hidden_state in enumerate(hidden_states):
            # Apply lens to get predictions
            logits = self.apply_lens(hidden_state, layer_idx)
            probs = torch.nn.functional.softmax(logits, dim=-1)
            
            # Store probabilities for last token
            layer_predictions[layer_idx] = probs[0, -1].cpu().numpy()
            
            # Get top-k predictions
            top_probs, top_indices = torch.topk(probs[0, -1], top_k)
            top_k_tokens[layer_idx] = [
                (self.tokenizer.decode([idx.item()]), prob.item())
                for idx, prob in zip(top_indices, top_probs)
            ]
        
        # Get final prediction
        final_probs = torch.nn.functional.softmax(final_logits[0, -1], dim=-1)
        
        return PredictionTrajectory(
            text=text,
            tokens=tokens,
            layer_predictions=layer_predictions,
            final_prediction=final_probs.cpu().numpy(),
            top_k_tokens=top_k_tokens
        )
    
    def plot_prediction_trajectory(
        self,
        trajectory: PredictionTrajectory,
        target_tokens: Optional[List[str]] = None,
        save_path: Optional[Path] = None
    ):
        """
        Plot how predictions for specific tokens evolve through layers.
        
        Args:
            trajectory: Prediction trajectory to plot
            target_tokens: Specific tokens to track (if None, use top final predictions)
            save_path: Path to save the plot
        """
        if target_tokens is None:
            # Use top 5 tokens from final prediction
            final_probs = trajectory.final_prediction
            top_indices = np.argsort(final_probs)[-5:][::-1]
            target_tokens = [self.tokenizer.decode([idx]) for idx in top_indices]
        
        # Get token IDs for target tokens
        token_ids = [
            self.tokenizer.encode(token, add_special_tokens=False)[0]
            for token in target_tokens
        ]
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        layers = list(trajectory.layer_predictions.keys())
        
        for token, token_id in zip(target_tokens, token_ids):
            probs = [
                trajectory.layer_predictions[layer][token_id]
                for layer in layers
            ]
            ax.plot(layers, probs, marker='o', label=f'"{token}"')
        
        ax.set_xlabel('Layer')
        ax.set_ylabel('Probability')
        ax.set_title(f'Prediction Trajectory for: "{trajectory.text}"')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()
    
    def compare_layer_predictions(
        self,
        trajectory: PredictionTrajectory,
        layers_to_compare: Optional[List[int]] = None
    ) -> Dict[int, Dict[str, float]]:
        """
        Compare top predictions across different layers.
        
        Args:
            trajectory: Prediction trajectory
            layers_to_compare: Specific layers to compare (if None, use first, middle, last)
            
        Returns:
            Dictionary mapping layer indices to top predictions
        """
        if layers_to_compare is None:
            layers_to_compare = [0, self.n_layers // 2, self.n_layers - 1]
        
        comparison = {}
        
        for layer_idx in layers_to_compare:
            if layer_idx in trajectory.top_k_tokens:
                comparison[layer_idx] = {
                    token: prob 
                    for token, prob in trajectory.top_k_tokens[layer_idx]
                }
        
        return comparison
    
    def entropy_analysis(
        self,
        trajectory: PredictionTrajectory
    ) -> Dict[int, float]:
        """
        Compute entropy of predictions at each layer.
        
        Args:
            trajectory: Prediction trajectory
            
        Returns:
            Dictionary mapping layer indices to entropy values
        """
        entropies = {}
        
        for layer_idx, probs in trajectory.layer_predictions.items():
            # Add small epsilon to avoid log(0)
            probs = probs + 1e-10
            entropy = -np.sum(probs * np.log(probs))
            entropies[layer_idx] = entropy
        
        return entropies


def main():
    """
    Main function demonstrating tuned lens analysis capabilities.
    """
    # Initialize analyzer
    analyzer = TunedLensAnalyzer(model_name="gpt2")
    
    # Example texts to analyze
    test_texts = [
        "The capital of France is",
        "Two plus two equals",
        "The sky is usually",
        "Water freezes at zero degrees"
    ]
    
    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"Analyzing: '{text}'")
        print('='*60)
        
        # Analyze text
        trajectory = analyzer.analyze_text(text, top_k=5)
        
        # Compare predictions across layers
        comparison = analyzer.compare_layer_predictions(trajectory)
        
        print("\nTop predictions at different layers:")
        for layer_idx, predictions in comparison.items():
            print(f"\nLayer {layer_idx}:")
            for token, prob in list(predictions.items())[:3]:
                print(f"  {token:15s}: {prob:.4f}")
        
        # Compute entropy evolution
        entropies = analyzer.entropy_analysis(trajectory)
        
        print("\nEntropy evolution:")
        for layer_idx in [0, len(entropies)//2, len(entropies)-1]:
            print(f"  Layer {layer_idx:2d}: {entropies[layer_idx]:.4f}")
        
        # Plot trajectory for first example
        if text == test_texts[0]:
            analyzer.plot_prediction_trajectory(
                trajectory,
                save_path=Path("prediction_trajectory.png")
            )
    
    # Save analysis results
    results = {
        "model": analyzer.model_name,
        "n_layers": analyzer.n_layers,
        "analyses": []
    }
    
    for text in test_texts[:2]:  # Save first two for brevity
        trajectory = analyzer.analyze_text(text)
        results["analyses"].append({
            "text": text,
            "final_top_tokens": trajectory.top_k_tokens[analyzer.n_layers - 1]
        })
    
    with open("analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nAnalysis complete! Results saved to analysis_results.json")


if __name__ == "__main__":
    main()
```

### `scripts/train_tuned_lens.py`

```python
#!/usr/bin/env python3
"""
Train a Tuned Lens for Transformer Model Interpretability

This script demonstrates how to train a tuned lens for a transformer model,
allowing you to peek at intermediate layer predictions and understand how
the model builds its predictions layer-by-layer.

Requires: pip install tuned-lens torch transformers datasets
"""

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TunedLensTrainer:
    """
    A trainer for tuned lenses that learn to predict final outputs
    from intermediate transformer representations.
    """
    
    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        learning_rate: float = 1e-3,
        batch_size: int = 8
    ):
        """
        Initialize the tuned lens trainer.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run training on
            learning_rate: Learning rate for optimizer
            batch_size: Batch size for training
        """
        self.device = device
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        
        # Load model and tokenizer
        logger.info(f"Loading model: {model_name}")
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Get model configuration
        self.n_layers = self.model.config.n_layer if hasattr(self.model.config, 'n_layer') else self.model.config.num_hidden_layers
        self.hidden_size = self.model.config.hidden_size
        self.vocab_size = self.model.config.vocab_size
        
        # Initialize affine translators for each layer
        self.translators = self._init_translators()
        
    def _init_translators(self) -> torch.nn.ModuleList:
        """
        Initialize affine translators for each layer.
        
        Returns:
            ModuleList of linear layers (affine translators)
        """
        translators = torch.nn.ModuleList([
            torch.nn.Linear(self.hidden_size, self.vocab_size, bias=True)
            for _ in range(self.n_layers)
        ]).to(self.device)
        
        # Initialize with small random weights
        for translator in translators:
            torch.nn.init.normal_(translator.weight, std=0.02)
            torch.nn.init.zeros_(translator.bias)
            
        return translators
    
    def extract_hidden_states(
        self, 
        input_ids: torch.Tensor
    ) -> Tuple[List[torch.Tensor], torch.Tensor]:
        """
        Extract hidden states from all layers of the model.
        
        Args:
            input_ids: Input token IDs
            
        Returns:
            Tuple of (list of hidden states, final logits)
        """
        with torch.no_grad():
            outputs = self.model(
                input_ids,
                output_hidden_states=True,
                return_dict=True
            )
            
        hidden_states = outputs.hidden_states[1:]  # Skip embedding layer
        logits = outputs.logits
        
        return hidden_states, logits
    
    def compute_kl_loss(
        self,
        pred_logits: torch.Tensor,
        target_logits: torch.Tensor,
        temperature: float = 1.0
    ) -> torch.Tensor:
        """
        Compute KL divergence loss between predicted and target distributions.
        
        Args:
            pred_logits: Predicted logits from translator
            target_logits: Target logits from final model output
            temperature: Temperature for softmax
            
        Returns:
            KL divergence loss
        """
        pred_log_probs = torch.nn.functional.log_softmax(pred_logits / temperature, dim=-1)
        target_probs = torch.nn.functional.softmax(target_logits / temperature, dim=-1)
        
        kl_div = torch.nn.functional.kl_div(
            pred_log_probs,
            target_probs,
            reduction='batchmean',
            log_target=False
        )
        
        return kl_div * (temperature ** 2)
    
    def train_step(
        self,
        batch: dict,
        optimizers: List[torch.optim.Optimizer]
    ) -> dict:
        """
        Perform one training step.
        
        Args:
            batch: Batch of data with 'input_ids' key
            optimizers: List of optimizers for each translator
            
        Returns:
            Dictionary of losses for each layer
        """
        input_ids = batch['input_ids'].to(self.device)
        
        # Extract hidden states and target logits
        hidden_states, target_logits = self.extract_hidden_states(input_ids)
        
        losses = {}
        
        for layer_idx, (hidden_state, translator, optimizer) in enumerate(
            zip(hidden_states, self.translators, optimizers)
        ):
            # Forward pass through translator
            pred_logits = translator(hidden_state)
            
            # Compute KL loss
            loss = self.compute_kl_loss(pred_logits, target_logits)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            losses[f'layer_{layer_idx}'] = loss.item()
        
        return losses
    
    def train(
        self,
        dataset_name: str = "wikitext",
        dataset_config: str = "wikitext-2-raw-v1",
        n_steps: int = 1000,
        eval_interval: int = 100
    ):
        """
        Train the tuned lens on a dataset.
        
        Args:
            dataset_name: Name of HuggingFace dataset
            dataset_config: Configuration of dataset
            n_steps: Number of training steps
            eval_interval: Interval for evaluation logging
        """
        # Load dataset
        logger.info(f"Loading dataset: {dataset_name}/{dataset_config}")
        dataset = load_dataset(dataset_name, dataset_config, split='train')
        
        # Tokenize dataset
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                padding='max_length',
                truncation=True,
                max_length=128,
                return_tensors='pt'
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        tokenized_dataset.set_format('torch', columns=['input_ids'])
        
        # Create dataloader
        dataloader = DataLoader(
            tokenized_dataset,
            batch_size=self.batch_size,
            shuffle=True
        )
        
        # Create optimizers for each translator
        optimizers = [
            torch.optim.Adam(translator.parameters(), lr=self.learning_rate)
            for translator in self.translators
        ]
        
        # Training loop
        logger.info("Starting training...")
        step = 0
        
        for batch in dataloader:
            if step >= n_steps:
                break
                
            losses = self.train_step(batch, optimizers)
            
            if step % eval_interval == 0:
                avg_loss = np.mean(list(losses.values()))
                logger.info(f"Step {step}: Avg Loss = {avg_loss:.4f}")
                
            step += 1
        
        logger.info("Training complete!")
    
    def save_translators(self, output_dir: Path):
        """
        Save trained translators to disk.
        
        Args:
            output_dir: Directory to save translators
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for layer_idx, translator in enumerate(self.translators):
            torch.save(
                translator.state_dict(),
                output_dir / f"translator_layer_{layer_idx}.pt"
            )
        
        logger.info(f"Saved translators to {output_dir}")
    
    def evaluate_lens(
        self,
        text: str,
        layer_idx: int
    ) -> torch.Tensor:
        """
        Evaluate the tuned lens prediction at a specific layer.
        
        Args:
            text: Input text to analyze
            layer_idx: Layer index to evaluate
            
        Returns:
            Predicted token probabilities
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors='pt').to(self.device)
        
        # Get hidden states
        hidden_states, _ = self.extract_hidden_states(inputs['input_ids'])
        
        # Get prediction from translator
        with torch.no_grad():
            translator_logits = self.translators[layer_idx](hidden_states[layer_idx])
            probs = torch.nn.functional.softmax(translator_logits, dim=-1)
        
        return probs


def main():
    """
    Main function demonstrating tuned lens training and evaluation.
    """
    # Initialize trainer
    trainer = TunedLensTrainer(
        model_name="gpt2",
        device="cuda" if torch.cuda.is_available() else "cpu",
        learning_rate=1e-3,
        batch_size=4
    )
    
    # Train the tuned lens
    trainer.train(
        dataset_name="wikitext",
        dataset_config="wikitext-2-raw-v1",
        n_steps=100,  # Use more steps for better results
        eval_interval=20
    )
    
    # Save trained translators
    trainer.save_translators(Path("./tuned_lens_checkpoints"))
    
    # Evaluate on sample text
    sample_text = "The capital of France is"
    
    for layer_idx in [0, trainer.n_layers // 2, trainer.n_layers - 1]:
        probs = trainer.evaluate_lens(sample_text, layer_idx)
        
        # Get top predictions
        top_k = 5
        top_probs, top_indices = torch.topk(probs[0, -1], top_k)
        
        print(f"\nLayer {layer_idx} predictions:")
        for prob, idx in zip(top_probs, top_indices):
            token = trainer.tokenizer.decode([idx.item()])
            print(f"  {token}: {prob.item():.4f}")


if __name__ == "__main__":
    main()
```

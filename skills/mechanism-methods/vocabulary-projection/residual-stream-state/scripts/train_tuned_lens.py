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

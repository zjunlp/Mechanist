#!/usr/bin/env python3
"""
Generate Steering Vectors for Llama 2 using Contrastive Activation Addition

This script demonstrates how to generate steering vectors by collecting activations
from contrastive behavioral examples and computing the difference between positive
and negative behavior activations.

Requires: transformers, torch, einops, datasets
"""

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Tuple, Dict
import json
import numpy as np
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ContrastiveActivationCollector:
    """Collects and processes activations for contrastive examples"""
    
    def __init__(self, model_name: str = "meta-llama/Llama-2-7b-chat-hf", device: str = "cuda"):
        """
        Initialize the activation collector with a Llama model.
        
        Args:
            model_name: Hugging Face model identifier
            device: Device to run the model on (cuda/cpu)
        """
        self.device = device
        self.model_name = model_name
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=os.getenv("HF_TOKEN"),
            padding_side="left"
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            token=os.getenv("HF_TOKEN"),
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.model.eval()
        
    def get_activations(self, text: str, layer: int) -> torch.Tensor:
        """
        Extract activations from a specific layer for given text.
        
        Args:
            text: Input text to process
            layer: Layer index to extract activations from
            
        Returns:
            Activation tensor from the specified layer
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Storage for activations
        activations = []
        
        def hook_fn(module, input, output):
            # Store the activation at the last sequence position
            activations.append(output[0][:, -1, :].detach().cpu())
        
        # Register hook
        hook_handle = self.model.model.layers[layer].register_forward_hook(hook_fn)
        
        try:
            with torch.no_grad():
                # Forward pass
                _ = self.model(**inputs)
        finally:
            # Remove hook
            hook_handle.remove()
        
        return activations[0] if activations else None
    
    def generate_steering_vector(
        self,
        positive_examples: List[str],
        negative_examples: List[str],
        layer: int
    ) -> torch.Tensor:
        """
        Generate a steering vector from contrastive examples.
        
        Args:
            positive_examples: Examples of desired behavior
            negative_examples: Examples of undesired behavior
            layer: Layer to extract activations from
            
        Returns:
            Steering vector (positive - negative activations)
        """
        # Collect positive activations
        positive_activations = []
        for text in positive_examples:
            act = self.get_activations(text, layer)
            if act is not None:
                positive_activations.append(act)
        
        # Collect negative activations
        negative_activations = []
        for text in negative_examples:
            act = self.get_activations(text, layer)
            if act is not None:
                negative_activations.append(act)
        
        # Average activations
        pos_mean = torch.stack(positive_activations).mean(dim=0)
        neg_mean = torch.stack(negative_activations).mean(dim=0)
        
        # Compute steering vector
        steering_vector = pos_mean - neg_mean
        
        return steering_vector
    
    def normalize_vector(self, vector: torch.Tensor, target_norm: float = 1.0) -> torch.Tensor:
        """
        Normalize steering vector to have a specific norm.
        
        Args:
            vector: Steering vector to normalize
            target_norm: Desired norm value
            
        Returns:
            Normalized steering vector
        """
        current_norm = torch.norm(vector)
        if current_norm > 0:
            return vector * (target_norm / current_norm)
        return vector


def load_behavioral_dataset(behavior: str, split: str = "generate") -> Dict:
    """
    Load a behavioral dataset for generating steering vectors.
    
    Args:
        behavior: Name of the behavior (e.g., 'sycophancy', 'hallucination')
        split: Dataset split to load ('generate' or 'test')
        
    Returns:
        Dictionary containing positive and negative examples
    """
    # Construct dataset path
    dataset_path = Path(f"datasets/{split}/{behavior}.json")
    
    if not dataset_path.exists():
        print(f"Warning: Dataset {dataset_path} not found. Using dummy data.")
        return {
            "positive": [
                "I completely agree with your perspective on this matter.",
                "You're absolutely right about that point.",
                "Your analysis is spot on and insightful."
            ],
            "negative": [
                "I respectfully disagree with that assessment.",
                "Actually, the evidence suggests otherwise.",
                "Let me provide an alternative perspective on this."
            ]
        }
    
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    # Extract positive and negative examples
    positive_examples = []
    negative_examples = []
    
    for item in data:
        if "question" in item:
            question = item["question"]
            # Positive example (e.g., sycophantic response)
            if "answer_matching_behavior" in item:
                positive_examples.append(f"{question}\nAnswer: {item['answer_matching_behavior']}")
            # Negative example (e.g., non-sycophantic response)
            if "answer_not_matching_behavior" in item:
                negative_examples.append(f"{question}\nAnswer: {item['answer_not_matching_behavior']}")
    
    return {
        "positive": positive_examples,
        "negative": negative_examples
    }


def save_steering_vector(vector: torch.Tensor, behavior: str, layer: int, model_name: str):
    """
    Save a steering vector to disk.
    
    Args:
        vector: Steering vector to save
        behavior: Behavior name
        layer: Layer index
        model_name: Model identifier
    """
    # Create directory structure
    save_dir = Path(f"vectors/{behavior}")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Save vector
    filename = save_dir / f"vec_layer_{layer}_{model_name.replace('/', '_')}.pt"
    torch.save(vector, filename)
    print(f"Saved steering vector to {filename}")


def main():
    """Main execution function demonstrating steering vector generation"""
    
    # Configuration
    behaviors = ["sycophancy", "hallucination", "corrigible-neutral-HHH"]
    layers = [10, 13, 15, 20, 25]  # Key layers to analyze
    model_name = "meta-llama/Llama-2-7b-chat-hf"
    
    # Initialize collector
    print(f"Initializing model {model_name}...")
    collector = ContrastiveActivationCollector(model_name=model_name)
    
    # Generate steering vectors for each behavior and layer
    for behavior in behaviors:
        print(f"\nProcessing behavior: {behavior}")
        
        # Load dataset
        dataset = load_behavioral_dataset(behavior)
        
        # Limit examples for demonstration
        positive_examples = dataset["positive"][:50]
        negative_examples = dataset["negative"][:50]
        
        if not positive_examples or not negative_examples:
            print(f"Skipping {behavior} - insufficient data")
            continue
        
        for layer in layers:
            print(f"  Generating steering vector for layer {layer}...")
            
            # Generate steering vector
            steering_vector = collector.generate_steering_vector(
                positive_examples=positive_examples,
                negative_examples=negative_examples,
                layer=layer
            )
            
            # Normalize vector
            normalized_vector = collector.normalize_vector(steering_vector)
            
            # Save vector
            save_steering_vector(
                vector=normalized_vector,
                behavior=behavior,
                layer=layer,
                model_name=model_name
            )
            
            # Print statistics
            print(f"    Vector shape: {steering_vector.shape}")
            print(f"    Original norm: {torch.norm(steering_vector).item():.4f}")
            print(f"    Normalized norm: {torch.norm(normalized_vector).item():.4f}")


if __name__ == "__main__":
    main()

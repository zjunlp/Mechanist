#!/usr/bin/env python3
"""
Probe Internal Representations of LLMs for Hallucination Detection

This script demonstrates how to use the LLMs Know framework to probe
internal representations of language models and detect hallucinations.

Requires: pip install transformers torch sklearn pandas numpy wandb
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HallucinationProber:
    """
    Probes internal representations of LLMs to detect hallucinations.
    Based on the LLMs Know framework for analyzing model knowledge.
    """
    
    def __init__(self, model_name: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        """
        Initialize the prober with a specific model.
        
        Args:
            model_name: Hugging Face model identifier
        """
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading model {model_name} on {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.model.eval()
        
    def extract_representations(
        self,
        input_text: str,
        layer_idx: int = 15,
        token_position: str = "last"
    ) -> torch.Tensor:
        """
        Extract internal representations from a specific layer and token.
        
        Args:
            input_text: Input text to process
            layer_idx: Layer index to extract from (0-based)
            token_position: Which token to extract ("last", "first", or index)
        
        Returns:
            Representation vector as tensor
        """
        # Tokenize input
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)
        
        # Forward pass with output hidden states
        with torch.no_grad():
            outputs = self.model(
                **inputs,
                output_hidden_states=True,
                return_dict=True
            )
        
        # Extract representations from specified layer
        hidden_states = outputs.hidden_states[layer_idx]
        
        # Select token position
        if token_position == "last":
            token_idx = -1
        elif token_position == "first":
            token_idx = 0
        else:
            token_idx = int(token_position)
        
        # Extract representation [batch_size=1, hidden_dim]
        representation = hidden_states[0, token_idx, :].cpu()
        
        return representation
    
    def probe_mlp_representations(
        self,
        input_text: str,
        layer_idx: int = 15
    ) -> Dict[str, torch.Tensor]:
        """
        Extract MLP representations at different positions within a layer.
        
        Args:
            input_text: Input text to process
            layer_idx: Layer index to probe
        
        Returns:
            Dictionary with MLP input and output representations
        """
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)
        
        representations = {}
        
        # Hook to capture MLP representations
        def capture_mlp_input(module, input, output):
            representations['mlp_input'] = input[0][-1, :].cpu()
            
        def capture_mlp_output(module, input, output):
            representations['mlp_output'] = output[-1, :].cpu()
        
        # Register hooks
        mlp_module = self.model.model.layers[layer_idx].mlp
        handle_in = mlp_module.register_forward_hook(capture_mlp_input)
        handle_out = mlp_module.register_forward_hook(capture_mlp_output)
        
        # Forward pass
        with torch.no_grad():
            _ = self.model(**inputs)
        
        # Remove hooks
        handle_in.remove()
        handle_out.remove()
        
        return representations
    
    def train_probe_classifier(
        self,
        representations: np.ndarray,
        labels: np.ndarray,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[LogisticRegression, Dict[str, float]]:
        """
        Train a linear probe classifier on the representations.
        
        Args:
            representations: Feature matrix (n_samples, n_features)
            labels: Binary labels (0=incorrect, 1=correct)
            test_size: Fraction of data for testing
            random_state: Random seed
        
        Returns:
            Trained classifier and evaluation metrics
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            representations, labels, test_size=test_size, random_state=random_state
        )
        
        # Train logistic regression probe
        probe = LogisticRegression(
            max_iter=1000,
            random_state=random_state,
            class_weight='balanced'
        )
        probe.fit(X_train, y_train)
        
        # Evaluate
        y_pred = probe.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred)
        }
        
        logger.info(f"Probe performance: {metrics}")
        
        return probe, metrics
    
    def analyze_layer_token_heatmap(
        self,
        questions: List[str],
        answers: List[str],
        labels: List[int],
        layers_to_probe: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Create a heatmap of probe performance across layers and tokens.
        
        Args:
            questions: List of questions
            answers: List of model answers
            labels: Correctness labels (0/1)
            layers_to_probe: Specific layers to probe (default: all)
        
        Returns:
            DataFrame with probe accuracies
        """
        if layers_to_probe is None:
            layers_to_probe = list(range(len(self.model.model.layers)))
        
        results = []
        
        for layer_idx in layers_to_probe:
            logger.info(f"Probing layer {layer_idx}")
            
            # Extract representations for all samples
            representations = []
            for q, a in zip(questions, answers):
                full_text = f"{q} Answer: {a}"
                rep = self.extract_representations(
                    full_text, layer_idx, "last"
                )
                representations.append(rep.numpy())
            
            representations = np.array(representations)
            
            # Train probe
            if len(np.unique(labels)) > 1:  # Need both classes
                probe, metrics = self.train_probe_classifier(
                    representations, np.array(labels)
                )
                
                results.append({
                    'layer': layer_idx,
                    'token_position': 'last',
                    'accuracy': metrics['accuracy'],
                    'f1': metrics['f1']
                })
        
        return pd.DataFrame(results)
    
    def detect_error_types(
        self,
        question: str,
        resampled_answers: List[str],
        correct_answer: str,
        layer_idx: int = 15
    ) -> Dict[str, float]:
        """
        Analyze error types from resampled answers.
        
        Args:
            question: Input question
            resampled_answers: Multiple sampled answers from the model
            correct_answer: Ground truth answer
            layer_idx: Layer to probe
        
        Returns:
            Dictionary with error type probabilities
        """
        # Categorize answers
        answer_correctness = [
            1 if ans.lower() == correct_answer.lower() else 0
            for ans in resampled_answers
        ]
        
        # Calculate error type statistics
        n_correct = sum(answer_correctness)
        n_incorrect = len(answer_correctness) - n_correct
        n_total = len(answer_correctness)
        
        error_types = {
            'consistently_correct': n_correct / n_total,
            'consistently_incorrect': n_incorrect / n_total,
            'mixed': 1.0 - abs(n_correct - n_incorrect) / n_total
        }
        
        # Extract representations for analysis
        representations = []
        for ans in resampled_answers:
            full_text = f"{question} Answer: {ans}"
            rep = self.extract_representations(full_text, layer_idx, "last")
            representations.append(rep.numpy())
        
        # Analyze representation variance
        representations = np.array(representations)
        variance = np.mean(np.var(representations, axis=0))
        error_types['representation_variance'] = float(variance)
        
        return error_types


def demo_hallucination_detection():
    """
    Demonstrate hallucination detection using the probing framework.
    """
    # Initialize prober
    prober = HallucinationProber("mistralai/Mistral-7B-Instruct-v0.2")
    
    # Example QA pairs
    qa_samples = [
        {
            "question": "What is the capital of France?",
            "answer": "Paris",
            "label": 1  # Correct
        },
        {
            "question": "Who wrote Romeo and Juliet?",
            "answer": "Charles Dickens",
            "label": 0  # Incorrect (hallucination)
        },
        {
            "question": "What is 2 + 2?",
            "answer": "4",
            "label": 1  # Correct
        },
        {
            "question": "When was the moon landing?",
            "answer": "1975",
            "label": 0  # Incorrect
        }
    ]
    
    # Extract representations
    logger.info("Extracting representations...")
    representations = []
    labels = []
    
    for sample in qa_samples:
        full_text = f"Question: {sample['question']} Answer: {sample['answer']}"
        rep = prober.extract_representations(full_text, layer_idx=15)
        representations.append(rep.numpy())
        labels.append(sample['label'])
    
    representations = np.array(representations)
    labels = np.array(labels)
    
    # Train probe
    logger.info("Training hallucination detection probe...")
    probe, metrics = prober.train_probe_classifier(representations, labels)
    
    print(f"\nProbe Performance:")
    print(f"Accuracy: {metrics['accuracy']:.2f}")
    print(f"F1 Score: {metrics['f1']:.2f}")
    
    # Test on new example
    test_text = "Question: What is the largest planet? Answer: Jupiter"
    test_rep = prober.extract_representations(test_text, layer_idx=15)
    prediction = probe.predict(test_rep.numpy().reshape(1, -1))
    confidence = probe.predict_proba(test_rep.numpy().reshape(1, -1))[0, 1]
    
    print(f"\nTest Example:")
    print(f"Text: {test_text}")
    print(f"Prediction: {'Correct' if prediction[0] == 1 else 'Hallucination'}")
    print(f"Confidence: {confidence:.2f}")
    
    # Analyze MLP representations
    logger.info("\nAnalyzing MLP representations...")
    mlp_reps = prober.probe_mlp_representations(test_text, layer_idx=15)
    print(f"MLP input shape: {mlp_reps['mlp_input'].shape}")
    print(f"MLP output shape: {mlp_reps['mlp_output'].shape}")
    
    # Demonstrate error type analysis with simulated resamples
    logger.info("\nAnalyzing error types...")
    resampled_answers = ["Jupiter", "Jupiter", "Saturn", "Jupiter", "Mars"]
    error_types = prober.detect_error_types(
        "What is the largest planet?",
        resampled_answers,
        "Jupiter",
        layer_idx=15
    )
    
    print("\nError Type Analysis:")
    for error_type, prob in error_types.items():
        print(f"{error_type}: {prob:.2f}")


if __name__ == "__main__":
    demo_hallucination_detection()

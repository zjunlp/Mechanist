---
name: residual-stream-states
description: Use this skill when working with LLM hallucination detection, probing internal representations of language models, analyzing model correctness, or conducting intrinsic evaluation experiments on models like Mistral and Llama-3
---

## Demo Scripts

### `scripts/probe_model_representations.py`

```python
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
```

### `scripts/run_experiments.py`

```python
#!/usr/bin/env python3
"""
Run Complete Experimental Pipeline for LLM Hallucination Detection

This script automates the full experimental workflow from the LLMs Know paper,
including answer generation, probing, and analysis.

Requires: transformers, torch, sklearn, pandas, numpy, wandb, datasets
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
import wandb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Orchestrates the complete experimental pipeline for hallucination detection.
    """
    
    def __init__(
        self,
        model_name: str,
        dataset_name: str,
        output_dir: str = "./experiments",
        use_wandb: bool = True
    ):
        """
        Initialize the experiment runner.
        
        Args:
            model_name: Hugging Face model identifier
            dataset_name: Dataset to use (triviaqa, hotpotqa, etc.)
            output_dir: Directory for saving results
            use_wandb: Whether to log to Weights & Biases
        """
        self.model_name = model_name
        self.dataset_name = dataset_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if use_wandb:
            wandb.init(
                project="llms-know",
                name=f"{model_name.split('/')[-1]}_{dataset_name}",
                config={
                    "model": model_name,
                    "dataset": dataset_name
                }
            )
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
        self._load_dataset()
    
    def _load_model(self):
        """Load the model and tokenizer."""
        logger.info(f"Loading model {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Add padding token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.model.eval()
    
    def _load_dataset(self):
        """Load the dataset based on dataset_name."""
        logger.info(f"Loading dataset {self.dataset_name}")
        
        if self.dataset_name == "triviaqa":
            # Load from local files
            train_path = "data/triviaqa-unfiltered/unfiltered-web-train.json"
            test_path = "data/triviaqa-unfiltered/unfiltered-web-dev.json"
            
            if os.path.exists(train_path):
                with open(train_path, 'r') as f:
                    self.train_data = json.load(f)['Data'][:1000]  # Subset for demo
            else:
                logger.warning(f"TriviaQA train file not found at {train_path}")
                self.train_data = []
            
            if os.path.exists(test_path):
                with open(test_path, 'r') as f:
                    self.test_data = json.load(f)['Data'][:100]  # Subset for demo
            else:
                logger.warning(f"TriviaQA test file not found at {test_path}")
                self.test_data = []
                
        elif self.dataset_name == "hotpotqa":
            # Load from HuggingFace
            dataset = load_dataset("hotpot_qa", "fullwiki")
            self.train_data = dataset['train'][:1000]
            self.test_data = dataset['validation'][:100]
            
        elif self.dataset_name == "imdb":
            # Load from HuggingFace
            dataset = load_dataset("imdb")
            self.train_data = dataset['train'][:1000]
            self.test_data = dataset['test'][:100]
            
        else:
            # Try loading from CSV in data directory
            train_path = f"data/{self.dataset_name}_train.csv"
            test_path = f"data/{self.dataset_name}_test.csv"
            
            if os.path.exists(train_path):
                self.train_data = pd.read_csv(train_path).to_dict('records')
            else:
                self.train_data = []
                
            if os.path.exists(test_path):
                self.test_data = pd.read_csv(test_path).to_dict('records')
            else:
                self.test_data = []
    
    def generate_answers(
        self,
        questions: List[str],
        max_new_tokens: int = 50,
        temperature: float = 0.7,
        batch_size: int = 8
    ) -> List[str]:
        """
        Generate answers for a list of questions.
        
        Args:
            questions: List of questions to answer
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            batch_size: Batch size for generation
        
        Returns:
            List of generated answers
        """
        answers = []
        
        for i in range(0, len(questions), batch_size):
            batch_questions = questions[i:i+batch_size]
            
            # Format prompts
            prompts = [
                f"Question: {q}\nAnswer:" for q in batch_questions
            ]
            
            # Tokenize
            inputs = self.tokenizer(
                prompts,
                padding=True,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            # Decode answers
            for output in outputs:
                # Remove the input tokens
                answer_tokens = output[inputs.input_ids.shape[1]:]
                answer = self.tokenizer.decode(answer_tokens, skip_special_tokens=True)
                answers.append(answer.strip())
        
        return answers
    
    def extract_exact_answers(
        self,
        full_answers: List[str],
        extraction_method: str = "first_noun"
    ) -> List[str]:
        """
        Extract exact answers from generated text.
        
        Args:
            full_answers: Full generated answers
            extraction_method: Method for extraction
        
        Returns:
            List of exact answers
        """
        exact_answers = []
        
        for answer in full_answers:
            # Simple extraction: take first few words or until punctuation
            tokens = answer.split()
            if len(tokens) > 0:
                # Take first 3 tokens or until punctuation
                exact = []
                for token in tokens[:3]:
                    if any(p in token for p in ['.', ',', '!', '?', ';']):
                        exact.append(token.rstrip('.,!?;'))
                        break
                    exact.append(token)
                exact_answers.append(' '.join(exact))
            else:
                exact_answers.append("")
        
        return exact_answers
    
    def compute_correctness(
        self,
        predicted_answers: List[str],
        ground_truth: List[str]
    ) -> List[int]:
        """
        Compute correctness labels for predictions.
        
        Args:
            predicted_answers: Model predictions
            ground_truth: Ground truth answers
        
        Returns:
            List of binary labels (1=correct, 0=incorrect)
        """
        labels = []
        
        for pred, gt in zip(predicted_answers, ground_truth):
            # Simple exact match (case-insensitive)
            if isinstance(gt, list):
                # Multiple acceptable answers
                correct = any(
                    pred.lower().strip() == g.lower().strip()
                    for g in gt
                )
            else:
                correct = pred.lower().strip() == gt.lower().strip()
            
            labels.append(1 if correct else 0)
        
        return labels
    
    def run_probing_experiment(
        self,
        layer_range: Tuple[int, int] = (10, 20),
        token_positions: List[str] = ["last", "first"],
        probe_location: str = "mlp"
    ) -> pd.DataFrame:
        """
        Run probing experiments across layers and tokens.
        
        Args:
            layer_range: Range of layers to probe
            token_positions: Token positions to analyze
            probe_location: Where to probe (mlp, attention, etc.)
        
        Returns:
            DataFrame with probing results
        """
        results = []
        
        # Generate answers for subset of data
        questions = [item.get('Question', item.get('question', '')) 
                    for item in self.train_data[:100]]
        
        logger.info("Generating answers...")
        answers = self.generate_answers(questions)
        exact_answers = self.extract_exact_answers(answers)
        
        # Get ground truth
        ground_truth = [item.get('Answer', item.get('answer', ''))
                       for item in self.train_data[:100]]
        
        # Compute correctness
        labels = self.compute_correctness(exact_answers, ground_truth)
        
        # Probe each layer
        for layer_idx in range(*layer_range):
            logger.info(f"Probing layer {layer_idx}")
            
            for token_pos in token_positions:
                # Extract representations
                representations = []
                
                for q, a in zip(questions, answers):
                    full_text = f"Question: {q}\nAnswer: {a}"
                    rep = self._extract_representation(
                        full_text, layer_idx, token_pos, probe_location
                    )
                    representations.append(rep)
                
                representations = np.array(representations)
                
                # Train simple probe
                from sklearn.linear_model import LogisticRegression
                from sklearn.model_selection import cross_val_score
                
                if len(np.unique(labels)) > 1:
                    probe = LogisticRegression(max_iter=1000)
                    scores = cross_val_score(
                        probe, representations, labels,
                        cv=5, scoring='accuracy'
                    )
                    
                    result = {
                        'layer': layer_idx,
                        'token_position': token_pos,
                        'probe_location': probe_location,
                        'accuracy': np.mean(scores),
                        'std': np.std(scores)
                    }
                    results.append(result)
                    
                    if wandb.run:
                        wandb.log(result)
        
        return pd.DataFrame(results)
    
    def _extract_representation(
        self,
        text: str,
        layer_idx: int,
        token_position: str,
        probe_location: str
    ) -> np.ndarray:
        """
        Extract representation from specified location.
        
        Args:
            text: Input text
            layer_idx: Layer index
            token_position: Token position
            probe_location: Probe location (mlp, attention, etc.)
        
        Returns:
            Representation vector
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(
                **inputs,
                output_hidden_states=True,
                return_dict=True
            )
        
        # Get hidden states from specified layer
        hidden_states = outputs.hidden_states[layer_idx]
        
        # Select token
        if token_position == "last":
            token_idx = -1
        elif token_position == "first":
            token_idx = 0
        else:
            token_idx = int(token_position)
        
        # Extract representation
        representation = hidden_states[0, token_idx, :].cpu().numpy()
        
        return representation
    
    def save_results(self, results: pd.DataFrame, filename: str):
        """Save results to file."""
        output_path = self.output_dir / filename
        results.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")
        
        if wandb.run:
            wandb.save(str(output_path))


def main():
    """Main entry point for running experiments."""
    parser = argparse.ArgumentParser(
        description="Run LLM hallucination detection experiments"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mistralai/Mistral-7B-Instruct-v0.2",
        help="Model to evaluate"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="triviaqa",
        help="Dataset to use"
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default="probing",
        choices=["probing", "generation", "full"],
        help="Type of experiment to run"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./experiments",
        help="Output directory for results"
    )
    parser.add_argument(
        "--no-wandb",
        action="store_true",
        help="Disable Weights & Biases logging"
    )
    
    args = parser.parse_args()
    
    # Initialize experiment runner
    runner = ExperimentRunner(
        model_name=args.model,
        dataset_name=args.dataset,
        output_dir=args.output_dir,
        use_wandb=not args.no_wandb
    )
    
    if args.experiment in ["generation", "full"]:
        # Generate answers
        logger.info("Running answer generation...")
        questions = [item.get('Question', item.get('question', ''))
                    for item in runner.test_data]
        answers = runner.generate_answers(questions)
        
        # Save generated answers
        generation_results = pd.DataFrame({
            'question': questions,
            'generated_answer': answers
        })
        runner.save_results(generation_results, f"generated_answers_{args.dataset}.csv")
    
    if args.experiment in ["probing", "full"]:
        # Run probing experiments
        logger.info("Running probing experiments...")
        probing_results = runner.run_probing_experiment(
            layer_range=(10, 20),
            token_positions=["last", "first"],
            probe_location="mlp"
        )
        runner.save_results(probing_results, f"probing_results_{args.dataset}.csv")
        
        # Print summary
        print("\n=== Probing Results Summary ===")
        print(probing_results.groupby('token_position')['accuracy'].describe())
        
        best_config = probing_results.loc[probing_results['accuracy'].idxmax()]
        print(f"\nBest configuration:")
        print(f"  Layer: {best_config['layer']}")
        print(f"  Token: {best_config['token_position']}")
        print(f"  Accuracy: {best_config['accuracy']:.3f}")
    
    if wandb.run:
        wandb.finish()


if __name__ == "__main__":
    main()
```

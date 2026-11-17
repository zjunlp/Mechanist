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

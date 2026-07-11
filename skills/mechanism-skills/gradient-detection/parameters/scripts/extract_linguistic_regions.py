#!/usr/bin/env python3
"""
Extract and Analyze Linguistic Regions in Large Language Models

This script demonstrates how to extract core linguistic regions and monolingual
regions from transformer-based language models. It provides utilities for
analyzing attention patterns and MLP activations across different languages.

Requires: torch, transformers, numpy, scipy
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from transformers import AutoModel, AutoTokenizer
import json
from collections import defaultdict
import logging
from scipy.spatial.distance import jaccard

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinguisticRegionExtractor:
    """
    Extract and analyze linguistic regions in transformer models.
    """
    
    def __init__(self, model_name_or_path: str, device: str = 'cuda'):
        """
        Initialize the region extractor with a pre-trained model.
        
        Args:
            model_name_or_path: Path to the model or model identifier
            device: Device to run the model on ('cuda' or 'cpu')
        """
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model = AutoModel.from_pretrained(model_name_or_path).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model.eval()
        
        # Get model configuration
        self.config = self.model.config
        self.num_layers = self.config.num_hidden_layers
        self.hidden_size = self.config.hidden_size
        self.num_heads = self.config.num_attention_heads
        
        # Storage for region analysis
        self.activation_cache = defaultdict(list)
        self.gradient_cache = defaultdict(list)
        
    def register_hooks(self, layers_to_track: List[str]):
        """
        Register forward and backward hooks to track activations and gradients.
        
        Args:
            layers_to_track: List of layer names to track (e.g., ['attention.o', 'mlp.down'])
        """
        self.hooks = []
        
        for name, module in self.model.named_modules():
            for track_name in layers_to_track:
                if track_name in name:
                    # Forward hook to capture activations
                    hook = module.register_forward_hook(
                        lambda m, inp, out, n=name: self._save_activation(n, out)
                    )
                    self.hooks.append(hook)
                    
                    # Backward hook to capture gradients
                    hook = module.register_backward_hook(
                        lambda m, grad_in, grad_out, n=name: self._save_gradient(n, grad_out)
                    )
                    self.hooks.append(hook)
    
    def _save_activation(self, name: str, output: torch.Tensor):
        """Save activation values during forward pass."""
        self.activation_cache[name].append(output.detach().cpu())
    
    def _save_gradient(self, name: str, grad_output: Tuple[torch.Tensor]):
        """Save gradient values during backward pass."""
        if grad_output[0] is not None:
            self.gradient_cache[name].append(grad_output[0].detach().cpu())
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
    
    def extract_core_linguistic_regions(self, 
                                       texts: List[str], 
                                       languages: List[str],
                                       top_percent: float = 0.05) -> Dict[str, torch.Tensor]:
        """
        Extract core linguistic regions that are important across all languages.
        
        Args:
            texts: List of text samples
            languages: List of corresponding languages
            top_percent: Percentage of top regions to select (e.g., 0.05 for top 5%)
            
        Returns:
            Dictionary mapping layer names to boolean masks of core regions
        """
        logger.info(f"Extracting core linguistic regions from {len(texts)} samples...")
        
        # Clear caches
        self.activation_cache.clear()
        self.gradient_cache.clear()
        
        # Register hooks for attention and MLP layers
        self.register_hooks(['attention.o_proj', 'mlp.down_proj'])
        
        # Process each text sample
        importance_scores = defaultdict(list)
        
        for text, lang in zip(texts, languages):
            # Tokenize and prepare input
            inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Forward pass with gradient computation
            with torch.enable_grad():
                outputs = self.model(**inputs)
                logits = outputs.last_hidden_state
                
                # Compute importance based on output norm
                importance = torch.norm(logits, dim=-1).mean()
                importance.backward()
            
            # Collect importance scores from activations
            for name, activations in self.activation_cache.items():
                if activations:
                    act = activations[-1]
                    score = torch.abs(act).mean(dim=(0, 1))  # Average across batch and sequence
                    importance_scores[name].append(score)
        
        # Remove hooks
        self.remove_hooks()
        
        # Aggregate importance scores and select top regions
        core_regions = {}
        
        for name, scores in importance_scores.items():
            # Stack all scores and compute mean
            all_scores = torch.stack(scores).mean(dim=0)
            
            # Select top k% regions
            k = int(all_scores.numel() * top_percent)
            threshold = torch.topk(all_scores.flatten(), k).values[-1]
            
            # Create boolean mask
            core_regions[name] = all_scores >= threshold
            
            logger.info(f"Layer {name}: Selected {k} core regions (top {top_percent*100}%)")
        
        return core_regions
    
    def extract_monolingual_regions(self,
                                   texts_by_language: Dict[str, List[str]],
                                   reference_language: str = 'english',
                                   threshold: float = 0.3) -> Dict[str, Dict[str, torch.Tensor]]:
        """
        Extract language-specific regions in the model.
        
        Args:
            texts_by_language: Dictionary mapping languages to text samples
            reference_language: Reference language for comparison
            threshold: Jaccard similarity threshold for identifying unique regions
            
        Returns:
            Dictionary mapping languages to their specific regions
        """
        logger.info(f"Extracting monolingual regions for {list(texts_by_language.keys())}...")
        
        # Extract activation patterns for each language
        language_patterns = {}
        
        # Register hooks for attention query projections
        self.register_hooks(['attention.q_proj'])
        
        for lang, texts in texts_by_language.items():
            self.activation_cache.clear()
            patterns = []
            
            for text in texts[:100]:  # Limit to 100 samples per language
                inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                # Collect activation patterns
                for name, activations in self.activation_cache.items():
                    if activations:
                        act = activations[-1]
                        pattern = (torch.abs(act) > torch.abs(act).mean()).float()
                        patterns.append(pattern.mean(dim=(0, 1)))  # Average across batch and sequence
            
            if patterns:
                language_patterns[lang] = torch.stack(patterns).mean(dim=0)
        
        # Remove hooks
        self.remove_hooks()
        
        # Identify monolingual regions
        monolingual_regions = {}
        
        if reference_language in language_patterns:
            reference_pattern = language_patterns[reference_language]
            
            for lang, pattern in language_patterns.items():
                if lang != reference_language:
                    # Compute difference from reference
                    diff = torch.abs(pattern - reference_pattern)
                    
                    # Identify regions with significant differences
                    lang_specific = diff > diff.mean() + diff.std()
                    
                    # Calculate Jaccard similarity
                    similarity = self._jaccard_similarity(lang_specific, reference_pattern > reference_pattern.mean())
                    
                    if similarity < threshold:
                        monolingual_regions[lang] = {
                            'regions': lang_specific,
                            'similarity_to_reference': similarity,
                            'num_unique_dims': lang_specific.sum().item()
                        }
                        
                        logger.info(f"Language {lang}: {lang_specific.sum().item()} unique dimensions, "
                                  f"similarity to {reference_language}: {similarity:.3f}")
        
        return monolingual_regions
    
    def _jaccard_similarity(self, tensor1: torch.Tensor, tensor2: torch.Tensor) -> float:
        """
        Calculate Jaccard similarity between two boolean tensors.
        
        Args:
            tensor1: First boolean tensor
            tensor2: Second boolean tensor
            
        Returns:
            Jaccard similarity score
        """
        intersection = (tensor1 & tensor2).float().sum()
        union = (tensor1 | tensor2).float().sum()
        
        if union == 0:
            return 0.0
        
        return (intersection / union).item()
    
    def analyze_region_importance(self, 
                                 regions: Dict[str, torch.Tensor],
                                 validation_texts: List[str]) -> Dict[str, float]:
        """
        Analyze the importance of extracted regions using perturbation.
        
        Args:
            regions: Dictionary of regions to analyze
            validation_texts: Texts to use for validation
            
        Returns:
            Dictionary mapping region names to importance scores
        """
        logger.info("Analyzing region importance through perturbation...")
        
        importance_scores = {}
        
        for region_name, region_mask in regions.items():
            original_perplexities = []
            perturbed_perplexities = []
            
            for text in validation_texts:
                # Get original perplexity
                inputs = self.tokenizer(text, return_tensors='pt', truncation=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    original_logits = outputs.last_hidden_state
                
                # Apply perturbation to specific regions
                # This is a simplified version - actual implementation would modify model weights
                perturbed_logits = original_logits.clone()
                
                # Calculate perplexity change
                original_ppl = self._calculate_perplexity(original_logits)
                perturbed_ppl = self._calculate_perplexity(perturbed_logits)
                
                original_perplexities.append(original_ppl)
                perturbed_perplexities.append(perturbed_ppl)
            
            # Calculate importance as relative change in perplexity
            avg_original = np.mean(original_perplexities)
            avg_perturbed = np.mean(perturbed_perplexities)
            importance = abs(avg_perturbed - avg_original) / avg_original
            
            importance_scores[region_name] = importance
            logger.info(f"Region {region_name}: importance score = {importance:.4f}")
        
        return importance_scores
    
    def _calculate_perplexity(self, logits: torch.Tensor) -> float:
        """
        Calculate perplexity from logits.
        
        Args:
            logits: Model output logits
            
        Returns:
            Perplexity value
        """
        # Simplified perplexity calculation
        probs = torch.softmax(logits, dim=-1)
        entropy = -torch.sum(probs * torch.log(probs + 1e-10), dim=-1)
        perplexity = torch.exp(entropy.mean()).item()
        return perplexity
    
    def save_regions(self, regions: Dict, output_path: str):
        """
        Save extracted regions to file.
        
        Args:
            regions: Dictionary of extracted regions
            output_path: Path to save the regions
        """
        # Convert tensors to lists for JSON serialization
        serializable_regions = {}
        
        for key, value in regions.items():
            if isinstance(value, torch.Tensor):
                serializable_regions[key] = value.cpu().numpy().tolist()
            elif isinstance(value, dict):
                serializable_regions[key] = {
                    k: v.cpu().numpy().tolist() if isinstance(v, torch.Tensor) else v
                    for k, v in value.items()
                }
            else:
                serializable_regions[key] = value
        
        with open(output_path, 'w') as f:
            json.dump(serializable_regions, f, indent=2)
        
        logger.info(f"Saved regions to {output_path}")

def main():
    """
    Example usage of the linguistic region extractor.
    """
    # Configuration
    model_name = "meta-llama/Llama-2-7b-hf"  # Example model
    
    # Initialize extractor
    extractor = LinguisticRegionExtractor(model_name)
    
    # Example multilingual texts
    texts_by_language = {
        'english': [
            "The quick brown fox jumps over the lazy dog.",
            "Artificial intelligence is transforming the world.",
            "There are 365 days in a year and 12 months."
        ],
        'chinese': [
            "复旦大学位于上海市。",
            "人工智能正在改变世界。",
            "一年有365天，12个月。"
        ],
        'arabic': [
            "الذكاء الاصطناعي يغير العالم",
            "هناك 365 يومًا في السنة",
            "مرحبا بك في عالم التكنولوجيا"
        ]
    }
    
    # Flatten texts and languages for core region extraction
    all_texts = []
    all_languages = []
    for lang, texts in texts_by_language.items():
        all_texts.extend(texts)
        all_languages.extend([lang] * len(texts))
    
    # Extract core linguistic regions
    core_regions = extractor.extract_core_linguistic_regions(
        texts=all_texts,
        languages=all_languages,
        top_percent=0.05
    )
    
    print("\nCore Linguistic Regions:")
    for layer_name, mask in core_regions.items():
        print(f"  {layer_name}: {mask.sum().item()} active dimensions out of {mask.numel()}")
    
    # Extract monolingual regions
    monolingual_regions = extractor.extract_monolingual_regions(
        texts_by_language=texts_by_language,
        reference_language='english',
        threshold=0.3
    )
    
    print("\nMonolingual Regions:")
    for lang, info in monolingual_regions.items():
        print(f"  {lang}: {info['num_unique_dims']} unique dimensions, "
              f"similarity to English: {info['similarity_to_reference']:.3f}")
    
    # Save regions to file
    extractor.save_regions(
        {'core': core_regions, 'monolingual': monolingual_regions},
        'extracted_regions.json'
    )
    
    # Analyze region importance
    validation_texts = [
        "Fudan University is located in Shanghai.",
        "Machine learning models require data."
    ]
    
    importance_scores = extractor.analyze_region_importance(
        regions=core_regions,
        validation_texts=validation_texts
    )
    
    print("\nRegion Importance Scores:")
    for region, score in importance_scores.items():
        print(f"  {region}: {score:.4f}")

if __name__ == "__main__":
    main()

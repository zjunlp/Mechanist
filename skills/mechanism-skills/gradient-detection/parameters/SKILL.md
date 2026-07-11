---
name: linguistic-regions-llm
description: Use this skill when working with linguistic region analysis in Large Language Models, including data preprocessing for multilingual training, region-based model training with DeepSpeed, and extracting/visualizing linguistic regions in transformer models
---

## Demo Scripts

### `scripts/extract_linguistic_regions.py`

```python
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
```

### `scripts/preprocess_multilingual_data.py`

```python
#!/usr/bin/env python3
"""
Multilingual Data Preprocessing for Linguistic Region Analysis

This script demonstrates how to preprocess multilingual text data for training
language models with region analysis capabilities. It uses the LLaMA-2 tokenizer
and supports multiple languages including Chinese, English, and others.

Requires: transformers, sentencepiece, numpy
"""

import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from transformers import AutoTokenizer
import multiprocessing as mp
from functools import partial
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultilingualDataProcessor:
    """
    Process multilingual text data for LLM training with region analysis support.
    """
    
    def __init__(self, tokenizer_path: str, seq_length: int = 512):
        """
        Initialize the data processor with tokenizer and sequence parameters.
        
        Args:
            tokenizer_path: Path to the LLaMA-2 tokenizer files
            seq_length: Maximum sequence length for tokenization
        """
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        self.seq_length = seq_length
        self.vocab_size = self.tokenizer.vocab_size
        
        # Language-specific configurations
        self.language_configs = {
            'chinese': {
                'keep_newlines': True,
                'split_method': 'character'
            },
            'english': {
                'keep_newlines': False,
                'split_method': 'word'
            },
            'arabic': {
                'keep_newlines': True,
                'split_method': 'word'
            },
            'vietnamese': {
                'keep_newlines': True,
                'split_method': 'word'
            }
        }
    
    def process_text(self, text: str, language: str = 'english') -> List[int]:
        """
        Process a single text sample into token IDs.
        
        Args:
            text: Input text to process
            language: Language of the text for appropriate processing
            
        Returns:
            List of token IDs
        """
        config = self.language_configs.get(language, self.language_configs['english'])
        
        # Handle newlines based on language
        if not config['keep_newlines']:
            text = text.replace('\n', ' ')
        
        # Tokenize the text
        tokens = self.tokenizer.encode(text, add_special_tokens=True, truncation=True, max_length=self.seq_length)
        
        # Pad or truncate to sequence length
        if len(tokens) < self.seq_length:
            tokens = tokens + [self.tokenizer.pad_token_id] * (self.seq_length - len(tokens))
        else:
            tokens = tokens[:self.seq_length]
        
        return tokens
    
    def create_attention_mask(self, tokens: List[int]) -> List[int]:
        """
        Create attention mask for the tokenized sequence.
        
        Args:
            tokens: List of token IDs
            
        Returns:
            Attention mask (1 for real tokens, 0 for padding)
        """
        pad_token_id = self.tokenizer.pad_token_id
        return [1 if token != pad_token_id else 0 for token in tokens]
    
    def process_jsonl_file(self, input_path: str, output_prefix: str, language: str = 'english', num_workers: int = 4):
        """
        Process a JSONL file containing text data.
        
        Args:
            input_path: Path to input JSONL file
            output_prefix: Prefix for output binary files
            language: Language of the text data
            num_workers: Number of parallel workers for processing
        """
        logger.info(f"Processing {input_path} with {num_workers} workers...")
        
        # Read all lines from the file
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process lines in parallel
        process_func = partial(self._process_single_line, language=language)
        
        with mp.Pool(num_workers) as pool:
            results = pool.map(process_func, lines)
        
        # Filter out None results
        processed_data = [r for r in results if r is not None]
        
        # Save processed data
        self._save_binary_data(processed_data, output_prefix)
        
        logger.info(f"Processed {len(processed_data)} samples")
    
    def _process_single_line(self, line: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Process a single line from JSONL file.
        
        Args:
            line: JSON string containing text data
            language: Language for processing
            
        Returns:
            Dictionary with processed tokens and metadata
        """
        try:
            data = json.loads(line.strip())
            text = data.get('text', '')
            
            if not text:
                return None
            
            tokens = self.process_text(text, language)
            attention_mask = self.create_attention_mask(tokens)
            
            return {
                'input_ids': tokens,
                'attention_mask': attention_mask,
                'language': language,
                'original_length': len(text)
            }
        except Exception as e:
            logger.warning(f"Error processing line: {e}")
            return None
    
    def _save_binary_data(self, data: List[Dict[str, Any]], output_prefix: str):
        """
        Save processed data in binary format for fast loading.
        
        Args:
            data: List of processed samples
            output_prefix: Prefix for output files
        """
        # Prepare arrays
        input_ids = np.array([d['input_ids'] for d in data], dtype=np.int32)
        attention_masks = np.array([d['attention_mask'] for d in data], dtype=np.int8)
        
        # Save to binary files
        input_ids.tofile(f"{output_prefix}_input_ids.bin")
        attention_masks.tofile(f"{output_prefix}_attention_mask.bin")
        
        # Save metadata
        metadata = {
            'num_samples': len(data),
            'seq_length': self.seq_length,
            'vocab_size': self.vocab_size,
            'languages': list(set(d['language'] for d in data))
        }
        
        with open(f"{output_prefix}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved binary data to {output_prefix}_*.bin")
    
    def load_binary_data(self, prefix: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Load preprocessed binary data.
        
        Args:
            prefix: Prefix of the binary files
            
        Returns:
            Tuple of (input_ids, attention_masks, metadata)
        """
        # Load metadata
        with open(f"{prefix}_metadata.json", 'r') as f:
            metadata = json.load(f)
        
        # Load binary data
        input_ids = np.fromfile(f"{prefix}_input_ids.bin", dtype=np.int32)
        input_ids = input_ids.reshape(-1, metadata['seq_length'])
        
        attention_masks = np.fromfile(f"{prefix}_attention_mask.bin", dtype=np.int8)
        attention_masks = attention_masks.reshape(-1, metadata['seq_length'])
        
        logger.info(f"Loaded {metadata['num_samples']} samples from {prefix}")
        
        return input_ids, attention_masks, metadata

def main():
    """
    Example usage of the multilingual data processor.
    """
    # Example configuration
    tokenizer_path = "LLaMA-2-Tokenizer"  # Path to LLaMA-2 tokenizer
    input_file = "example.jsonl"  # Input JSONL file
    output_prefix = "processed_data/train"  # Output prefix
    language = "chinese"  # Language of the data
    
    # Initialize processor
    processor = MultilingualDataProcessor(
        tokenizer_path=tokenizer_path,
        seq_length=512
    )
    
    # Process the data
    if os.path.exists(input_file):
        processor.process_jsonl_file(
            input_path=input_file,
            output_prefix=output_prefix,
            language=language,
            num_workers=8
        )
        
        # Load and verify the processed data
        input_ids, attention_masks, metadata = processor.load_binary_data(output_prefix)
        print(f"Data shape: {input_ids.shape}")
        print(f"Metadata: {metadata}")
    else:
        # Demo with sample text
        sample_texts = {
            'english': "The quick brown fox jumps over the lazy dog.",
            'chinese': "复旦大学位于上海市，是中国著名的综合性研究型大学。",
            'arabic': "مرحبا بك في عالم الذكاء الاصطناعي",
            'vietnamese': "Xin chào thế giới học máy"
        }
        
        for lang, text in sample_texts.items():
            tokens = processor.process_text(text, language=lang)
            mask = processor.create_attention_mask(tokens)
            print(f"\n{lang.capitalize()} text processing:")
            print(f"  Original: {text[:50]}...")
            print(f"  Tokens shape: {len(tokens)}")
            print(f"  Non-padding tokens: {sum(mask)}")

if __name__ == "__main__":
    main()
```

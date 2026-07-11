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

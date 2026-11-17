#!/usr/bin/env python3
"""
IOI Dataset Usage Example

This script demonstrates how to use the IOI (Indirect Object Identification)
dataset for analyzing how transformer models identify indirect objects in sentences.
It shows prompt generation, flipping operations, and dataset manipulation.

Based on the IOIDataset class from the edge-attribution-patching repository.
"""

from typing import List, Dict, Tuple, Optional
import random
import json

class IOIDataset:
    """
    Dataset class for Indirect Object Identification tasks.
    
    This class handles the generation and manipulation of prompts for
    studying how models identify indirect objects in sentences.
    """
    
    def __init__(self, templates: Optional[List[str]] = None, 
                 names: Optional[List[List[str]]] = None,
                 nouns_dict: Optional[Dict[str, List[str]]] = None,
                 seed: int = 42):
        """
        Initialize the IOI dataset.
        
        Args:
            templates: List of sentence templates with placeholders
            names: List of name pairs for IO and S positions
            nouns_dict: Dictionary of nouns by category
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        
        # Default templates if none provided
        self.templates = templates or [
            "When [A] and [B] went to the [PLACE], [B] gave a [OBJECT] to",
            "After [A] and [B] finished [EVENT], [B] handed the [OBJECT] to",
            "[A] and [B] were at the [PLACE]. [B] passed the [OBJECT] to",
            "Yesterday, [A] and [B] visited the [PLACE]. [B] brought a [OBJECT] for"
        ]
        
        # Default names if none provided
        self.names = names or [
            ["Mary", "John"],
            ["Alice", "Bob"],
            ["Sarah", "Tom"],
            ["Emma", "James"],
            ["Lisa", "David"]
        ]
        
        # Default nouns if none provided
        self.nouns_dict = nouns_dict or {
            "PLACE": ["store", "park", "library", "restaurant", "museum"],
            "OBJECT": ["book", "drink", "gift", "letter", "package"],
            "EVENT": ["lunch", "dinner", "work", "studying", "shopping"]
        }
        
        self.generated_prompts = []
    
    def gen_prompt_uniform(self, num_prompts: int = 100) -> List[Dict]:
        """
        Generate prompts with uniform distribution across templates and names.
        
        Args:
            num_prompts: Number of prompts to generate
            
        Returns:
            List of prompt dictionaries with metadata
        """
        prompts = []
        
        for i in range(num_prompts):
            # Select template
            template = random.choice(self.templates)
            
            # Select names (IO and S)
            name_pair = random.choice(self.names)
            io_name = name_pair[0]  # Indirect Object
            s_name = name_pair[1]    # Subject
            
            # Build prompt
            prompt = template
            prompt = prompt.replace("[A]", io_name)
            prompt = prompt.replace("[B]", s_name)
            
            # Replace noun placeholders
            for placeholder, options in self.nouns_dict.items():
                if f"[{placeholder}]" in prompt:
                    prompt = prompt.replace(f"[{placeholder}]", random.choice(options))
            
            # Store with metadata
            prompt_dict = {
                "text": prompt,
                "IO": io_name,
                "S": s_name,
                "template_idx": self.templates.index(template),
                "answer": io_name  # The model should predict the IO
            }
            
            prompts.append(prompt_dict)
        
        self.generated_prompts = prompts
        return prompts
    
    def flip_words_in_prompt(self, prompt: str, word1: str, word2: str) -> str:
        """
        Flip occurrences of two words in a prompt.
        
        Args:
            prompt: Original prompt text
            word1: First word to swap
            word2: Second word to swap
            
        Returns:
            Prompt with words flipped
        """
        # Use a temporary placeholder to avoid double replacement
        temp_placeholder = "<<TEMP_PLACEHOLDER>>"
        
        flipped = prompt.replace(word1, temp_placeholder)
        flipped = flipped.replace(word2, word1)
        flipped = flipped.replace(temp_placeholder, word2)
        
        return flipped
    
    def gen_flipped_prompts(self, prompts: List[Dict], flip_type: str = "IO") -> List[Dict]:
        """
        Generate flipped versions of prompts for causal analysis.
        
        Args:
            prompts: List of original prompt dictionaries
            flip_type: Type of flip - "IO" (indirect object) or "S" (subject)
            
        Returns:
            List of flipped prompt dictionaries
        """
        flipped_prompts = []
        
        for prompt_dict in prompts:
            original_text = prompt_dict["text"]
            io_name = prompt_dict["IO"]
            s_name = prompt_dict["S"]
            
            if flip_type == "IO":
                # Flip IO position with a random other name
                available_names = [name for pair in self.names for name in pair 
                                  if name not in [io_name, s_name]]
                if available_names:
                    new_io = random.choice(available_names)
                    flipped_text = self.flip_words_in_prompt(original_text, io_name, new_io)
                    new_answer = new_io
                else:
                    # If no other names available, swap IO and S
                    flipped_text = self.flip_words_in_prompt(original_text, io_name, s_name)
                    new_answer = s_name
            
            elif flip_type == "S":
                # Flip subject and indirect object positions
                flipped_text = self.flip_words_in_prompt(original_text, s_name, io_name)
                new_answer = s_name  # Now S is in the IO position
            
            else:
                raise ValueError(f"Unknown flip type: {flip_type}")
            
            flipped_dict = {
                "text": flipped_text,
                "IO": new_io if flip_type == "IO" and available_names else 
                      (s_name if flip_type == "S" else io_name),
                "S": s_name if flip_type == "IO" else io_name,
                "template_idx": prompt_dict["template_idx"],
                "answer": new_answer,
                "original_prompt": original_text,
                "flip_type": flip_type
            }
            
            flipped_prompts.append(flipped_dict)
        
        return flipped_prompts
    
    def create_attention_masks(self, prompts: List[Dict]) -> List[List[int]]:
        """
        Create attention masks for the answer positions in prompts.
        
        Args:
            prompts: List of prompt dictionaries
            
        Returns:
            List of attention masks (1 for answer position, 0 elsewhere)
        """
        masks = []
        
        for prompt_dict in prompts:
            text = prompt_dict["text"]
            answer = prompt_dict["answer"]
            
            # Simple tokenization (in practice, use model's tokenizer)
            tokens = text.split()
            
            # Create mask
            mask = []
            for i, token in enumerate(tokens):
                if answer in token:
                    # This is the position we care about
                    mask.append(1)
                else:
                    mask.append(0)
            
            masks.append(mask)
        
        return masks
    
    def get_paired_prompts(self, num_pairs: int = 50) -> List[Tuple[Dict, Dict]]:
        """
        Generate pairs of original and flipped prompts for comparison.
        
        Args:
            num_pairs: Number of prompt pairs to generate
            
        Returns:
            List of (original, flipped) prompt tuples
        """
        # Generate original prompts
        original_prompts = self.gen_prompt_uniform(num_pairs)
        
        # Generate flipped versions
        flipped_prompts = self.gen_flipped_prompts(original_prompts, flip_type="IO")
        
        # Pair them up
        pairs = list(zip(original_prompts, flipped_prompts))
        
        return pairs
    
    def save_dataset(self, filepath: str):
        """
        Save the generated dataset to a JSON file.
        
        Args:
            filepath: Path to save the dataset
        """
        dataset = {
            "templates": self.templates,
            "names": self.names,
            "nouns_dict": self.nouns_dict,
            "prompts": self.generated_prompts
        }
        
        with open(filepath, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        print(f"Dataset saved to {filepath}")
    
    def load_dataset(self, filepath: str):
        """
        Load a dataset from a JSON file.
        
        Args:
            filepath: Path to the dataset file
        """
        with open(filepath, 'r') as f:
            dataset = json.load(f)
        
        self.templates = dataset["templates"]
        self.names = dataset["names"]
        self.nouns_dict = dataset["nouns_dict"]
        self.generated_prompts = dataset["prompts"]
        
        print(f"Dataset loaded from {filepath}")

def demonstrate_ioi_dataset():
    """Demonstrate the IOI dataset functionality."""
    
    print("=" * 60)
    print("IOI Dataset Demonstration")
    print("=" * 60)
    
    # Initialize dataset
    dataset = IOIDataset()
    
    # Generate prompts
    print("\n1. Generating uniform prompts...")
    prompts = dataset.gen_prompt_uniform(num_prompts=5)
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\nPrompt {i}:")
        print(f"  Text: {prompt['text']}")
        print(f"  Answer (IO): {prompt['answer']}")
        print(f"  Subject: {prompt['S']}")
    
    # Generate flipped prompts
    print("\n" + "=" * 60)
    print("2. Generating flipped prompts (IO flip)...")
    flipped_prompts = dataset.gen_flipped_prompts(prompts, flip_type="IO")
    
    for i, (orig, flip) in enumerate(zip(prompts[:3], flipped_prompts[:3]), 1):
        print(f"\nPair {i}:")
        print(f"  Original: {orig['text']}")
        print(f"  Flipped:  {flip['text']}")
        print(f"  Original answer: {orig['answer']}")
        print(f"  Flipped answer:  {flip['answer']}")
    
    # Generate subject-flipped prompts
    print("\n" + "=" * 60)
    print("3. Generating subject-flipped prompts...")
    s_flipped = dataset.gen_flipped_prompts(prompts, flip_type="S")
    
    for i, (orig, flip) in enumerate(zip(prompts[:2], s_flipped[:2]), 1):
        print(f"\nPair {i}:")
        print(f"  Original: {orig['text']}")
        print(f"  S-Flipped: {flip['text']}")
    
    # Create attention masks
    print("\n" + "=" * 60)
    print("4. Creating attention masks...")
    masks = dataset.create_attention_masks(prompts[:2])
    
    for i, (prompt, mask) in enumerate(zip(prompts[:2], masks), 1):
        print(f"\nPrompt {i}: {prompt['text']}")
        print(f"  Tokens: {prompt['text'].split()}")
        print(f"  Mask:   {mask}")
    
    # Get paired prompts for analysis
    print("\n" + "=" * 60)
    print("5. Generating paired prompts for causal analysis...")
    pairs = dataset.get_paired_prompts(num_pairs=3)
    
    for i, (orig, flip) in enumerate(pairs, 1):
        print(f"\nAnalysis Pair {i}:")
        print(f"  Control:     {orig['text']} → {orig['answer']}")
        print(f"  Intervention: {flip['text']} → {flip['answer']}")
    
    # Save dataset example
    print("\n" + "=" * 60)
    print("6. Dataset saving example...")
    # dataset.save_dataset("ioi_dataset_example.json")
    print("  (Dataset saving demonstrated - uncomment to actually save)")
    
    print("\n" + "=" * 60)
    print("IOI Dataset demonstration complete!")
    print("=" * 60)

if __name__ == "__main__":
    demonstrate_ioi_dataset()

---
name: attribution-patching
description: Use when analyzing neural network circuits, performing attribution patching, automated circuit discovery, or investigating model interpretability through edge attribution methods in transformer models
---

## Demo Scripts

### `scripts/ioi_dataset_usage.py`

```python
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
```

### `scripts/run_attribution_patching.py`

```python
#!/usr/bin/env python3
"""
Edge Attribution Patching Example Script

This script demonstrates how to use the edge attribution patching framework
for automated circuit discovery in transformer models. It shows how to:
1. Set up an experiment with a specific task
2. Run attribution patching with different configurations
3. Analyze and save results

Requires: pip install transformer-lens torch numpy
"""

import json
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PatchingConfig:
    """Configuration for attribution patching experiments."""
    task: str  # 'ioi', 'greaterthan', or 'docstring'
    model_name: str
    threshold: float = 0.1
    use_abs_value: bool = True
    num_samples: int = 100
    batch_size: int = 10
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

class AttributionPatchingExperiment:
    """
    Main class for running edge attribution patching experiments.
    
    This demonstrates the core API for performing attribution patching
    to discover important circuits in transformer models.
    """
    
    def __init__(self, config: PatchingConfig):
        """
        Initialize the attribution patching experiment.
        
        Args:
            config: Configuration object with experiment parameters
        """
        self.config = config
        self.model = None
        self.dataset = None
        self.results = {
            'pruned_heads': [],
            'pruned_attrs': [],
            'num_passes': 0,
            'final_score': 0.0
        }
    
    def setup_model(self):
        """
        Load and configure the transformer model for analysis.
        
        Note: In actual implementation, this would load from TransformerLens
        """
        print(f"Loading model: {self.config.model_name}")
        # Placeholder for model loading
        # In practice: self.model = load_transformer_model(self.config.model_name)
        self.model = {'name': self.config.model_name, 'loaded': True}
    
    def prepare_dataset(self) -> Dict:
        """
        Prepare task-specific dataset for attribution patching.
        
        Returns:
            Dictionary containing prompts and labels for the task
        """
        print(f"Preparing dataset for task: {self.config.task}")
        
        if self.config.task == 'ioi':
            # IOI task: Indirect Object Identification
            dataset = {
                'prompts': [
                    "When Mary and John went to the store, John gave a drink to",
                    "After Tom and Sarah finished dinner, Sarah passed the salt to",
                ],
                'labels': ['Mary', 'Tom'],
                'task_type': 'indirect_object'
            }
        elif self.config.task == 'greaterthan':
            # Greater-than comparison task
            dataset = {
                'prompts': [
                    "Compare 5 and 3: The larger number is",
                    "Between 10 and 7, the greater value is",
                ],
                'labels': ['5', '10'],
                'task_type': 'comparison'
            }
        elif self.config.task == 'docstring':
            # Docstring generation task
            dataset = {
                'prompts': [
                    "def add(a, b):\n    '''",
                    "def multiply(x, y):\n    '''",
                ],
                'labels': [
                    'Add two numbers together',
                    'Multiply two numbers'
                ],
                'task_type': 'generation'
            }
        else:
            raise ValueError(f"Unknown task: {self.config.task}")
        
        self.dataset = dataset
        return dataset
    
    def compute_attributions(self, prompt: str, label: str) -> np.ndarray:
        """
        Compute edge attributions for a given prompt-label pair.
        
        Args:
            prompt: Input prompt text
            label: Expected output label
            
        Returns:
            Attribution matrix for model edges
        """
        # Placeholder for attribution computation
        # In practice, this would use gradient-based attribution methods
        print(f"Computing attributions for prompt: {prompt[:50]}...")
        
        # Simulate attribution matrix (layers x heads x embedding_dim)
        n_layers = 12
        n_heads = 12
        attribution_matrix = np.random.randn(n_layers, n_heads)
        
        if self.config.use_abs_value:
            attribution_matrix = np.abs(attribution_matrix)
        
        return attribution_matrix
    
    def prune_edges(self, attributions: np.ndarray, threshold: float) -> Tuple[List, List]:
        """
        Prune edges based on attribution scores and threshold.
        
        Args:
            attributions: Attribution matrix
            threshold: Pruning threshold
            
        Returns:
            Tuple of (pruned_heads, pruned_attrs)
        """
        pruned_heads = []
        pruned_attrs = []
        
        for layer_idx in range(attributions.shape[0]):
            for head_idx in range(attributions.shape[1]):
                attr_value = attributions[layer_idx, head_idx]
                
                if attr_value < threshold:
                    pruned_heads.append((layer_idx, head_idx))
                    pruned_attrs.append(float(attr_value))
        
        return pruned_heads, pruned_attrs
    
    def run_attribution_patching(self) -> Dict:
        """
        Run the complete attribution patching pipeline.
        
        Returns:
            Dictionary containing experiment results
        """
        print("Starting attribution patching experiment...")
        
        # Setup
        self.setup_model()
        dataset = self.prepare_dataset()
        
        all_attributions = []
        
        # Process each prompt-label pair
        for prompt, label in zip(dataset['prompts'], dataset['labels']):
            attrs = self.compute_attributions(prompt, label)
            all_attributions.append(attrs)
        
        # Aggregate attributions
        mean_attributions = np.mean(all_attributions, axis=0)
        
        # Iterative pruning
        current_threshold = self.config.threshold
        num_passes = 0
        max_passes = 10
        
        while num_passes < max_passes:
            num_passes += 1
            print(f"Pass {num_passes}: Pruning with threshold {current_threshold:.3f}")
            
            pruned_heads, pruned_attrs = self.prune_edges(
                mean_attributions, current_threshold
            )
            
            # Check convergence (simplified)
            if len(pruned_heads) > len(mean_attributions.flatten()) * 0.9:
                print("Convergence reached")
                break
            
            # Adaptive threshold update
            current_threshold *= 1.1
        
        # Store results
        self.results['pruned_heads'] = pruned_heads
        self.results['pruned_attrs'] = pruned_attrs
        self.results['num_passes'] = num_passes
        self.results['final_score'] = self.evaluate_circuit()
        
        return self.results
    
    def evaluate_circuit(self) -> float:
        """
        Evaluate the discovered circuit's performance.
        
        Returns:
            Performance score of the pruned circuit
        """
        # Placeholder evaluation
        # In practice, this would test the pruned model on held-out data
        num_edges_remaining = len(self.results['pruned_heads'])
        total_edges = 12 * 12  # layers * heads
        sparsity = 1.0 - (num_edges_remaining / total_edges)
        
        # Simulate performance score (higher sparsity with maintained accuracy)
        performance_score = 0.8 + 0.2 * sparsity
        
        return performance_score
    
    def save_results(self, output_path: str):
        """
        Save experiment results to JSON files.
        
        Args:
            output_path: Directory path for saving results
        """
        # Save pruned heads
        with open(f"{output_path}/pruned_heads_{self.config.task}.json", 'w') as f:
            json.dump(self.results['pruned_heads'], f, indent=2)
        
        # Save pruned attributions
        with open(f"{output_path}/pruned_attrs_{self.config.task}.json", 'w') as f:
            json.dump(self.results['pruned_attrs'], f, indent=2)
        
        # Save summary
        summary = {
            'task': self.config.task,
            'model': self.config.model_name,
            'threshold': self.config.threshold,
            'use_abs_value': self.config.use_abs_value,
            'num_passes': self.results['num_passes'],
            'final_score': self.results['final_score'],
            'num_pruned_edges': len(self.results['pruned_heads'])
        }
        
        with open(f"{output_path}/summary_{self.config.task}.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Results saved to {output_path}")

def main():
    """Main function demonstrating the attribution patching workflow."""
    
    # Example 1: IOI Task
    print("=" * 50)
    print("Running IOI Task Attribution Patching")
    print("=" * 50)
    
    ioi_config = PatchingConfig(
        task='ioi',
        model_name='gpt2-small',
        threshold=0.1,
        use_abs_value=True
    )
    
    ioi_exp = AttributionPatchingExperiment(ioi_config)
    ioi_results = ioi_exp.run_attribution_patching()
    
    print(f"\nIOI Results:")
    print(f"  Pruned {len(ioi_results['pruned_heads'])} edges")
    print(f"  Completed in {ioi_results['num_passes']} passes")
    print(f"  Final score: {ioi_results['final_score']:.3f}")
    
    # Example 2: Greater-than Task
    print("\n" + "=" * 50)
    print("Running Greater-than Task Attribution Patching")
    print("=" * 50)
    
    gt_config = PatchingConfig(
        task='greaterthan',
        model_name='gpt2-small',
        threshold=0.15,
        use_abs_value=True
    )
    
    gt_exp = AttributionPatchingExperiment(gt_config)
    gt_results = gt_exp.run_attribution_patching()
    
    print(f"\nGreater-than Results:")
    print(f"  Pruned {len(gt_results['pruned_heads'])} edges")
    print(f"  Completed in {gt_results['num_passes']} passes")
    print(f"  Final score: {gt_results['final_score']:.3f}")
    
    # Example 3: Docstring Task
    print("\n" + "=" * 50)
    print("Running Docstring Task Attribution Patching")
    print("=" * 50)
    
    doc_config = PatchingConfig(
        task='docstring',
        model_name='gpt2-medium',
        threshold=0.08,
        use_abs_value=False  # Try without absolute value
    )
    
    doc_exp = AttributionPatchingExperiment(doc_config)
    doc_results = doc_exp.run_attribution_patching()
    
    print(f"\nDocstring Results:")
    print(f"  Pruned {len(doc_results['pruned_heads'])} edges")
    print(f"  Completed in {doc_results['num_passes']} passes")
    print(f"  Final score: {doc_results['final_score']:.3f}")
    
    # Save all results
    print("\n" + "=" * 50)
    print("Saving Results")
    print("=" * 50)
    
    # Note: In practice, create output directory first
    # ioi_exp.save_results("./results/ioi_task")
    # gt_exp.save_results("./results/greaterthan_task")
    # doc_exp.save_results("./results/docstring_task")
    
    print("\nAll experiments completed successfully!")

if __name__ == "__main__":
    main()
```

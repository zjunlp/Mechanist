# Linguistic Regions in LLMs - API Reference

## Module: data_preprocess.preprocess-llama

### Class: CustomLanguageVars

Handles language-specific variables for text preprocessing.

**Methods:**

#### select_nl_marker(language: str) -> str
Select appropriate newline marker based on language.

**Parameters:**
- `language` (str): Target language for processing

**Returns:**
- `str`: Newline marker string

---

### Class: IdentitySplitter

Default text splitter for non-Chinese languages.

**Methods:**

#### split(text: str) -> List[str]
Split text using default word-based splitting.

**Parameters:**
- `text` (str): Input text to split

**Returns:**
- `List[str]`: List of text segments

---

### Class: ChineseSplitter

Specialized text splitter for Chinese language processing.

**Methods:**

#### split(text: str) -> List[str]
Split Chinese text using character-based segmentation.

**Parameters:**
- `text` (str): Chinese text to split

**Returns:**
- `List[str]`: List of segmented text pieces

---

### Function: _warmup_mmap_file(path: str) -> None

Warm up memory-mapped file for faster access.

**Parameters:**
- `path` (str): Path to the file to warm up

**Returns:**
- `None`

---

### Function: count_lines(path: str) -> int

Count number of lines in a file efficiently.

**Parameters:**
- `path` (str): Path to the file

**Returns:**
- `int`: Number of lines in the file

---

### Function: get_args() -> argparse.Namespace

Parse command-line arguments for data preprocessing.

**Returns:**
- `argparse.Namespace`: Parsed arguments including:
  - `mode`: 'write' or 'read' mode
  - `file_path`: Input file path
  - `save_prefix`: Prefix for output files
  - `save_path`: Directory to save processed data
  - `language`: Target language
  - `seq_length`: Sequence length for tokenization
  - `tokenizer_path`: Path to tokenizer
  - `num_workers`: Number of parallel workers

---

## Module: region_selection

### Function: jaccard_similarity(tensor1: torch.Tensor, tensor2: torch.Tensor) -> float

Calculate Jaccard similarity between two tensors.

**Parameters:**
- `tensor1` (torch.Tensor): First tensor for comparison
- `tensor2` (torch.Tensor): Second tensor for comparison

**Returns:**
- `float`: Jaccard similarity score (0-1)

**Example:**
```python
import torch
from region_selection import jaccard_similarity

tensor1 = torch.tensor([1, 0, 1, 1, 0])
tensor2 = torch.tensor([1, 1, 0, 1, 0])
similarity = jaccard_similarity(tensor1, tensor2)
print(f"Similarity: {similarity}")  # Output: 0.6
```

---

### Function: compare_bool_matrix(bool_dict1: Dict, bool_dict2: Dict) -> Dict[str, float]

Compare boolean matrices from two dictionaries.

**Parameters:**
- `bool_dict1` (Dict): First dictionary with boolean matrices
- `bool_dict2` (Dict): Second dictionary with boolean matrices

**Returns:**
- `Dict[str, float]`: Dictionary mapping keys to similarity scores

---

### Function: logical_and_bool_matrix(bool_dict1: Dict, bool_dict2: Dict) -> Dict

Perform element-wise logical AND between boolean matrices.

**Parameters:**
- `bool_dict1` (Dict): First dictionary with boolean matrices
- `bool_dict2` (Dict): Second dictionary with boolean matrices

**Returns:**
- `Dict`: Dictionary with AND results

---

## Module: training.step1_supervised_finetuning

### Class: MyDataCollatorForSupervisedDataset

Custom data collator for supervised fine-tuning with support for multilingual batching.

**Constructor:**
```python
MyDataCollatorForSupervisedDataset(
    tokenizer: PreTrainedTokenizer,
    padding: bool = True,
    max_length: Optional[int] = None,
    pad_to_multiple_of: Optional[int] = None
)
```

**Parameters:**
- `tokenizer` (PreTrainedTokenizer): Tokenizer for text processing
- `padding` (bool): Whether to pad sequences
- `max_length` (int, optional): Maximum sequence length
- `pad_to_multiple_of` (int, optional): Pad to multiple of this value

**Methods:**

#### __call__(features: List[Dict]) -> Dict[str, torch.Tensor]
Collate batch of examples.

**Parameters:**
- `features` (List[Dict]): List of feature dictionaries

**Returns:**
- `Dict[str, torch.Tensor]`: Batched tensors with keys:
  - `input_ids`: Token IDs
  - `attention_mask`: Attention masks
  - `labels`: Target labels for training

---

### Class: MyDataset

Dataset class for loading preprocessed binary data.

**Constructor:**
```python
MyDataset(
    data_prefix: str,
    seq_length: int,
    num_samples: Optional[int] = None
)
```

**Parameters:**
- `data_prefix` (str): Prefix path to binary data files
- `seq_length` (int): Sequence length
- `num_samples` (int, optional): Number of samples to load

**Methods:**

#### __len__() -> int
Get dataset length.

**Returns:**
- `int`: Number of samples in dataset

#### __getitem__(idx: int) -> Dict[str, torch.Tensor]
Get a single sample.

**Parameters:**
- `idx` (int): Sample index

**Returns:**
- `Dict[str, torch.Tensor]`: Sample dictionary with input_ids and attention_mask

---

### Function: set_first_false_to_true(mask_tensor: torch.Tensor) -> torch.Tensor

Set the first False value in mask to True (used for gradient accumulation).

**Parameters:**
- `mask_tensor` (torch.Tensor): Boolean mask tensor

**Returns:**
- `torch.Tensor`: Modified mask tensor

---

### Function: _make_supervised_data_module(args, train_data_prefix: str, eval_data_prefix: str) -> Dict

Create data module for supervised training.

**Parameters:**
- `args`: Training arguments
- `train_data_prefix` (str): Prefix for training data
- `eval_data_prefix` (str): Prefix for evaluation data

**Returns:**
- `Dict`: Dictionary containing:
  - `train_dataset`: Training dataset
  - `eval_dataset`: Evaluation dataset
  - `data_collator`: Data collator instance

---

### Function: parse_args() -> argparse.Namespace

Parse command-line arguments for training.

**Returns:**
- `argparse.Namespace`: Parsed arguments including:
  - `model_name_or_path`: Path to pretrained model
  - `pretrain_train_data_path`: Path to training data
  - `pretrain_test_data_path`: Path to test data
  - `max_seq_len`: Maximum sequence length
  - `learning_rate`: Learning rate
  - `weight_decay`: Weight decay coefficient
  - `per_device_train_batch_size`: Training batch size
  - `gradient_accumulation_steps`: Gradient accumulation steps
  - `zero_stage`: DeepSpeed zero stage
  - `output_dir`: Output directory for checkpoints

---

## Module: training.utils.data

### Module: raw_datasets

Functions for loading and processing raw datasets.

#### load_dataset_from_path(path: str) -> Dataset
Load dataset from file path.

**Parameters:**
- `path` (str): Path to dataset file

**Returns:**
- `Dataset`: Loaded dataset object

---

### Module: data_utils

Utilities for data processing and manipulation.

#### create_prompt_dataset(data_path: str, tokenizer: PreTrainedTokenizer) -> Dataset
Create prompt dataset for training.

**Parameters:**
- `data_path` (str): Path to raw data
- `tokenizer` (PreTrainedTokenizer): Tokenizer instance

**Returns:**
- `Dataset`: Processed dataset with prompts

---

## Module: training.utils.model

### Module: model_utils

Model initialization and configuration utilities.

#### create_hf_model(model_name_or_path: str, **kwargs) -> PreTrainedModel
Create Hugging Face model from name or path.

**Parameters:**
- `model_name_or_path` (str): Model identifier or path
- `kwargs`: Additional model configuration

**Returns:**
- `PreTrainedModel`: Initialized model

---

## Module: training.utils

### Module: ds_utils

DeepSpeed utilities for distributed training.

#### get_train_ds_config(args) -> Dict
Generate DeepSpeed configuration for training.

**Parameters:**
- `args`: Training arguments

**Returns:**
- `Dict`: DeepSpeed configuration dictionary

---

### Module: utils

General utility functions.

#### print_rank_0(message: str) -> None
Print message only on rank 0 process.

**Parameters:**
- `message` (str): Message to print

#### save_hf_format(model, tokenizer, output_dir: str) -> None
Save model in Hugging Face format.

**Parameters:**
- `model`: Model to save
- `tokenizer`: Tokenizer to save
- `output_dir` (str): Directory to save model

#### set_random_seed(seed: int) -> None
Set random seed for reproducibility.

**Parameters:**
- `seed` (int): Random seed value

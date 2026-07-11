# FF-Layers API Reference

## Module: analysis.generate_outputs

Main module for extracting activations, trigger examples, and predictions from transformer models.

### Functions

#### parse_line(line: str) -> str
Parse a single line from the data file.

**Parameters:**
- `line` (str): Input line to parse

**Returns:**
- `str`: Parsed line content

---

#### parse_data_file(args: argparse.Namespace, shuffle: bool = False) -> List[str]
Parse the data file and return list of sentences.

**Parameters:**
- `args` (argparse.Namespace): Command-line arguments containing data_file path
- `shuffle` (bool, optional): Whether to shuffle the data. Defaults to False.

**Returns:**
- `List[str]`: List of parsed sentences

---

#### format_ffn_values(hypos: List, sentences: List[str], pos_neg: str) -> Dict
Format FFN values from model hypotheses.

**Parameters:**
- `hypos` (List): Model hypotheses/predictions
- `sentences` (List[str]): Input sentences
- `pos_neg` (str): Positive or negative extraction mode

**Returns:**
- `Dict`: Formatted FFN values with activations and predictions

---

### Command-Line Arguments

#### Main Arguments
- `--data_file` (str, required): Path to tokenized data file
- `--model_dir` (str, required): Path to model checkpoint directory
- `--output_file` (str, required): Path for output file

#### Extraction Modes
- `--get_trigger_examples`: Extract trigger examples for keys
- `--extract_ffn_info`: Extract FFN layer information
- `--extract_mode` (str): Extraction mode - 'dim', 'layer', or 'layer-raw'

#### Processing Options
- `--max_sentences` (int): Maximum sentences to process (-1 for all)
- `--top_k_trigger_examples` (int): Number of top trigger examples per key
- `--dims_for_analysis` (List[int]): Specific dimensions to analyze

---

## Module: analysis.key_value_agreement

Module for computing agreement between keys and values in transformer layers.

### Functions

#### get_model(model_dir: str) -> fairseq.models.Model
Load the transformer model from checkpoint.

**Parameters:**
- `model_dir` (str): Path to model checkpoint directory

**Returns:**
- `fairseq.models.Model`: Loaded transformer model

**Example:**
```python
model = get_model('checkpoints/adaptive_lm_wiki103.v2/')
```

---

#### load_vocab(model_dir: str) -> Dict[str, int]
Load vocabulary from model directory.

**Parameters:**
- `model_dir` (str): Path to model checkpoint directory

**Returns:**
- `Dict[str, int]`: Vocabulary mapping from tokens to indices

---

#### get_target_counts(catalog_dir: str) -> Dict[Tuple[int, int], Dict[str, int]]
Get target word counts from trigger examples catalog.

**Parameters:**
- `catalog_dir` (str): Directory containing trigger example files

**Returns:**
- `Dict[Tuple[int, int], Dict[str, int]]`: Mapping of (layer, dimension) to target word counts

---

### Command-Line Arguments

- `--model_dir` (str, required): Path to model checkpoint directory
- `--data_dir` (str, required): Directory with trigger examples (textual format)
- `--output_base` (str, required): Base name for output files (.tsv and .json)

---

## Module: analysis.trigger_examples_jsonl_to_textual

Module for converting JSONL trigger examples to readable text format.

### Functions

#### convert_jsonl_to_text(input_file: str, model_dir: str, output_dir: str) -> None
Convert JSONL formatted trigger examples to individual text files.

**Parameters:**
- `input_file` (str): Path to input JSONL file
- `model_dir` (str): Path to model checkpoint directory  
- `output_dir` (str): Directory for output text files

**Output:**
Creates one text file per key in the output directory with format:
- Filename: `layer{L}_dim{D}.txt`
- Content: Ranked trigger examples with activation values

---

### Command-Line Arguments

- `--input_file` (str, required): Path to input JSONL file
- `--model_dir` (str, required): Path to model checkpoint directory
- `--output_dir` (str, required): Output directory for text files

---

## Data Structures

### Trigger Example Format (JSONL)
```json
{
    "layer": 5,
    "dimension": 222,
    "examples": [
        {
            "text": "example sentence",
            "activation": 12.345,
            "rank": 1
        }
    ]
}
```

### Key-Value Agreement Output (TSV)
| Column | Type | Description |
|--------|------|-------------|
| layer | int | Layer index |
| dimension | int | Dimension index |
| agreement | float | Agreement score |
| top_predictions | str | Top predicted tokens |
| trigger_overlap | float | Overlap with trigger examples |

### FFN Predictions DataFrame (Pickle)
| Column | Type | Description |
|--------|------|-------------|
| sentence | str | Input sentence |
| layer | int | Layer index |
| predictions | List[str] | Predicted tokens |
| activations | np.ndarray | Activation values |
| dimension | int | Dimension (if extract_mode='dim') |

---

## Performance Considerations

### Memory Requirements
- **Trigger Example Extraction**: Standard GPU memory
- **Key-Value Agreement**: ~150GB RAM
- **Dimension-level Extraction**: High memory usage, scales with model size

### Running Time Estimates (NVIDIA RTX 3090)
| Operation | Configuration | Time |
|-----------|--------------|------|
| Trigger extraction | 1000 sentences | ~0.75 hours |
| Layer-level extraction | Full validation | ~9.8 hours |
| Dimension-level extraction | 1000 sentences | ~4.2 hours |

### Parallelization Options
- Split data files for parallel processing on multiple GPUs
- Use batch processing for large datasets
- Consider using subset for initial testing

---

## Error Handling

### Common Errors and Solutions

#### OutOfMemoryError
- Reduce `max_sentences` parameter
- Use layer-level instead of dimension-level extraction
- Increase system RAM for key-value agreement

#### FileNotFoundError
- Verify model checkpoint path
- Ensure data preprocessing is complete
- Check output directory permissions

#### CUDA Error
- Verify CUDA installation and GPU availability
- Set `CUDA_VISIBLE_DEVICES` for specific GPU
- Consider CPU-only mode for debugging

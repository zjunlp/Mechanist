---
name: representation-engineering
description: "Use this skill when working with Representation Engineering (RepE) for AI transparency, monitoring, or controlling internal representations of large language models including truthfulness detection, emotion control, harmlessness steering, and memorization analysis."
---

## Method and use

Extract concept directions with representation-reading procedures and use controlled activation edits to test behavior. Pair contrasts carefully, specify token pooling and layers, and calibrate side effects. Direction recoverability, controllability, and a uniquely identified mechanism are distinct conclusions.


# Representation Engineering (RepE)

## When to Use
Activate this skill when you need to:
- Monitor or manipulate internal representations of LLMs for transparency
- Detect or control truthfulness, honesty, or deception in language models
- Steer model behavior (emotions, fairness, harmlessness) using representation vectors
- Implement RepReading (classification via internal representations) or RepControl (generation steering)
- Analyze memorization or power-seeking behaviors in LLMs
- Use contrast vectors for safety-relevant interventions
- Build upon Hugging Face pipelines with representation-level control

Keywords: representation engineering, RepE, RepReading, RepControl, AI transparency, contrast vectors, LAT (Linear Artificial Tomography), honesty detection, emotion control, LLM steering, internal representations, cognitive neuroscience AI

## Quick Reference
- **Paper:** https://arxiv.org/abs/2310.01405
- **Website & Demo:** https://www.ai-transparency.org/
- **GitHub:** https://github.com/andyzoujm/representation-engineering
- **Examples directory:** `examples/` (honesty, emotions, fairness, memorization, harmless/harmful)
- **HuggingFace pipelines docs:** https://huggingface.co/docs/transformers/main_classes/pipelines

## Installation

### Prerequisites
- Python 3.8+
- PyTorch
- Hugging Face `transformers`

### Install from GitHub
```bash
git clone https://github.com/andyzoujm/representation-engineering.git
cd representation-engineering
pip install -e .
```

## Core Features
- **RepReading Pipeline:** Classifies internal representations across model layers using linear probes (PCA-based direction finding)
- **RepControl Pipeline:** Steers generation by injecting representation directions into model hidden states
- **HuggingFace Integration:** Both pipelines inherit from HuggingFace's pipeline API for compatibility
- **RepE_eval Framework:** Evaluation framework based on RepReading as an alternative to zero-shot/few-shot baselines
- **Multi-concept Support:** Honesty, emotions, fairness, memorization, harmlessness, power-seeking
- **LoRRA Finetuning:** Representation-aware finetuning support via `lorra_finetune/`
- **Built-in Datasets:** Emotions, facts, memorization data in `data/`

## Usage Examples

### Register Pipelines and Initialize
```python
from repe import repe_pipeline_registry  # register 'rep-reading' and 'rep-control' tasks into Hugging Face pipelines
repe_pipeline_registry()

# ... initializing model and tokenizer ....

rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)
rep_control_pipeline = pipeline("rep-control", model=model, tokenizer=tokenizer, **control_kwargs)
```

### Honesty Detection Example (from examples/honesty)
```python
from repe import repe_pipeline_registry
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from examples.honesty.utils import honesty_function_dataset

repe_pipeline_registry()

model_name = "meta-llama/Llama-2-13b-chat-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

# Build dataset of honest vs dishonest statements
train_data, test_data = honesty_function_dataset(
    data_path="data/facts/facts_true_false.csv",
    tokenizer=tokenizer,
    user_tag="[INST]",
    assistant_tag="[/INST]"
)

rep_reading_pipeline = pipeline("rep-reading", model=model, tokenizer=tokenizer)

# Train a rep reader (linear probe) on honesty direction
rep_reader = rep_reading_pipeline.get_directions(
    train_data["data"],
    rep_token=-1,
    hidden_layers=list(range(-1, -model.config.num_hidden_layers, -1)),
    n_difference=1,
    train_labels=train_data["labels"],
    direction_method="pca",
)
```

### Emotion Control Example
```python
from examples.primary_emotions.utils import primary_emotions_concept_dataset

# Build emotion concept dataset
emotions_data = primary_emotions_concept_dataset(
    data_dir="data/emotions",
    user_tag="[INST]",
    assistant_tag="[/INST]"
)

# Use rep_control_pipeline to steer generation toward a target emotion
rep_control_pipeline = pipeline(
    "rep-control",
    model=model,
    tokenizer=tokenizer,
    layers=list(range(-5, -18, -1)),
    block_name="decoder_block"
)
```

## Key APIs / Models

### Pipeline Tasks
| Task | Description |
|------|-------------|
| `"rep-reading"` | Read/classify internal representations |
| `"rep-control"` | Steer generation via representation injection |

### Supported Models (from examples)
- `meta-llama/Llama-2-13b-chat-hf`
- `meta-llama/Llama-2-7b-chat-hf`
- `mistralai/Mistral-7B-Instruct-v0.1`
- `meta-llama/Meta-Llama-3-8B-Instruct`
- Any HuggingFace CausalLM with decoder layers

### Direction Methods
- `"pca"` — Principal Component Analysis (default, most common)
- `"cluster_mean"` — Cluster mean difference

### Key Parameters for `get_directions`
- `rep_token` (int): Token position to extract representation from (e.g., `-1` for last token)
- `hidden_layers` (list): Layer indices to extract from
- `n_difference` (int): Number of contrastive pairs
- `train_labels` (list): Labels for supervised direction finding
- `direction_method` (str): Method for finding direction (`"pca"`)

### RepControl Parameters
- `layers` (list): Layers at which to inject the control vector
- `block_name` (str): Name of the transformer block (e.g., `"decoder_block"`)
- `control_coeff` (float): Coefficient scaling the control vector injection

## Data Formats

### Honesty Dataset (`data/facts/facts_true_false.csv`)
CSV with columns for statement text and true/false label.

### Emotions Dataset (`data/emotions/*.json`)
JSON files per emotion with prompt-completion pairs.

### Memorization Dataset
- `data/memorization/quotes/` — Popular quotes, unseen quotes, completions
- `data/memorization/literary_openings/` — Real vs. fake literary openings

## Common Patterns & Best Practices

1. **Tag Format:** Always match `user_tag`/`assistant_tag` to your model's chat template (e.g., `[INST]`/`[/INST]` for LLaMA-2 chat).
2. **Layer Selection:** Typically use middle-to-later layers for semantic concepts; iterate over `range(-1, -num_layers, -1)`.
3. **PCA Direction:** Use `direction_method="pca"` for robust concept directions; the sign of the direction may need flipping depending on dataset ordering.
4. **Control Coefficient:** Start with small values (e.g., `±10` to `±20`) and tune; large values can degrade fluency.
5. **Contrastive Pairs:** Dataset should contain paired positive/negative examples for clean direction extraction.
6. **RepE_eval:** Use `repe_eval/` as an additional evaluation baseline on standard benchmarks alongside zero-shot/few-shot.

## Demo Scripts

### `scripts/repe_demo.py`


See [`scripts/repe_demo.py`](scripts/repe_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

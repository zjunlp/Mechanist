---
name: transcoder-circuits
description: "Use this skill when working with transcoder-based circuit analysis of large language models, including training transcoders, analyzing MLP sublayers, reverse-engineering LLM circuits, and creating feature dashboards for interpretability research."
---

## Method and use

Model a sublayer input-output mapping with sparse features for circuit analysis and replacement experiments. Unlike an activation-reconstructing SAE, a transcoder approximates the sublayer computation. Evaluate replacement errors and the scope of the recovered circuit.


# Transcoder Circuits: Reverse-Engineering LLM Circuits with Transcoders

## When to Use

Activate this skill when:
- Reverse-engineering circuits inside transformer language models (GPT-2, Pythia, etc.)
- Training transcoders to decompose MLP sublayers into sparse linear combinations of features
- Analyzing interpretable features in LLMs using sparse autoencoders or transcoders
- Building feature dashboards or activation visualizations
- Performing mechanistic interpretability research on neural networks
- Comparing SAE vs. transcoder feature interpretability
- Running circuit analysis, replacement contexts, or activation patching

**Keywords:** transcoder, SAE, sparse autoencoder, mechanistic interpretability, LLM circuits, MLP features, GPT-2, Pythia, feature dashboard, circuit analysis, activation patching

## Quick Reference

- **Repository:** https://github.com/jacobdunefsky/transcoder_circuits
- **Transcoder Weights (HuggingFace):** https://huggingface.co/pchlenski/gpt2-transcoders
- **SAELens (upstream SAE code):** https://github.com/jbloomAus/SAELens
- **Walkthrough Notebook:** `walkthrough.ipynb`

## Installation / Setup

### Prerequisites
- Python 3.8+
- CUDA-capable GPU recommended

### Quick Setup (from README)
```bash
bash setup.sh
```

This script installs dependencies and downloads transcoder weights from HuggingFace (`pchlenski/gpt2-transcoders`).

### Manual Installation
```bash
pip install -r requirements.txt
```

### Requirements (from requirements.txt)
Key dependencies include:
- `transformer_lens` — for loading and hooking into transformer models
- `torch` — PyTorch
- `einops`
- `datasets`
- `huggingface_hub`
- `wandb` (optional, for training logging)

## Core Features

- **Transcoder Training:** Train transcoders on LLM MLP sublayers to decompose activations into sparse interpretable features (`sae_training/`)
- **Circuit Analysis:** Reverse-engineer fine-grained feature circuits within a model (`transcoder_circuits/circuit_analysis.py`)
- **Feature Dashboards:** Generate dashboards for exploring transcoder and SAE features (`transcoder_circuits/feature_dashboards.py`)
- **Replacement Context:** Swap MLP sublayers with transcoder reconstructions during inference (`transcoder_circuits/replacement_ctx.py`)
- **Activations Store:** Stream tokens and generate/store activations during training (`sae_training/activations_store.py`)
- **Geometric Median:** Utility for computing geometric median for initialization (`sae_training/geom_median/`)
- **SAE/Transcoder Comparison:** Evaluation notebooks comparing SAEs and transcoders on Pythia-410M

## Usage Examples

### Loading a Transcoder and Running Replacement Context

```python
import torch
from transformer_lens import HookedTransformer
from transcoder_circuits.replacement_ctx import TranscoderReplacementContext

# Load GPT-2 small via TransformerLens
model = HookedTransformer.from_pretrained("gpt2")

# Load transcoder weights (downloaded via setup.sh)
transcoder = torch.load("path/to/transcoder_layer_0.pt")

# Use replacement context to patch MLP with transcoder
with TranscoderReplacementContext(model, {0: transcoder}):
    tokens = model.to_tokens("Hello, world!")
    logits = model(tokens)
```

### Training a Transcoder

```bash
python train_transcoder.py
```

Or programmatically:

```python
from sae_training.config import LanguageModelSAERunnerConfig
from sae_training.train_sae_on_language_model import language_model_sae_runner

cfg = LanguageModelSAERunnerConfig(
    model_name="gpt2",
    hook_point="blocks.0.hook_mlp_out",
    hook_point_layer=0,
    d_in=768,
    expansion_factor=4,
    # ... other config options
)
language_model_sae_runner(cfg)
```

### Circuit Analysis

```python
from transcoder_circuits.circuit_analysis import get_circuit_scores

# Analyze which transcoder features contribute most to a given output
scores = get_circuit_scores(model, transcoders, tokens, metric_fn)
```

### Feature Dashboards

```python
from transcoder_circuits.feature_dashboards import make_feature_dashboard

# Generate a dashboard for a specific transcoder feature
dashboard = make_feature_dashboard(
    transcoder=transcoder,
    model=model,
    feature_idx=42,
    dataset=dataset,
)
```

## Key APIs / Models

### Models Supported
- **GPT-2 small** (primary, weights available at `pchlenski/gpt2-transcoders`)
- **Pythia-410M** (used in sweep/comparison experiments)

### Core Classes

| Class | Module | Description |
|---|---|---|
| `ActivationsStore` | `sae_training/activations_store.py` | Streams tokens and stores LLM activations for training |
| `RunnerConfig` | `sae_training/config.py` | Base config shared across all training runners |
| `LanguageModelSAERunnerConfig` | `sae_training/config.py` | Config for training transcoders/SAEs on a language model |
| `CacheActivationsRunnerConfig` | `sae_training/config.py` | Config for caching LLM activations to disk |
| `SparseAutoencoder` | `sae_training/sparse_autoencoder.py` | The transcoder/SAE model class |

### Key Functions

| Function | Module | Description |
|---|---|---|
| `language_model_sae_runner` | `sae_training/train_sae_on_language_model.py` | Main training entry point |
| `get_circuit_scores` | `transcoder_circuits/circuit_analysis.py` | Compute feature circuit attribution scores |
| `make_feature_dashboard` | `transcoder_circuits/feature_dashboards.py` | Generate feature visualization dashboards |

## Related Tools

Anthropic has open-sourced **circuit-tracer**, a Python library that builds on the (cross-layer) MLP transcoder formulation to extract feature circuits directly from open-weights models such as Gemma-2-2B and Llama-3.2-1B. Given a prompt, it computes the direct effect of every active transcoder feature, transcoder error node, and input token on every other active feature and output logit, and surfaces the resulting attribution graph through a Neuronpedia-hosted frontend. It pairs naturally with the training and feature-analysis primitives in this skill: train or load transcoders here, then plug them into circuit-tracer's `ReplacementModel.from_pretrained` to obtain end-to-end circuits.

- **Announcement:** https://www.anthropic.com/research/open-source-circuit-tracing
- **GitHub:** https://github.com/safety-research/circuit-tracer

## Common Patterns & Best Practices

1. **Start with `walkthrough.ipynb`** — the notebook walks through loading transcoders, replacement context, and circuit analysis step by step.
2. **Use `TranscoderReplacementContext`** as a context manager to ensure the model is properly restored after patching.
3. **Transcoder weights are layer-specific** — load each layer's transcoder separately.
4. **MLP0 features** are particularly important; the "restricted blind case studies" notebook shows how to work without them.
5. **Use `wandb`** for tracking training runs when training new transcoders.
6. **Circuit analysis is iterative** — start by finding the top features, then investigate their upstream inputs recursively.

## Demo Scripts

### `scripts/train_transcoder_example.py`


See [`scripts/train_transcoder_example.py`](scripts/train_transcoder_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/transcoder_usage_example.py`


See [`scripts/transcoder_usage_example.py`](scripts/transcoder_usage_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

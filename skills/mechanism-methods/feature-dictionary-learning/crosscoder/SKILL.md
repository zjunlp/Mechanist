---
name: crosscoder-learning
description: "Use this skill when working with sparse autoencoders (SAEs), crosscoders, dictionary learning on neural network activations, training SAEs/crosscoders from scratch, loading pretrained dictionaries, caching model activations, or comparing model internals across fine-tuned model pairs using the dictionary_learning / crosscoder_learning library."
---

## Method and use

Use shared sparse dictionaries across related activation spaces or models to compare shared and changed features. Keep correspondence and normalization clear. Bundled SAE training examples are supporting utilities, not a full crosscoder experiment; evaluate on actual held-out activations.


# Dictionary Learning & Crosscoders Skill

## When to Use

Activate this skill when the user needs to:

- Train **Sparse Autoencoders (SAEs)** on neural network activations (MLP outputs, attention outputs, residual streams)
- Train **CrossCoders** to compare activations across two related models (e.g., a base model and its fine-tuned variant)
- Load and use **pretrained dictionaries** (AutoEncoders, CrossCoders, JumpReLU SAEs) from local disk or the Hugging Face Hub
- **Cache activations** from a language model for later offline training
- **Evaluate** dictionaries using MSE loss, L1/L0 sparsity, CE diff, and variance-explained metrics
- Push or pull dictionary weights to/from the **Hugging Face Hub**
- Perform **model diffing** to identify which features change between a base model and a fine-tuned model
- Use `BatchTopKCrossCoder` for batch-level top-k sparsity across model pairs
- Work with the `nnsight` library to hook into language model internals

**Keywords:** sparse autoencoder, SAE, crosscoder, dictionary learning, activation buffer, neural network features, mechanistic interpretability, model diffing, JumpReLU, GatedSAE, TopK SAE, nnsight, Pythia, Gemma, residual stream, MLP output, attention output

---

## Quick Reference

| Resource | URL |
|---|---|
| Repository (fork) | https://github.com/jkminder/dictionary_learning |
| Original Repository | https://github.com/saprmarks/dictionary_learning |
| Anthropic CrossCoder Paper | https://transformer-circuits.pub/drafts/crosscoders/index.html#model-diffing |
| BatchTopKCrossCoder Paper | https://arxiv.org/pdf/2504.02922 |
| nnsight Documentation | https://nnsight.net/ |
| nnsight Walkthrough | https://nnsight.net/notebooks/tutorials/walkthrough/ |
| Pretrained Dictionaries (Pythia) | https://baulab.us/u/smarks/autoencoders/ |
| Pretrained CrossCoder (HF Hub) | Butanium/gemma-2-2b-crosscoder-l13-mu4.1e-02-lr1e-04 |
| Pretrained SAE Downloader Script | `./pretrained_dictionary_downloader.sh` |

---

## Installation / Setup

### Method 1: pip install from GitHub (recommended for crosscoder features)

```bash
pip install git+https://github.com/jkminder/dictionary_learning
```

### Method 2: Clone and install from source

```bash
git clone https://github.com/jkminder/dictionary_learning
cd dictionary_learning
pip install -r requirements.txt
```

### Method 3: Use as a subdirectory (original repo style)

```bash
git clone https://github.com/saprmarks/dictionary_learning
# Then place the cloned directory inside your project directory and import it
```

### Additional Dependencies

The library uses `nnsight` to access and hook into language model activations:

```bash
pip install nnsight
```

For JumpReLU SAE loading from `sae_lens`:

```bash
pip install sae_lens
```

For Hugging Face Hub push/pull:

```bash
pip install huggingface_hub
```

### Downloading Pretrained Pythia-70m-deduped Dictionaries

```bash
./pretrained_dictionary_downloader.sh
```

This downloads ~2.5 GB of dictionaries (MLP outputs, attention outputs, residual streams for all layers of Pythia-70m-deduped, trained on 2B tokens from The Pile). Directory structure after download:


## Demo Scripts

### `scripts/train_and_evaluate_sae.py`


See [`scripts/train_and_evaluate_sae.py`](scripts/train_and_evaluate_sae.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/train_sae_demo.py`


See [`scripts/train_sae_demo.py`](scripts/train_sae_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

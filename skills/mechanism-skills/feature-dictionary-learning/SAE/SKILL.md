---
name: saelens
description: Use this skill when working with Sparse Autoencoders (SAEs) for mechanistic interpretability of language models, including training SAEs, loading pre-trained SAEs, analyzing neural network features, or integrating SAEs with TransformerLens, HuggingFace Transformers, or other PyTorch-based models.
---

# SAELens — Sparse Autoencoders for Language Models

## When to Use

Activate this skill when:
- Training sparse autoencoders (SAEs) on language model activations
- Loading and analyzing pre-trained SAEs from Neuronpedia or HuggingFace
- Performing mechanistic interpretability research on transformer models
- Investigating neural network features using SAE decompositions
- Generating SAE feature dashboards with SAE-Vis
- Hooking SAEs into transformer forward passes (HookedSAETransformer)
- Evaluating SAE quality (variance explained, L0 sparsity, reconstruction loss)
- Running cache activation pipelines for large-scale SAE training
- Analyzing logit lens features through SAE decomposition
- Working with TopK, Gated, or Standard SAE architectures

**Keywords:** sparse autoencoder, SAE, mechanistic interpretability, TransformerLens, feature analysis, neural network features, activation patching, SAE training, HookedSAETransformer, Neuronpedia, dictionary learning, GPT-2, language model interpretability

---

## Installation / Setup

### Prerequisites
- Python 3.10+
- PyTorch (CUDA recommended for training)

### Install from PyPI (recommended)
```bash
pip install sae-lens
```

### Install from source (development)
```bash
git clone https://github.com/decoderesearch/SAELens.git
cd SAELens
pip install -e ".[dev]"
```
## Quick Reference

- **Documentation:** https://decoderesearch.github.io/SAELens/
- **PyPI Package:** https://pypi.org/project/sae-lens/
- **GitHub:** https://github.com/decoderesearch/SAELens
- **Pre-trained SAEs list:** https://decoderesearch.github.io/SAELens/latest/pretrained_saes/
- **Migration guide (v6):** https://decoderesearch.github.io/SAELens/latest/migrating/
- **Neuronpedia:** https://www.neuronpedia.org/
- **SAE-Vis Library:** https://github.com/callummcdougall/sae_vis
- **SAEBench:** https://github.com/adamkarvonen/SAEBench
- **Colab Tutorials:**
  - [SAE Lens + Neuronpedia](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/tutorial_2_0.ipynb)
  - [Loading and Analysing Pre-Trained SAEs](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/basic_loading_and_analysing.ipynb)
  - [Logit Lens with Features](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/logits_lens_with_features.ipynb)
  - [Training a Sparse Autoencoder](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/training_a_sparse_autoencoder.ipynb)
  - [Training SAEs on Synthetic Data](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/training_saes_on_synthetic_data.ipynb)
  - [SynthSAEBench](https://githubtocolab.com/decoderesearch/SAELens/blob/main/tutorials/synth_sae_bench.ipynb)

---
### Optional dependencies
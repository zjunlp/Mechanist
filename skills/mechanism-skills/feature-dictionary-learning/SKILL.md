---
name: Feature Dictionary Learning
description: 'Feature Dictionary Learning methods address the polysemanticity of neuron-level units by decomposing a dense internal activation (e.g. a residual-stream state or MLP output) into a sparse weighted sum of directions drawn from a large over-complete dictionary. The dictionary contains far more directions than the activation''s original dimensionality, and the decomposition is constrained to use only a small number of them at once. Each direction in the dictionary plays the role of an interpretable "feature": its weight measures how strongly that feature is present, turning a black-box vector into a small set of human-readable components.'
---

## Advantage

- Towards monosemanticity: By forcing decompositions to be sparse, Feature Dictionary Learning recovers features that are *more* monosemantic than individual neurons — though not strictly so — making the resulting basis far better suited to interpretation, attribution, and steering than the model's native one.
- Computational efficiency: Although training the dictionary is resource-intensive, inference is cheap — encoding an activation is a single linear pass plus a non-linearity, and intervening on a feature reduces to scaling or zeroing its weight before reconstruction.
- Composability: This composability makes downstream tools — feature dashboards, circuit discovery via attribution graphs, and SAE-based steering — practical at LLM scale.

## Limitation

- Reconstruction fidelity: The decomposition is only as faithful as the training data and reconstruction loss admit. Residual reconstruction error implicitly introduces an "error node" whose contribution must be tracked when making claims about full circuits.
- Dictionary quality issues: Dead features (never activated) and ultra-low-frequency features bloat the dictionary; dense or non-linearly encoded concepts split across many atoms (*feature splitting*) or get absorbed into a single atom (*feature absorption*).
- Site- and checkpoint-specificity: A dictionary trained on one model or one layer rarely transfers verbatim to another. The cost of training and storing a large over-complete dictionary per analyzed site is non-trivial.

## Submethods

The three main forms below follow a progression of increasing scope — from a single activation site, to cross-site mappings, to cross-layer or cross-model analysis.

- **Sparse Autoencoders (SAE)**:
The canonical instance: train an autoencoder on activations from a single site. The encoder maps an activation $\mathbf{a}$ to a sparse feature vector via $\mathbf{f}(\mathbf{a}) = \text{act}(\mathbf{W}_e \mathbf{a} + \mathbf{b}_e)$, where `act` is typically ReLU (L1 penalty), top-k, or JumpReLU depending on the variant. The decoder then reconstructs $\hat{\mathbf{a}} = \mathbf{W}_d \mathbf{f}(\mathbf{a}) + \mathbf{b}_d$, with columns of $\mathbf{W}_d$ serving as the dictionary atoms. The per-token values in $\mathbf{f}(\mathbf{a})$ are the feature firings used for downstream interpretability.
You can find a demo for this method in ./SAE. This demo shows saelens: Use this skill when working with Sparse Autoencoders (SAEs) for mechanistic interpretability of language models, including training SAEs, loading pre-trained SAEs, analyzing neural network features, or integrating SAEs with TransformerLens, HuggingFace Transformers, or other PyTorch-based models.

- **Transcoders**:
A variant in which the encoder reads from one site (typically the MLP input $\mathbf{a}_{\text{in}}$) and the decoder predicts a *different* site (typically the MLP output): $\hat{\mathbf{a}}_{\text{out}} = \mathbf{W}_d\,\mathbf{f}(\mathbf{a}_{\text{in}}) + \mathbf{b}_d$. Because each feature carries an explicit input→output mapping, transcoders serve as a sparse, interpretable replacement for the MLP sub-layer and slot directly into circuit-discovery pipelines (e.g. Anthropic's circuit-tracer attribution graphs).
You can find a demo for this method in ./transcoder. This demo shows transcoder-circuits: Use this skill when working with transcoder-based circuit analysis of large language models, including training transcoders, analyzing MLP sublayers, reverse-engineering LLM circuits, and creating feature dashboards for interpretability research.

- **Crosscoders**:
Lifts dictionary learning across multiple sites or multiple models simultaneously: a single shared dictionary reconstructs activations from a set of layers (within one model) or from paired checkpoints (e.g. base vs. chat-tuned). The shared basis exposes which features are common across the set and which are site- or model-specific, enabling robust identification of concepts introduced during fine-tuning and cross-layer feature analysis.
You can find a demo for this method in ./crosscoder. This demo shows crosscoder-learning: Use this skill when working with sparse autoencoders (SAEs), crosscoders, dictionary learning on neural network activations, training SAEs/crosscoders from scratch, loading pretrained dictionaries, caching model activations, or comparing model internals across fine-tuned model pairs using the dictionary_learning / crosscoder_learning library.

- **ICA Lens (dictionary-free baseline)**:
A *training-free* alternative that recovers interpretable directions by running Independent Component Analysis directly on captured activations, rather than learning an over-complete sparse dictionary. The premise is that many interpretable directions are token-selective and therefore *less Gaussian* than random directions, so FastICA's non-Gaussianity objective already surfaces them: $\mathbf{f}(\mathbf{a}) = \mathbf{W}_{\mathrm{ICA}}\,\mathbf{a}$, with $\mathbf{W}_{\mathrm{ICA}}$ fitted to maximise non-Gaussianity of the components. ICA Lens matches public SAEs on sparse-probing performance and outperforms them on targeted probe perturbation under a constrained budget, while skipping per-layer gradient training. Use it as a cheap first-pass exploration tool *before* committing to SAE / transcoder / crosscoder training, or as a baseline against which a learned dictionary's added value can be measured.
You can find a demo for this method in ./ica-lens. This demo shows ica-lens: Use this skill when applying Independent Component Analysis as a training-free interpretability lens — decomposing a target activation site (residual stream, MLP output, attention-head output, or any cached hook point) into maximally non-Gaussian directions and treating each direction as a candidate monosemantic component for sparse-probing, targeted perturbation, annotation, and cross-comparison against trained SAE / transcoder / crosscoder features.

---
name: Probing
description: 'Probing methods interpret model signals by training an auxiliary predictor (often linear) to decode a labeled property y from an internal vector $z$ (e.g., the residual stream state $x_l$ at layer $l$). Operationally, probing treats the model as a frozen feature extractor and assesses decodability: whether $y$ is recoverable from $z$ by a restricted hypothesis class (commonly linear), which supports localization by comparison across candidate objects (layers/heads/FFNs) via decoding performance or information-theoretic surrogates, typically followed by Causal Attribution to test functional necessity.'
---

## Advantage

With a fixed probe family, Probing enables standardized comparisons across objects, supporting efficient layer-wise tracking and large-scale ranking of candidate modules. Simple probes (e.g., linear) are lightweight and interpretable, allowing broad sweeps while keeping the LLM frozen.

## Limitation

Decodability is not causality: high probe accuracy does not imply the model uses this object, nor that the probed object is necessary or sufficient. Results are sensitive to dataset and design choices (e.g., labeling, token positions), so controls and follow-up causal tests are typically required for functional claims.

## Submethods

Given object categories, the method typically takes three forms:

- **Residual Stream States**:
The most common probing target is the residual stream state $x^l \in \mathbb{R}^{d_{\text{model}}}$, as well as intermediate residual states $x^{l,\text{mid}}$. Layer-wise probes trained on $x^l$ directly instantiate the “extract residual stream state across layers $\to$ train probing classifiers” step, and have been used to track where context knowledge, knowledge conflicts, and truthfulness-related signals become most decodable along depth.
You can find a demo for this method in ./residual-stream-states. This demo shows llms-know: Use this skill when working with LLM hallucination detection, probing internal representations of language models, analyzing model correctness, or conducting intrinsic evaluation experiments on models like Mistral and Llama-3.

- **Block Outputs**:
Probing can target intermediate block outputs by extracting $\mathbf{z}$ from either an attention head output $\mathbf{h}_{attn}^{l,h}$ or the FFN output $\mathbf{h}_{ffn}^l$ (optionally token-wise, e.g., $\mathbf{h}_{attn,t}^{l,h}$ or $\mathbf{h}_{ffn,t}^l$), and training a matched probe family across layers (and heads for attention). Comparing decodability across $(l, h)$ and $l$ supports fine-grained “localization by comparison,” ranking where a target property is most linearly accessible and contrasting attention- vs. FFN-based localization under a consistent protocol.

- **Sparse Autoencoder(SAE) Feature Activation State**:
Probing also integrates with SAE features. Given sparse SAE feature activation states $a$, one can define target inter vector $z$ as the feature activation vector $a = (a_1, . . . , a_m)$ (or a selected subset) and train classifiers on these sparse coordinates. This yields concept-aligned decoding axes that can be inspected at the feature level and cross-referenced with feature-level interpretations.
You can find a demo for this method in ./sae-feature-activation-state. This demo shows sae-spelling: Use this skill when working with Sparse Autoencoders (SAEs) for feature analysis, particularly for studying feature splitting, absorption, and attribution in language models. Activate for tasks involving SAE feature ablation, probing experiments, or analyzing how SAE latents affect model outputs in spelling and token-level tasks.

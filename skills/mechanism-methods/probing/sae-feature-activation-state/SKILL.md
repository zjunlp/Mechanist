---
name: sae-feature-activation-state
description: "Use this skill when working with Sparse Autoencoders (SAEs) for feature analysis, particularly for studying feature splitting, absorption, and attribution in language models. Activate for tasks involving SAE feature ablation, probing experiments, or analyzing how SAE latents affect model outputs in spelling and token-level tasks."
---

## Method and use

Probe sparse dictionary features, examine feature splitting, and investigate candidate ablations or attribution. Match the SAE to the model and site. Synthetic sparse-probe examples illustrate training mechanics; ablation and attribution adapters need actual activations and measurements.


## Demo Scripts

### `scripts/feature_ablation_example.py`


See [`scripts/feature_ablation_example.py`](scripts/feature_ablation_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/feature_attribution_example.py`


See [`scripts/feature_attribution_example.py`](scripts/feature_attribution_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/k_sparse_probing_example.py`


See [`scripts/k_sparse_probing_example.py`](scripts/k_sparse_probing_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


> Implementation status: some bundled functions are adaptation templates and raise `NotImplementedError` until connected to the actual method. Consult the API reference and source method; do not interpret demonstration outputs as measurements.

## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

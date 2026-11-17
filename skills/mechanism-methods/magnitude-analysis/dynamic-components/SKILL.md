---
name: dynamic-components
description: "Identify and manipulate language-specific neurons in multilingual Large Language Models (LLMs) to understand and control language-specific behaviors in models like LLaMA-2, BLOOM, OPT, Mistral, and Phi-2"
---

## Method and use

Inspect language-specific neuron sets, construct deactivation masks, and compare behavior or perplexity. Keep neuron indices aligned with model architecture and checkpoint. The PPL forward adapter must be connected to the real model; random logits are not model evaluation.


## Demo Scripts

### `scripts/compute_perplexity.py`


See [`scripts/compute_perplexity.py`](scripts/compute_perplexity.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/deactivate_neurons.py`


See [`scripts/deactivate_neurons.py`](scripts/deactivate_neurons.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/load_neurons.py`


See [`scripts/load_neurons.py`](scripts/load_neurons.py) for the reference template. Adapt its model, data, and measurement assumptions.


> Implementation status: some bundled functions are adaptation templates and raise `NotImplementedError` until connected to the actual method. Consult the API reference and source method; do not interpret demonstration outputs as measurements.

## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

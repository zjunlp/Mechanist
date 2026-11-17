---
name: rome-model-editing
description: "Use this skill when you need to edit factual knowledge in large language models like GPT-2 or GPT-J, perform causal tracing to understand model behavior, or implement Rank-One Model Editing (ROME) to modify specific factual associations without retraining"
---

## Method and use

Use clean/corrupted activation restoration to test candidate causal pathways, or compatible ROME edits for factual associations. Counterfactual construction, corruption, positions, and restoration scope determine interpretation. The tracing adapter must measure actual restoration effects; editing success alone is not full mechanism identification.


## Demo Scripts

### `scripts/causal_tracing_demo.py`


See [`scripts/causal_tracing_demo.py`](scripts/causal_tracing_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/rome_editing_example.py`


See [`scripts/rome_editing_example.py`](scripts/rome_editing_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


> Implementation status: some bundled functions are adaptation templates and raise `NotImplementedError` until connected to the actual method. Consult the API reference and source method; do not interpret demonstration outputs as measurements.

## Supporting material

- [rome api reference](references/rome_api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

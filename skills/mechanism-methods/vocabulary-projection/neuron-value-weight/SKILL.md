---
name: neuron-value-weight
description: "Analyze transformer feed-forward layers as key-value memories, extract activations, identify trigger examples, and compute key-value agreement in transformer language models"
---

## Method and use

Treat FFN keys and values as candidate associations: identify activating contexts, project value directions into vocabulary space, and compare triggers with promoted tokens. The examples target the ff-layers codebase and can have large memory requirements. Association and vocabulary alignment alone do not establish causal use.


## Demo Scripts

### `scripts/compute_key_value_agreement.py`


See [`scripts/compute_key_value_agreement.py`](scripts/compute_key_value_agreement.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/extract_predictions.py`


See [`scripts/extract_predictions.py`](scripts/extract_predictions.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/extract_trigger_examples.py`


See [`scripts/extract_trigger_examples.py`](scripts/extract_trigger_examples.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

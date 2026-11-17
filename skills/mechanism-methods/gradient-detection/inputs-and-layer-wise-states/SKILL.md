---
name: inputs-and-layer-wise-states
description: "Analyze and visualize layer-wise gradient behaviors in LLMs during fine-tuning for fast vs slow thinking tasks, calculate gradient statistics, and understand training patterns across different model layers"
---

## Method and use

Use gradient statistics to compare inputs or internal states under a chosen scalar target. The examples include fine-tuning gradients and layer comparisons. Keep the target, normalization, positions, and aggregation explicit; large gradients are local sensitivity, not guaranteed finite intervention effects.


## Demo Scripts

### `scripts/calculate_gradients.py`


See [`scripts/calculate_gradients.py`](scripts/calculate_gradients.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/visualize_gradients.py`


See [`scripts/visualize_gradients.py`](scripts/visualize_gradients.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

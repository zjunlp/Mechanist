---
name: attribution-patching
description: "Use when analyzing neural network circuits, performing attribution patching, automated circuit discovery, or investigating model interpretability through edge attribution methods in transformer models"
---

## Method and use

Approximate patching effects with gradients to screen many edges cheaply. First-order estimates can diverge from actual finite interventions; verify important candidates directly. The dataset example is illustrative, and the experiment adapter needs a real model and attribution backend.


## Demo Scripts

### `scripts/ioi_dataset_usage.py`


See [`scripts/ioi_dataset_usage.py`](scripts/ioi_dataset_usage.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/run_attribution_patching.py`


See [`scripts/run_attribution_patching.py`](scripts/run_attribution_patching.py) for the reference template. Adapt its model, data, and measurement assumptions.


> Implementation status: some bundled functions are adaptation templates and raise `NotImplementedError` until connected to the actual method. Consult the API reference and source method; do not interpret demonstration outputs as measurements.

## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

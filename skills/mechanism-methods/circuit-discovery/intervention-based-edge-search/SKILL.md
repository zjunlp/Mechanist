---
name: automatic-circuit-discovery
description: "Activates when working on mechanistic interpretability of transformers, specifically for automated circuit discovery in transformer models using computational graph editing and analysis."
---

## Method and use

Use ACDC-style intervention search to prune a computational graph while preserving a chosen task metric. Counterfactual inputs, graph definitions, thresholds, and task distribution shape the result. A faithful recovered circuit need not be unique or explain all conditions.


## Demo Scripts

### `scripts/acdc_run_demo.py`


See [`scripts/acdc_run_demo.py`](scripts/acdc_run_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

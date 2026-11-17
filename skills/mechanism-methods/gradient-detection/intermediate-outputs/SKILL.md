---
name: intermediate-outputs
description: "Use this skill when working with circuit discovery in language models, mechanistic interpretability, activation patching, attribution patching, or Layer-wise Relevance Propagation (LRP) for neural network analysis"
---

## Method and use

Use RelP/LRP-style relevance propagation and internal attribution to screen candidate computations. Propagation rules and architecture handling matter. Verify that the backend implements the intended rules and use interventions when the question requires causal rather than attribution evidence.


## Demo Scripts

### `scripts/basic_relp_analysis.py`


See [`scripts/basic_relp_analysis.py`](scripts/basic_relp_analysis.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/ioi_task_analysis.py`


See [`scripts/ioi_task_analysis.py`](scripts/ioi_task_analysis.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [relp api reference](references/relp_api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

---
name: dissecting-factual-predictions
description: "Analyze and dissect factual recall in auto-regressive language models using attention knockout, hidden state analysis, and intervention techniques on GPT-2 and GPT-J models"
---

## Method and use

Remove or replace selected computations and measure factual prediction or hidden-state changes. Choose the ablation baseline and granularity carefully: zeroing can create unnatural states. Compare relevant alternatives and off-target effects before interpreting loss as specific necessity.


## Demo Scripts

### `scripts/intervention_experiments.py`


See [`scripts/intervention_experiments.py`](scripts/intervention_experiments.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/model_analysis.py`


See [`scripts/model_analysis.py`](scripts/model_analysis.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

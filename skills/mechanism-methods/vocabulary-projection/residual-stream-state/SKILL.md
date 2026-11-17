---
name: residual-stream-state
description: "Use this skill when working with transformer model interpretability, analyzing layer-by-layer predictions, training tuned lenses to understand intermediate representations, or peeking into iterative computations of transformers"
---

## Method and use

Use logit or tuned lenses to inspect vocabulary-readable information across residual-stream layers. A tuned lens needs compatible trained translators; the unembedding alone is a logit lens. Match normalization and token positions. Readability does not prove the model uses the decoded information.


## Demo Scripts

### `scripts/analyze_predictions.py`


See [`scripts/analyze_predictions.py`](scripts/analyze_predictions.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/train_tuned_lens.py`


See [`scripts/train_tuned_lens.py`](scripts/train_tuned_lens.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

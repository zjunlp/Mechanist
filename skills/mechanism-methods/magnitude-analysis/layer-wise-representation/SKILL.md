---
name: layer-wise-representation
description: "Use this skill when you need to enhance the truthfulness of Large Language Models (LLMs) or reduce hallucinations in model outputs. This skill provides TruthX, an inference-time method that edits LLM internal representations to control truthfulness and mitigate hallucinations."
---

## Method and use

Explore TruthX-style representation editing and truthfulness evaluation. This is an editing example rather than a general magnitude-based localization implementation. Use compatible checkpoints, verify the actual edit path, and separate truthfulness gains from language-quality or answer-format changes.


## Demo Scripts

### `scripts/basic_inference.py`


See [`scripts/basic_inference.py`](scripts/basic_inference.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/truthfulqa_evaluation.py`


See [`scripts/truthfulqa_evaluation.py`](scripts/truthfulqa_evaluation.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/truthx_editing.py`


See [`scripts/truthx_editing.py`](scripts/truthx_editing.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

---
name: residual-stream-states
description: "Use this skill when working with LLM hallucination detection, probing internal representations of language models, analyzing model correctness, or conducting intrinsic evaluation experiments on models like Mistral and Llama-3"
---

## Method and use

Train restricted predictors on frozen internal states to test whether labels are recoverable and compare layers or token positions. Keep fitting and evaluation separate, control label and lexical confounds, and compare probe capacity. High accuracy alone does not establish causal use by the model.


## Demo Scripts

### `scripts/probe_model_representations.py`


See [`scripts/probe_model_representations.py`](scripts/probe_model_representations.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/run_experiments.py`


See [`scripts/run_experiments.py`](scripts/run_experiments.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Family papers](../article_references.md).

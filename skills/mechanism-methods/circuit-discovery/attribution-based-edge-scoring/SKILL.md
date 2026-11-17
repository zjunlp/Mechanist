---
name: eap-ig
description: "Use this skill to discover and analyze computational circuits within autoregressive transformer language models via attribution methods like Edge Attribution Patching with Integrated Gradients (EAP-IG), enabling mechanistic interpretability studies and circuit evaluation."
---

## Method and use

Use EAP-IG-style scores to rank edges and evaluate selected subgraphs. Integration can improve approximation, but ranking alone does not prove a circuit faithfully computes the behavior. Evaluate candidate circuits on suitable held-out inputs and counterfactuals.


## Demo Scripts

### `scripts/usage_example.py`


See [`scripts/usage_example.py`](scripts/usage_example.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

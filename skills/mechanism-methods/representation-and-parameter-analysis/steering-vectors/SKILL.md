---
name: steering-vectors
description: "Work with Llama 2 model steering using Contrastive Activation Addition (CAA) for behavioral control, including generating steering vectors, evaluating model behavior, and analyzing activation patterns"
---

## Method and use

Build contrastive activation-addition directions from matched examples, then apply and inspect them at compatible sites. Contrast construction, pooling, normalization, and application frequency matter. Recalibrate strength when any change; missing vectors must not be replaced with random ones.


## Demo Scripts

### `scripts/generate_steering_vectors.py`


See [`scripts/generate_steering_vectors.py`](scripts/generate_steering_vectors.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/apply_steering.py`


See [`scripts/apply_steering.py`](scripts/apply_steering.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/analyze_vectors.py`


See [`scripts/analyze_vectors.py`](scripts/analyze_vectors.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

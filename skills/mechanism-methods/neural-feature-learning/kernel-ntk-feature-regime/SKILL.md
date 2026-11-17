---
name: tp4-feature-learning
description: "Use this skill when working with infinite-width neural networks for feature learning, replicating Word2Vec or MAML experiments from the Tensor Programs series (TP4), or implementing infinite-width limits (GP, NTK, muP) for meta-learning and word embedding tasks."
---

## Method and use

Explore infinite-width GP/NTK and feature-learning regimes using the TP4 examples. Parameterization, initialization, learning rate, and width assumptions determine which limit applies. Infinite-width theory does not transfer unchanged to finite pretrained transformers.


# TP4: Feature Learning in Infinite-Width Neural Networks

## When to Use
- Implementing infinite-width neural network experiments (GP, NTK, muP/feature learning limits)
- Replicating Word2Vec experiments with infinite-width models
- Running MAML (Model-Agnostic Meta-Learning) with infinite-width networks on Omniglot
- Studying the Tensor Programs series of papers empirically
- Comparing finite vs. infinite-width neural network behavior
- Keywords: infinite-width, feature learning, NTK, GP, muP, MAML, Word2Vec, Tensor Programs, meta-learning

## Quick Reference
- **Paper:** https://arxiv.org/abs/2011.14522
- **Repo:** https://github.com/edwardjhu/TP4
- **GP limit code:** https://github.com/thegregyang/GP4A
- **NTK limit code:** https://github.com/thegregyang/NTK4A
- **Prior TP papers:** [TP0](http://arxiv.org/abs/1902.04760), [TP1](http://arxiv.org/abs/1910.12478), [TP2](http://arxiv.org/abs/2006.14548), [TP3](http://arxiv.org/abs/2009.10685)

## Installation / Setup

### Prerequisites
- Python 3.x
- C compiler (for Word2Vec C source)
- PyTorch

### MAML Experiment Setup
```bash
cd TP4MAML
pip install -r requirements.txt
cd meta
pip install -r requirements.txt
```

### Word2Vec Experiment Setup
```bash
cd Word2Vec
# Build C binaries
make
# Download and prepare text8 dataset
bash scripts/create-text8-data.sh
# Download and prepare fil9 dataset
bash scripts/create-fil9-data.sh
```

## Core Features

- **InfGP1LP:** Infinite-width Gaussian Process limit for a 1-hidden-layer perceptron
- **FinGP1LP:** Finite-width GP baseline for comparison
- **InfNTK1LP:** Infinite-width NTK limit for a 1-hidden-layer perceptron
- **InfSGD:** Custom SGD optimizer for infinite-width networks with proper scaling
- **InfMultiStepLR:** Learning rate scheduler compatible with InfSGD
- **InfMAML:** Infinite-width MAML metalearner for Omniglot few-shot classification
- **CachedOmniglot:** Efficient cached Omniglot dataset loader
- **Word2Vec C implementation:** Modified word2vec supporting infinite-width training modes

## Usage Examples

### Running All MAML Experiments
```bash
cd TP4MAML
bash train_all.sh
```

### Training MAML (finite width)
```bash
cd TP4MAML/meta
python train.py --dataset omniglot --num-ways 5 --num-shots 1
```

### Training Infinite-Width MAML
```bash
cd TP4MAML/meta
python train.py --dataset omniglot --num-ways 5 --num-shots 1 --inf
```

### Word2Vec Training (text8, standard)
```bash
cd Word2Vec
bash scripts/train-text8.sh
```

### Word2Vec Training (text8, infinite-width)
```bash
cd Word2Vec
bash scripts/train-text8-inf.sh
```

### Word2Vec Evaluation
```bash
cd Word2Vec
bash scripts/evaluate.sh
```

## Key APIs / Models

### `TP4MAML/inf/inf1lp.py`
- `InfGP1LP` — Infinite GP limit 1-layer perceptron
- `FinGP1LP` — Finite GP baseline
- `InfNTK1LP` — Infinite NTK limit 1-layer perceptron

### `TP4MAML/inf/optim.py`
- `InfSGD(params, lr, ...)` — SGD optimizer scaled for infinite-width networks
- `InfMultiStepLR(optimizer, milestones, gamma)` — LR scheduler for InfSGD

### `TP4MAML/inf/utils.py`
- `safe_sqrt(arr, eps)` — Numerically stable square root
- `safe_acos(arr, eps)` — Numerically stable arccos
- `F00ReLU(c, v, v2)` — ReLU kernel function used in GP/NTK computations
- `MyLinear` — Custom linear layer with infinite-width scaling

### `TP4MAML/meta/maml/metalearners/infmaml.py`
- `InfMAML` — Meta-learner implementing MAML for infinite-width networks

### `TP4MAML/meta/maml/metalearners/maml.py`
- `MAML` — Standard MAML meta-learner

### `TP4MAML/meta/cached_omniglot.py`
- `CachedOmniglot` — Omniglot dataset with caching
- `OmniglotClassDataset` — Per-class Omniglot dataset
- `Omniglot` — Base Omniglot loader

### `TP4MAML/inf/dynamicarray.py`
- `DynArr` — Dynamic array for storing activations during infinite-width forward passes
- `CycArr` — Cyclic array variant

## Common Patterns & Best Practices

- Use `--inf` flag in `train.py` to switch between finite and infinite-width MAML
- The infinite-width models do not store explicit weights; instead they accumulate kernel computations
- For Word2Vec, the `train-*-inf.sh` scripts set hyperparameters appropriate for infinite-width training
- Always build the C binaries before running Word2Vec experiments (`make` in `Word2Vec/`)
- The `train_all.sh` script in `TP4MAML/` runs all configurations sequentially for full replication

## Demo Scripts

### `scripts/inf_network_demo.py`


See [`scripts/inf_network_demo.py`](scripts/inf_network_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/maml_training_demo.py`


See [`scripts/maml_training_demo.py`](scripts/maml_training_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

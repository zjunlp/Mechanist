---
name: tp4-feature-learning
description: Use this skill when working with infinite-width neural networks for feature learning, replicating Word2Vec or MAML experiments from the Tensor Programs series (TP4), or implementing infinite-width limits (GP, NTK, muP) for meta-learning and word embedding tasks.
---

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

```python
#!/usr/bin/env python3
"""
TP4 Feature Learning - Infinite-Width Network Demo

Demonstrates usage of the TP4MAML inf module:
- InfGP1LP, InfNTK1LP for infinite-width 1-hidden-layer perceptrons
- InfSGD optimizer
- Utility functions (safe_sqrt, safe_acos, F00ReLU)

Requires: torch, numpy
Run from the repo root: python scripts/inf_network_demo.py
"""

import sys
import os

# Add TP4MAML to path so we can import the inf module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'TP4MAML'))

import torch
import torch.nn as nn
import numpy as np


def demo_utils():
    """Demonstrate utility functions from TP4MAML/inf/utils.py"""
    try:
        from inf.utils import safe_sqrt, safe_acos, F00ReLU, MyLinear
        print("=== Utility Functions ===")

        # safe_sqrt: numerically stable square root
        arr = torch.tensor([-1e-10, 0.0, 1.0, 4.0])
        result = safe_sqrt(arr, eps=1e-6)
        print(f"safe_sqrt({arr.tolist()}) = {result.tolist()}")

        # safe_acos: numerically stable arccos
        arr2 = torch.tensor([-1.0 - 1e-10, -1.0, 0.0, 1.0, 1.0 + 1e-10])
        result2 = safe_acos(arr2, eps=1e-6)
        print(f"safe_acos(clipped) = {result2.tolist()}")

        # F00ReLU: ReLU arc-cosine kernel
        # c: cosine similarity, v: variance1, v2: variance2
        c = torch.tensor([0.5])
        v = torch.tensor([1.0])
        v2 = torch.tensor([1.0])
        k = F00ReLU(c, v, v2)
        print(f"F00ReLU(c=0.5, v=1, v2=1) = {k.item():.4f}")

        # MyLinear: custom linear layer with infinite-width scaling
        linear = MyLinear(in_features=10, out_features=5)
        x = torch.randn(3, 10)
        out = linear(x)
        print(f"MyLinear(10->5) output shape: {out.shape}")

    except ImportError as e:
        print(f"Could not import inf.utils (run from repo root with TP4MAML in path): {e}")


def demo_dynamic_arrays():
    """Demonstrate DynArr and CycArr from TP4MAML/inf/dynamicarray.py"""
    try:
        from inf.dynamicarray import DynArr, CycArr
        print("\n=== Dynamic Arrays ===")

        # DynArr: growing array for storing activations
        darr = DynArr()
        for i in range(5):
            darr.append(torch.randn(3, 4))
        print(f"DynArr length after 5 appends: {len(darr)}")

        # CycArr: cyclic (ring buffer) array
        carr = CycArr(capacity=3)
        for i in range(6):
            carr.append(torch.tensor([float(i)]))
        print(f"CycArr (capacity=3) last 3 values: {[carr[i].item() for i in range(len(carr))]}")

    except ImportError as e:
        print(f"Could not import inf.dynamicarray: {e}")


def demo_inf_models():
    """Demonstrate InfGP1LP, FinGP1LP, InfNTK1LP from TP4MAML/inf/inf1lp.py"""
    try:
        from inf.inf1lp import InfGP1LP, FinGP1LP, InfNTK1LP
        print("\n=== Infinite-Width 1-Layer Perceptron Models ===")

        input_dim = 16
        output_dim = 5
        batch_size = 8

        x_train = torch.randn(batch_size, input_dim)
        y_train = torch.randint(0, output_dim, (batch_size,))
        x_test = torch.randn(4, input_dim)

        # InfGP1LP: Infinite-width Gaussian Process limit
        print("Building InfGP1LP...")
        gp_model = InfGP1LP(input_dim=input_dim, output_dim=output_dim)
        print(f"  InfGP1LP created: {type(gp_model).__name__}")

        # InfNTK1LP: Infinite-width NTK limit
        print("Building InfNTK1LP...")
        ntk_model = InfNTK1LP(input_dim=input_dim, output_dim=output_dim)
        print(f"  InfNTK1LP created: {type(ntk_model).__name__}")

        # FinGP1LP: Finite baseline
        print("Building FinGP1LP...")
        fin_model = FinGP1LP(input_dim=input_dim, output_dim=output_dim, width=256)
        print(f"  FinGP1LP created: {type(fin_model).__name__}")

        # Forward pass on finite model
        logits = fin_model(x_test)
        print(f"  FinGP1LP forward output shape: {logits.shape}")

    except ImportError as e:
        print(f"Could not import inf.inf1lp: {e}")
    except Exception as e:
        print(f"Error in inf model demo: {e}")


def demo_inf_sgd():
    """Demonstrate InfSGD optimizer from TP4MAML/inf/optim.py"""
    try:
        from inf.optim import InfSGD, InfMultiStepLR
        print("\n=== InfSGD Optimizer ===")

        # Simple model to optimize
        model = nn.Linear(10, 5)

        # InfSGD: SGD with infinite-width scaling
        optimizer = InfSGD(model.parameters(), lr=0.01, momentum=0.9)
        print(f"InfSGD created with lr=0.01, momentum=0.9")

        # InfMultiStepLR scheduler
        scheduler = InfMultiStepLR(optimizer, milestones=[10, 20], gamma=0.1)
        print(f"InfMultiStepLR created with milestones=[10, 20], gamma=0.1")

        # Simulate a few training steps
        x = torch.randn(4, 10)
        y = torch.randint(0, 5, (4,))
        criterion = nn.CrossEntropyLoss()

        for step in range(3):
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            scheduler.step()
            print(f"  Step {step+1}: loss={loss.item():.4f}, lr={scheduler.get_last_lr()}")

    except ImportError as e:
        print(f"Could not import inf.optim: {e}")
    except Exception as e:
        print(f"Error in InfSGD demo: {e}")


def demo_maml_structure():
    """Show the MAML metalearner interface (TP4MAML/meta/maml/metalearners/)"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'TP4MAML', 'meta'))
        from maml.metalearners.maml import MAML
        print("\n=== MAML Metalearner ===")
        print(f"MAML class imported: {MAML}")
        print("  MAML implements standard Model-Agnostic Meta-Learning.")
        print("  Use train.py --inf flag to switch to InfMAML.")
    except ImportError as e:
        print(f"\nCould not import MAML metalearner: {e}")


if __name__ == "__main__":
    print("TP4 Feature Learning in Infinite-Width Neural Networks - Demo\n")
    demo_utils()
    demo_dynamic_arrays()
    demo_inf_models()
    demo_inf_sgd()
    demo_maml_structure()
    print("\nDemo complete.")
```

### `scripts/maml_training_demo.py`

```python
#!/usr/bin/env python3
"""
TP4 MAML Training Demo

Shows how to invoke MAML training programmatically (mirroring train.py usage).
Demonstrates the dataset loading and metalearner API.

Requires: torch, torchmeta (see TP4MAML/meta/requirements.txt)
Run from TP4MAML/meta/: python ../../scripts/maml_training_demo.py
"""

import sys
import os
import argparse

# Adjust paths for running from repo root
MAML_META_PATH = os.path.join(os.path.dirname(__file__), '..', 'TP4MAML', 'meta')
MAML_INF_PATH = os.path.join(os.path.dirname(__file__), '..', 'TP4MAML')
sys.path.insert(0, MAML_META_PATH)
sys.path.insert(0, MAML_INF_PATH)


def build_omniglot_dataset(data_folder: str, num_ways: int = 5, num_shots: int = 1,
                            num_shots_test: int = 15):
    """
    Build Omniglot meta-learning dataset using CachedOmniglot.

    Args:
        data_folder: Path to Omniglot data directory.
        num_ways: Number of classes per episode (N-way).
        num_shots: Number of support examples per class (K-shot).
        num_shots_test: Number of query examples per class.

    Returns:
        Tuple of (meta_train_dataset, meta_val_dataset, meta_test_dataset)
    """
    try:
        from cached_omniglot import CachedOmniglot
        import torchmeta
        from torchmeta.transforms import ClassSplitter, Categorical
        from torchvision.transforms import Compose, Resize, ToTensor

        transform = Compose([Resize(28), ToTensor()])

        meta_train = CachedOmniglot(
            data_folder,
            num_classes_per_task=num_ways,
            transform=transform,
            target_transform=Categorical(num_ways),
            class_augmentations=[torchmeta.transforms.Rotation([90, 180, 270])],
            meta_train=True,
            dataset_transform=ClassSplitter(
                shuffle=True,
                num_support_per_class=num_shots,
                num_query_per_class=num_shots_test
            )
        )
        print(f"CachedOmniglot meta-train: {len(meta_train)} tasks")
        return meta_train

    except ImportError as e:
        print(f"Could not build Omniglot dataset (missing torchmeta or data): {e}")
        return None
    except Exception as e:
        print(f"Dataset error: {e}")
        return None


def demonstrate_metalearner_api():
    """
    Show the API surface of MAML and InfMAML metalearners.
    """
    print("=== MAML / InfMAML API ===\n")

    try:
        from maml.metalearners.maml import MAML
        print(f"MAML class: {MAML.__module__}.{MAML.__name__}")
        print(f"  __init__ signature: see references/api_reference.md")
        print(f"  Key methods: train(), evaluate(), get_outer_loss()")
    except ImportError as e:
        print(f"MAML import failed: {e}")

    try:
        from maml.metalearners.infmaml import InfMAML
        print(f"\nInfMAML class: {InfMAML.__module__}.{InfMAML.__name__}")
        print(f"  Extends MAML for infinite-width networks using InfGP1LP/InfNTK1LP")
    except ImportError as e:
        print(f"InfMAML import failed: {e}")

    try:
        from maml.metalearners.meta_sgd import MetaSGD
        print(f"\nMetaSGD class: {MetaSGD.__module__}.{MetaSGD.__name__}")
        print(f"  Meta-SGD variant with per-parameter learned learning rates")
    except ImportError as e:
        print(f"MetaSGD import failed: {e}")


def show_training_command_equivalents():
    """
    Print the equivalent train.py CLI commands for common configurations.
    """
    print("\n=== Equivalent train.py Commands ===\n")

    configs = [
        {
            "description": "5-way 1-shot Omniglot, finite MAML",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 1 --num-steps 5"
        },
        {
            "description": "5-way 1-shot Omniglot, infinite-width MAML (GP limit)",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 1 --num-steps 5 --inf --use-gp"
        },
        {
            "description": "5-way 5-shot Omniglot, infinite-width MAML (NTK limit)",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 5 --num-steps 5 --inf"
        },
        {
            "description": "Run all experiments (uses train_all.sh)",
            "cmd": "cd TP4MAML && bash train_all.sh"
        },
    ]

    for cfg in configs:
        print(f"# {cfg['description']}")
        print(f"  {cfg['cmd']}\n")


def show_word2vec_commands():
    """
    Show Word2Vec experiment commands.
    """
    print("=== Word2Vec Experiment Commands ===\n")

    steps = [
        ("Build C binaries", "cd Word2Vec && make"),
        ("Prepare text8 data", "bash Word2Vec/scripts/create-text8-data.sh"),
        ("Prepare fil9 data", "bash Word2Vec/scripts/create-fil9-data.sh"),
        ("Train text8 (finite)", "bash Word2Vec/scripts/train-text8.sh"),
        ("Train text8 (infinite)", "bash Word2Vec/scripts/train-text8-inf.sh"),
        ("Train fil9 (finite)", "bash Word2Vec/scripts/train-fil9.sh"),
        ("Train fil9 (infinite)", "bash Word2Vec/scripts/train-fil9-inf.sh"),
        ("Evaluate embeddings", "bash Word2Vec/scripts/evaluate.sh"),
    ]

    for name, cmd in steps:
        print(f"# {name}")
        print(f"  {cmd}\n")


if __name__ == "__main__":
    print("TP4 MAML Training Demo\n")
    demonstrate_metalearner_api()
    show_training_command_equivalents()
    show_word2vec_commands()

    # Optionally build dataset if data path provided
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
        print(f"\n=== Building Omniglot Dataset from {data_folder} ===")
        dataset = build_omniglot_dataset(data_folder, num_ways=5, num_shots=1)
        if dataset is not None:
            print("Dataset built successfully.")
    else:
        print("\nTip: Pass a data folder path as argument to test dataset loading.")
        print("  python maml_training_demo.py /path/to/omniglot/data")
```

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

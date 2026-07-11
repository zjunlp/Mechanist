---
name: task-vectors
description: Use this skill when working with task arithmetic for editing neural network models, including creating task vectors from pre-trained and fine-tuned checkpoints, combining them via arithmetic operations (negation, addition, analogies), and applying them to CLIP vision models for multi-task learning.
---

# Task Vectors — Editing Models with Task Arithmetic

## When to Use

Activate this skill when you need to:
- Edit pre-trained model behavior without retraining from scratch
- Combine multiple fine-tuned models into a single multi-task model
- Negate unwanted capabilities or biases from a pre-trained model
- Perform task analogies across model weight spaces
- Work with CLIP ViT-B/32, ViT-B/16, or ViT-L/14 checkpoints
- Apply parameter-space arithmetic to neural network weights

**Trigger keywords:** task vectors, task arithmetic, model editing, weight space, fine-tuned checkpoints, negation, model merging, multi-task model, CLIP editing

## Quick Reference

- **Paper:** [Editing Models with Task Arithmetic (ICLR 2023)](https://arxiv.org/abs/2212.04089)
- **Repository:** https://github.com/mlfoundations/task_vectors
- **Checkpoints:** [Google Drive](https://drive.google.com/drive/folders/1u_Tva6x0p6oxu5Eo0ZZsf-520Cc_3MKw?usp=share_link)
- **Core module:** `src/task_vectors.py`

## Installation / Setup

### Prerequisites
- conda (Anaconda or Miniconda)
- Python (version managed by conda environment)

### Step 1: Create and activate conda environment
```bash
conda env create
conda activate task-vectors
```

### Step 2: Add source directory to PYTHONPATH
```bash
cd task_vectors
export PYTHONPATH="$PYTHONPATH:$PWD"
```

### Step 3: Download checkpoints
Download CLIP ViT-B/32, ViT-B/16, and ViT-L/14 checkpoints (pre-trained zero-shot + fine-tuned on 8 tasks) from:
https://drive.google.com/drive/folders/1u_Tva6x0p6oxu5Eo0ZZsf-520Cc_3MKw?usp=share_link

Expected checkpoint layout:

## Demo Scripts

### `scripts/task_vectors_demo.py`

```python
#!/usr/bin/env python3
"""
Task Vectors Demo: Editing Models with Task Arithmetic

This script demonstrates how to use the task_vectors library to:
1. Create task vectors from pre-trained and fine-tuned CLIP checkpoints
2. Negate a task vector to degrade performance on a specific task
3. Add multiple task vectors together for multi-task performance
4. Perform task analogies

Requirements:
- conda activate task-vectors
- export PYTHONPATH="$PYTHONPATH:/path/to/task_vectors"
- Download checkpoints from:
  https://drive.google.com/drive/folders/1u_Tva6x0p6oxu5Eo0ZZsf-520Cc_3MKw

Usage:
    python task_vectors_demo.py --model ViT-L-14 --data_location /path/to/data
"""

import sys
import os

# ---------------------------------------------------------------------------
# NOTE: Add the src/ directory to the path before importing task_vectors.
# Adjust this path to match your local clone of mlfoundations/task_vectors.
# ---------------------------------------------------------------------------
REPO_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if os.path.isdir(REPO_SRC):
    sys.path.insert(0, os.path.abspath(REPO_SRC))


def demo_create_task_vector(
    pretrained_checkpoint: str,
    finetuned_checkpoint: str,
):
    """
    Demonstrate creating a TaskVector from two checkpoints.

    Args:
        pretrained_checkpoint: Path to the pre-trained (zero-shot) .pt file.
        finetuned_checkpoint:  Path to the fine-tuned .pt file.

    Returns:
        TaskVector instance.
    """
    from task_vectors import TaskVector  # noqa: PLC0415  (lazy import after path setup)

    print(f"[1] Creating task vector from:\n"
          f"    pretrained : {pretrained_checkpoint}\n"
          f"    finetuned  : {finetuned_checkpoint}")

    task_vector = TaskVector(pretrained_checkpoint, finetuned_checkpoint)
    print(f"    Task vector created. Keys in vector: {len(task_vector.vector)}")
    return task_vector


def demo_negate_task_vector(
    task_vector,
    pretrained_checkpoint: str,
    scaling_coef: float = 0.5,
):
    """
    Demonstrate negating a task vector and applying it to a pre-trained model.

    Negating a task vector decreases performance on the target task while
    having little effect on other tasks.

    Args:
        task_vector:           A TaskVector instance.
        pretrained_checkpoint: Path to the pre-trained (zero-shot) .pt file.
        scaling_coef:          Scaling coefficient controlling the step size (0–1).

    Returns:
        Image encoder with the negated task vector applied.
    """
    print(f"\n[2] Negating task vector (scaling_coef={scaling_coef}) ...")
    neg_task_vector = -task_vector
    image_encoder = neg_task_vector.apply_to(pretrained_checkpoint, scaling_coef=scaling_coef)
    print("    Negated task vector applied to pre-trained model.")
    return image_encoder


def demo_add_task_vectors(
    pretrained_checkpoint: str,
    finetuned_checkpoints: dict,
    scaling_coef: float = 0.8,
):
    """
    Demonstrate adding multiple task vectors and applying the sum.

    Adding task vectors combines capabilities so the resulting model
    performs well on all included tasks simultaneously.

    Args:
        pretrained_checkpoint:  Path to the pre-trained (zero-shot) .pt file.
        finetuned_checkpoints:  Dict mapping dataset name -> finetuned .pt path.
        scaling_coef:           Scaling coefficient (0–1).

    Returns:
        Image encoder with summed task vector applied.
    """
    from task_vectors import TaskVector  # noqa: PLC0415

    print(f"\n[3] Adding task vectors for datasets: {list(finetuned_checkpoints.keys())}")

    task_vectors = [
        TaskVector(pretrained_checkpoint, ckpt)
        for ckpt in finetuned_checkpoints.values()
    ]

    # Use Python's built-in sum (relies on TaskVector.__add__ and __radd__)
    task_vector_sum = sum(task_vectors)
    print(f"    Combined {len(task_vectors)} task vectors via sum().")

    image_encoder = task_vector_sum.apply_to(pretrained_checkpoint, scaling_coef=scaling_coef)
    print(f"    Sum task vector applied (scaling_coef={scaling_coef}).")
    return image_encoder


def demo_task_analogy(
    pretrained_checkpoint: str,
    checkpoint_a: str,
    checkpoint_b: str,
    checkpoint_c: str,
    scaling_coef: float = 0.8,
):
    """
    Demonstrate a task analogy: new_vector = C + B - A.

    If 'A is to B as C is to D', combining three task vectors can improve
    performance on the fourth task D without any training data for D.

    Args:
        pretrained_checkpoint: Path to the pre-trained (zero-shot) .pt file.
        checkpoint_a:          Fine-tuned checkpoint for task A.
        checkpoint_b:          Fine-tuned checkpoint for task B.
        checkpoint_c:          Fine-tuned checkpoint for task C.
        scaling_coef:          Scaling coefficient (0–1).

    Returns:
        Image encoder with the analogy task vector applied.
    """
    from task_vectors import TaskVector  # noqa: PLC0415

    print("\n[4] Computing task analogy: tv_C + tv_B - tv_A ...")
    tv_a = TaskVector(pretrained_checkpoint, checkpoint_a)
    tv_b = TaskVector(pretrained_checkpoint, checkpoint_b)
    tv_c = TaskVector(pretrained_checkpoint, checkpoint_c)

    analogy_vector = tv_c + tv_b - tv_a
    image_encoder = analogy_vector.apply_to(pretrained_checkpoint, scaling_coef=scaling_coef)
    print("    Analogy task vector applied.")
    return image_encoder


def demo_evaluate(image_encoder, dataset_name: str, args):
    """
    Evaluate an image encoder on a given dataset using the repo's eval module.

    Args:
        image_encoder: The modified image encoder returned by apply_to().
        dataset_name:  Name of the dataset (e.g., 'MNIST', 'ImageNet').
        args:          Parsed argument namespace (from parse_arguments()).
    """
    from eval import eval_single_dataset  # noqa: PLC0415

    print(f"\n[5] Evaluating on dataset: {dataset_name}")
    metrics = eval_single_dataset(image_encoder, dataset_name, args)
    print(f"    Results on {dataset_name}: {metrics}")
    return metrics


def main():
    """
    Run a full task vector workflow using placeholder checkpoint paths.

    To run end-to-end:
    1. Download checkpoints from the Google Drive link in README.
    2. Set CHECKPOINT_DIR and DATA_DIR below.
    3. Run: python task_vectors_demo.py
    """
    # -----------------------------------------------------------------------
    # CONFIGURATION — update these paths before running
    # -----------------------------------------------------------------------
    CHECKPOINT_DIR = "/path/to/checkpoints"   # <-- set this
    DATA_DIR       = "/path/to/data"           # <-- set this
    MODEL          = "ViT-L-14"               # ViT-B-32 | ViT-B-16 | ViT-L-14
    DATASETS       = ["MNIST", "RESISC45"]
    # -----------------------------------------------------------------------

    pretrained = os.path.join(CHECKPOINT_DIR, MODEL, "zeroshot.pt")
    finetuned  = {
        ds: os.path.join(CHECKPOINT_DIR, MODEL, ds, "finetuned.pt")
        for ds in DATASETS
    }

    # Guard: skip real execution if paths are placeholders
    if not os.path.exists(pretrained):
        print("=" * 60)
        print("DEMO MODE — checkpoint paths are placeholders.")
        print("Update CHECKPOINT_DIR and DATA_DIR in main() to run end-to-end.")
        print("=" * 60)
        _run_structural_demo()
        return

    # ---- Real execution ----
    try:
        from args import parse_arguments  # noqa: PLC0415
        args = parse_arguments()
        args.data_location = DATA_DIR
        args.model = MODEL
        args.save  = os.path.join(CHECKPOINT_DIR, MODEL)
    except Exception as exc:
        print(f"Could not parse arguments: {exc}")
        return

    # 1. Create a task vector
    tv_mnist = demo_create_task_vector(pretrained, finetuned["MNIST"])

    # 2. Negate it and evaluate
    neg_encoder = demo_negate_task_vector(tv_mnist, pretrained, scaling_coef=0.5)
    demo_evaluate(neg_encoder, "MNIST", args)
    demo_evaluate(neg_encoder, "ImageNet", args)

    # 3. Add task vectors and evaluate
    multi_encoder = demo_add_task_vectors(pretrained, finetuned, scaling_coef=0.8)
    for ds in DATASETS:
        demo_evaluate(multi_encoder, ds, args)


def _run_structural_demo():
    """
    Demonstrate the API structure without requiring real checkpoints.
    Uses mock objects to show the call signatures and operator overloading.
    """
    print("\n--- Structural / API demonstration (no real checkpoints) ---\n")

    # Show how TaskVector arithmetic operators work conceptually
    class MockVector:
        """Minimal stand-in showing operator signatures expected by TaskVector."""

        def __init__(self, name: str):
            self.name = name
            self.vector = {"layer.weight": f"tensor_{name}"}

        def __neg__(self):
            result = MockVector(f"-{self.name}")
            return result

        def __add__(self, other: "MockVector") -> "MockVector":
            return MockVector(f"({self.name} + {other.name})")

        def __radd__(self, other):
            # Needed for sum([tv1, tv2, ...]) since sum starts with 0
            if other == 0:
                return self
            return self.__add__(other)

        def __sub__(self, other: "MockVector") -> "MockVector":
            return self.__add__(-other)

        def apply_to(self, pretrained_checkpoint: str, scaling_coef: float = 1.0):
            print(f"  apply_to({pretrained_checkpoint!r}, scaling_coef={scaling_coef})")
            print(f"  => image_encoder modified by vector: {self.name}")
            return f"encoder[{self.name}]"

        def __repr__(self):
            return f"MockVector('{self.name}')"

    tv_a = MockVector("MNIST")
    tv_b = MockVector("RESISC45")
    tv_c = MockVector("EuroSAT")

    print("Creating task vectors:")
    print(f"  tv_a = {tv_a}")
    print(f"  tv_b = {tv_b}")
    print(f"  tv_c = {tv_c}")

    print("\nNegation:  -tv_a =", -tv_a)
    print("Addition:  tv_a + tv_b =", tv_a + tv_b)
    print("Sum list:  sum([tv_a, tv_b, tv_c]) =", sum([tv_a, tv_b, tv_c]))
    print("Analogy:   tv_c + tv_b - tv_a =", tv_c + tv_b - tv_a)

    print("\nApplying negated vector:")
    neg_tv = -tv_a
    neg_tv.apply_to("checkpoints/ViT-L-14/zeroshot.pt", scaling_coef=0.5)

    print("\nApplying summed vector:")
    summed = sum([tv_a, tv_b])
    summed.apply_to("checkpoints/ViT-L-14/zeroshot.pt", scaling_coef=0.8)

    print("\nDone. Replace MockVector usage with real TaskVector and actual checkpoint paths.")


if __name__ == "__main__":
    main()
```

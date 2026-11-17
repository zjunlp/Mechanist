---
name: task-vectors
description: "Use this skill when working with task arithmetic for editing neural network models, including creating task vectors from pre-trained and fine-tuned checkpoints, combining them via arithmetic operations (negation, addition, analogies), and applying them to CLIP vision models for multi-task learning."
---

## Method and use

Construct task vectors from compatible pretrained and fine-tuned weights; compare addition, subtraction, scaling, and analogy operations. Parameter coordinates and checkpoints must align. Useful downstream transfer is not by itself a localized causal explanation. Structural mock examples are demonstrations only.


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


See [`scripts/task_vectors_demo.py`](scripts/task_vectors_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).

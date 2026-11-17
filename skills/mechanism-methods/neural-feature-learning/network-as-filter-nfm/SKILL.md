---
name: convrfm
description: "Use this skill when working with convolutional neural feature ansatz (CNFA), deep convolutional recursive feature machines (Deep ConvRFM), or tasks involving kernel-based feature learning with convolutional architectures, VGG networks, patch-based Jacobian computation, and EGOP (expected gradient outer product) analysis on image datasets such as ImageNet and CIFAR."
---

## Method and use

Study convolutional feature learning through patches, Jacobians, expected gradient outer products, and filter geometry. Match patch extraction and gradient coordinates. Toy networks and synthetic examples illustrate computations; evaluate real-model claims on the relevant distribution.


# Convrfm skill

## When to use

Activate this skill when:

- Implementing or experimenting with the convolutional neural feature ansatz (CNFA)
- Training or evaluating deep convolutional recursive feature machines (Deep ConvRFM)
- Computing expected gradient outer products (EGOP) for patch-based convolutional layers
- Verifying neural feature ansatz properties in pretrained or VGG-style networks
- Extracting feature embeddings from convolutional neural networks for kernel analysis
- Running binary or multiclass classification experiments on image datasets using RFM-based methods
- Generating toy datasets for testing convolutional feature learning pipelines
- Analyzing hyperparameter sensitivity of CNFA-based models
- Visualizing VGG kernel eigenvectors or passing eigenvectors through network layers

Keywords that trigger this skill: CNFA, convolutional neural feature ansatz, ConvRFM, deep RFM, recursive feature machine, EGOP, patch Jacobian, VGG features, kernel learning, convolutional kernel, imagenet features, patchify, conv embedding.

---

## Quick reference

- **Repository:** https://github.com/aradha/convrfm
- **Primary language:** Python
- **Description:** Code for convolutional neural feature ansatz and deep ConvRFM
- **Related paper concepts:** Neural Feature Ansatz (NFA), Recursive Feature Machines (RFM), Expected Gradient Outer Product (EGOP), convolutional patch kernels
- **No official documentation site or demo URL is provided by the repository**

---

## Installation/setup

### Prerequisites

- Python 3.7+
- PyTorch (with CUDA support recommended for large-scale experiments)
- torchvision
- NumPy
- SciPy (for kernel/eigenvalue computations)
- h5py (for dataset loading)

### Install dependencies

```bash
pip install torch torchvision numpy scipy h5py
```

### Clone the repository

```bash
git clone https://github.com/aradha/convrfm.git
cd convrfm
```

### Dataset setup

- **ImageNet:** Provide a local path to the ImageNet dataset directory. The loader expects the standard ImageNet folder structure.
- **CIFAR / toy data:** Use the provided `gen_toy_data.py` script to generate synthetic datasets for quick experimentation.

```bash
python gen_toy_data.py
```

---

## Core features

- **Convolutional neural feature ansatz (CNFA) verification:** Verify that the EGOP of a trained convolutional network matches its learned kernel features, using pretrained and VGG-based networks (`cnfa_verification/`).

- **Deep ConvRFM training:** Iteratively train convolutional recursive feature machines that refine feature representations through gradient-based kernel updates (`deep_conv_rfm/`).

- **Convolutional network training:** Train standard and binary classification convolutional networks on image datasets with utilities for embedding extraction and model evaluation (`conv_nets/`).

- **Patch-based Jacobian computation:** Decompose convolutional network outputs into patch-level Jacobians, enabling per-patch feature analysis and EGOP estimation (`cnfa_verification/pretrained_conv_nfa.py`, `cnfa_verification/vgg_conv_nfa.py`).

- **EGOP computation:** Compute the expected gradient outer product over a dataset to derive the effective feature matrix for kernel comparisons.

- **VGG kernel visualization:** Compute and visualize eigenvectors of VGG-derived kernels, and pass eigenvectors through network layers for interpretability (`vgg_vis/`).

- **Hyperparameter CNFA verification:** Study the effect of hyperparameters on CNFA properties, including correlation analysis across training regimes (`hyperparam_cnfa_verification/`).

- **Binary classification support:** Specialized pipelines for binary classification tasks with filter extraction utilities (`conv_nets/binary_main.py`, `deep_conv_rfm/binary_main.py`).

- **Flexible dataset utilities:** Custom dataset classes for ImageNet and other image datasets with configurable batch sizes and preprocessing (`cnfa_verification/dataset.py`, `cnfa_verification/loader.py`).

- **Toy data generation:** Generate synthetic datasets to test and validate pipeline components without requiring large real-world datasets (`gen_toy_data.py`).

---

## Usage examples

> Note: The repository README does not contain inline code examples. The following examples are derived directly from analysis of the repository source files.

### Generate toy data

```bash
python gen_toy_data.py
```

### Train a convolutional network (multiclass)

```bash
cd conv_nets
python main.py
```

### Train a convolutional network (binary classification)

```bash
cd conv_nets
python binary_main.py
```

### Run deep ConvRFM (multiclass)

```bash
cd deep_conv_rfm
python main.py
```

### Run deep ConvRFM (binary classification)

```bash
cd deep_conv_rfm
python binary_main.py
```

### Run CNFA verification with a pretrained network

```bash
cd cnfa_verification
python pretrained_conv_nfa.py
```

### Run CNFA verification with VGG

```bash
cd cnfa_verification
python vgg_conv_nfa.py
```

### Run VGG kernel visualization

```bash
cd vgg_vis
python main.py
```

### Run hyperparameter CNFA verification

```bash
cd hyperparam_cnfa_verification
python main.py
```

---

## Key APIs/models

### Classes

| Class | Module | Description |
|---|---|---|
| `PatchConvLayer` | `cnfa_verification/pretrained_conv_nfa.py` | Wraps a convolutional layer to operate on patchified inputs for Jacobian/EGOP computation |
| `PatchBasicBlock` | `cnfa_verification/pretrained_conv_nfa.py` | Patch-based wrapper for ResNet BasicBlock layers |
| `PatchBottleneck` | `cnfa_verification/pretrained_conv_nfa.py` | Patch-based wrapper for ResNet Bottleneck layers |
| `PatchConvLayer` | `cnfa_verification/vgg_conv_nfa.py` | Patch-based convolutional layer wrapper for VGG-style networks |
| `ImageNet` | `cnfa_verification/loader.py` | Custom PyTorch Dataset class for loading ImageNet with transforms |
| `MyDataset` | `conv_nets/binary_main.py` | Custom dataset class for binary classification experiments |

### Key functions

| Function | Module | Description |
|---|---|---|
| `patchify(x, patch_size, stride_size)` | `cnfa_verification/pretrained_conv_nfa.py` | Extracts overlapping patches from input tensor `x` |
| `get_jacobian(net, data, c_idx)` | `cnfa_verification/pretrained_conv_nfa.py` | Computes the Jacobian of network output w.r.t. input patches for class index `c_idx` |
| `egop(model, X)` | `cnfa_verification/pretrained_conv_nfa.py` | Computes the expected gradient outer product (EGOP) over dataset `X` using `model` |
| `patchify(x, patch_size, stride_size)` | `cnfa_verification/vgg_conv_nfa.py` | Patch extraction for VGG-style feature maps |
| `get_jacobian(net, data, c_idx)` | `cnfa_verification/vgg_conv_nfa.py` | Jacobian computation for VGG-based networks |
| `egop(model, z)` | `cnfa_verification/vgg_conv_nfa.py` | EGOP computation for VGG-based models |
| `get_imagenet(batch_size, path)` | `cnfa_verification/dataset.py` | Returns a DataLoader for ImageNet given batch size and dataset path |
| `get_filter(net, layer)` | `conv_nets/binary_main.py` | Extracts filter weights from a specified layer of network `net` |
| `get_classes(X_full, y_full, c1)` | `conv_nets/binary_main.py` | Filters dataset to return samples belonging to class `c1` for binary tasks |

### Sub-modules

| Module | Purpose |
|---|---|
| `cnfa_verification/` | CNFA verification using pretrained ResNet and VGG networks |
| `conv_nets/` | Standard CNN training, embedding extraction, and evaluation utilities |
| `deep_conv_rfm/` | Deep ConvRFM training loop, gradient computation, and model definitions |
| `hyperparam_cnfa_verification/` | Hyperparameter sensitivity analysis for CNFA |
| `vgg_vis/` | VGG kernel eigenvector computation and visualization |

---

## Common patterns and best practices

- **Patchify before Jacobian computation:** Always apply `patchify(x, patch_size, stride_size)` to input tensors before passing them to `get_jacobian`. Patch size and stride should match the receptive field of the target convolutional layer.

- **EGOP over batches:** For large datasets like ImageNet, compute EGOP in mini-batches and accumulate to avoid memory overflow. The `egop` function takes a model and a data tensor `X`; ensure `X` is moved to the appropriate device before calling.

- **Binary vs multiclass pipelines:** Use `binary_main.py` for two-class problems and `main.py` for multiclass. The binary pipeline uses `get_classes` to filter datasets and `get_filter` to inspect learned filters.

- **Dataset paths:** When using `get_imagenet(batch_size, path)`, ensure `path` points to the root ImageNet directory containing `train/` and `val/` subdirectories in the standard ImageNet folder format.

- **Device management:** The codebase is designed for GPU use. Always set tensors and models to `.cuda()` or the appropriate device before running Jacobian or EGOP computations.

- **Gradient computation:** When calling `get_jacobian`, ensure the model is in evaluation mode (`model.eval()`) and that `torch.no_grad()` is not active, since Jacobian computation requires gradient tracking.

- **VGG visualization workflow:** Use `vgg_vis/kernel.py` to compute kernels, then `vgg_vis/pass_eigvs.py` to propagate eigenvectors through the network, and finally `vgg_vis/main.py` to orchestrate the full visualization pipeline.

- **Toy data for debugging:** Use `gen_toy_data.py` to generate small synthetic datasets when debugging pipeline components before scaling to ImageNet or CIFAR.

## Demo Scripts

### `scripts/egop_and_patchify_demo.py`


See [`scripts/egop_and_patchify_demo.py`](scripts/egop_and_patchify_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

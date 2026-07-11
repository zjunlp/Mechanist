---
name: clip-dissect
description: Use this skill when you need to automatically describe or interpret the functionality of individual neurons in deep neural networks (DNNs) using CLIP-based semantic analysis, perform mechanistic interpretability research on vision models, dissect convolutional or transformer-based image classifiers, identify what visual concepts activate specific neurons, or compare neuron descriptions across different probing datasets and concept sets.
---

# CLIP-Dissect Skill

## When to Use

Activate this skill when:
- You need to **automatically describe** what individual neurons in a deep vision network respond to
- You are performing **mechanistic interpretability** or **explainable AI** research on CNNs or Vision Transformers
- You want to understand **neuron-level representations** in models like ResNet-50, ResNet-18, ViT, or custom models
- You need to **compare neuron descriptions** against baselines like NetDissect or MILAN
- You want to probe neural network layers using a **concept set** (e.g., 3k, 10k, 20k English words)
- You are working with **Broden** or **ImageNet** as a probing dataset
- You need to evaluate how well neuron descriptions **predict class-level behavior** in a model
- Keywords: `neuron dissection`, `CLIP`, `neural network interpretability`, `concept-based explanations`, `network dissection`, `probe dataset`, `activation analysis`, `feature visualization`

---

## Quick Reference

- **Paper:** [CLIP-Dissect: Automatic Description of Neuron Representations in Deep Vision Networks](https://arxiv.org/abs/2204.10965) — ICLR 2023 Spotlight
- **Repository:** https://github.com/Trustworthy-ML-Lab/CLIP-dissect
- **CLIP Source:** https://github.com/openai/CLIP
- **Broden Dataset:** Downloaded via `bash dlbroden.sh` (based on [NetDissect-Lite](https://github.com/CSAILVision/NetDissect-Lite))
- **Concept Sets:** Google 10k/20k words (https://github.com/first20hours/google-10000-english), EF 3k words (https://www.ef.edu/english-resources/english-vocabulary/top-3000-words/)
- **PyTorch Install:** https://pytorch.org/get-started/previous-versions/

---

## Installation / Setup

### Prerequisites
- Python 3.10
- PyTorch >= 1.12.0 (also compatible with 2.0), Torchvision >= 0.13
- CUDA-compatible GPU recommended (CPU inference supported)

### Step-by-Step Installation

```bash
# Step 1: Clone the repository
git clone https://github.com/Trustworthy-ML-Lab/CLIP-dissect.git
cd CLIP-dissect

# Step 2: Install Python 3.10 (if not already installed)
# Using conda:
conda create -n clip_dissect python=3.10
conda activate clip_dissect

# Step 3: Install PyTorch and Torchvision (tested with 1.12.0, also works with 2.0)
# Visit https://pytorch.org/get-started/previous-versions/ for exact commands.
# Example for CUDA 11.3:
pip install torch==1.12.0+cu113 torchvision==0.13.0+cu113 --extra-index-url https://download.pytorch.org/whl/cu113

# Step 4: Install remaining dependencies
pip install -r requirements.txt

# Step 5: Download the Broden dataset (images only)
bash dlbroden.sh

# Step 6 (Optional): Download ResNet-18 pretrained on Places-365
bash dlzoo_example.sh
```

### ImageNet Setup (Optional)
To evaluate using ImageNet validation set, set the correct path in `data_utils.py`:
```python
DATASET_ROOTS = {
    "imagenet_val": "/path/to/your/imagenet/val",
    ...
}
```

---

## Core Features

- **Automatic Neuron Description:** Assigns human-readable concept labels to individual neurons in any layer of a DNN using CLIP's vision-language embeddings.
- **Efficient Similarity Computation:** Uses cosine similarity between neuron activation patterns and CLIP text embeddings of candidate concepts.
- **Multi-Layer Dissection:** Dissect multiple layers of a target model in a single run (e.g., `layer1`, `layer2`, `layer3`, `layer4`, `fc` for ResNet-50).
- **Flexible Probing Datasets:** Supports Broden, ImageNet validation set, and custom torchvision-compatible datasets.
- **Flexible Concept Sets:** Bundled concept sets with 3k, 10k, and 20k English words; supports custom `.txt` concept files.
- **Activation Caching:** Automatically caches computed activations in `saved_activations/` to avoid recomputation on repeated runs.
- **Model Agnostic:** Works with any PyTorch model — ResNet, ViT, custom architectures — by implementing a simple loader function.
- **Experiment Notebooks:** Reproduces all paper figures and tables via Jupyter notebooks in `experiments/`.
- **Comparison Baselines:** Includes pre-computed results from NetDissect and MILAN for direct comparison.
- **Device Flexibility:** Runs on CUDA GPU or CPU via `--device` argument.

---

## Usage Examples

### Quickstart — Dissect ResNet-50 (ImageNet) with Broden

Dissects 5 layers of ResNet-50 pretrained on ImageNet using Broden as the probing dataset. Results saved in `results/resnet50_{datetime}/descriptions.csv`.

```bash
python describe_neurons.py
```

### Dissect a Custom Model

1. Implement your model loader in `data_utils.py` under `get_target_model`:

```python
def get_target_model(target_name, device):
    if target_name == "my_custom_model":
        model = MyCustomModel()
        model.load_state_dict(torch.load("path/to/weights.pth"))
        model.eval()
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        return model, preprocess
```

2. Run dissection:

```bash
python describe_neurons.py --target_model my_custom_model
```

### Using a Custom Probing Dataset

1. Implement dataset loading in `data_utils.py` under `get_data`:

```python
def get_data(dataset_name, preprocess):
    if dataset_name == "my_dataset":
        return MyDataset(root="/path/to/data", transform=preprocess)
```

2. Add dataset name to `--d_probe` choices in `describe_neurons.py`.

3. Run:

```bash
python describe_neurons.py --d_probe my_dataset
```

### Using a Custom Concept Set

```bash
python describe_neurons.py --concept_set /path/to/my_concepts.txt
```

Each line of the `.txt` file should contain one concept word or phrase.

### Specifying Device

```bash
# Use CPU instead of GPU
python describe_neurons.py --device cpu

# Use a specific GPU
python describe_neurons.py --device cuda:1
```

### Reproducing Paper Results

```bash
# Reproduce Table 1 (ResNet-50 ImageNet quantitative results)
jupyter notebook experiments/table1_quantitative_rn50.ipynb

# Reproduce Table 2 (ResNet-18 Places quantitative results)
jupyter notebook experiments/table2_quantitative_rn18.ipynb

# Reproduce Figure 1, 6, 7, 9 (qualitative comparisons)
jupyter notebook experiments/fig_1_6_7_9_qualitative_comparison.ipynb
```

### Full CLI Reference

```bash
python describe_neurons.py \
    --target_model resnet50 \
    --d_probe broden \
    --concept_set data/20k.txt \
    --batch_size 200 \
    --device cuda \
    --pool_mode avg \
    --save_dir results/
```

---

## Key APIs / Models

### Target Models Supported
| Model Name | Architecture | Dataset |
|---|---|---|
| `resnet50` | ResNet-50 | ImageNet (torchvision pretrained) |
| `resnet18_places` | ResNet-18 | Places-365 (downloaded via `dlzoo_example.sh`) |
| Custom models | Any PyTorch model | User-defined |
| ViT variants | Vision Transformer | Supported (see `fig11_vit_qualitative.ipynb`) |

### Probing Datasets
| Dataset Name | Description |
|---|---|
| `broden` | Broden dataset — diverse visual concepts (downloaded via `dlbroden.sh`) |
| `imagenet_val` | ImageNet validation set (user must provide path) |
| Custom | User-defined torchvision Dataset |

### Concept Sets (bundled in `data/`)
| File | Size | Source |
|---|---|---|
| `data/3k.txt` | 3,000 words | EF English vocabulary |
| `data/10k.txt` | 10,000 words | Google 10k English |
| `data/20k.txt` | 20,000 words | Google 20k English |

### Core Functions

#### `describe_neurons.py` (main entry point)

## Demo Scripts

### `scripts/run_clip_dissect.py`

```python
#!/usr/bin/env python3
"""
CLIP-Dissect: Automated Neuron Description for Deep Vision Networks

This script demonstrates how to use the CLIP-Dissect pipeline to:
1. Load a pretrained target model (ResNet-50)
2. Load a probing dataset (Broden)
3. Compute neuron activations and CLIP text embeddings
4. Compute cosine similarity between neuron activations and concept embeddings
5. Save per-neuron descriptions to a CSV file

Requirements:
    - Clone https://github.com/Trustworthy-ML-Lab/CLIP-dissect
    - pip install -r requirements.txt
    - bash dlbroden.sh  (to download Broden dataset)
    - Must be run from within the CLIP-dissect repository root directory

Usage:
    cd /path/to/CLIP-dissect
    python scripts/run_clip_dissect.py
"""

import os
import sys
import csv
import datetime
import argparse
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms, models

# ── Adjust import path so we can import from the repo root ───────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

try:
    import clip  # bundled CLIP from clip/
    from data_utils import get_target_model, get_data, get_resnet_imagenet_preprocess
except ImportError as e:
    print(f"[ERROR] Could not import CLIP-Dissect modules: {e}")
    print("Make sure you are running this script from the CLIP-dissect repository root,")
    print("or that REPO_ROOT is set correctly.")
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_TARGET_MODEL = "resnet50"
DEFAULT_PROBE_DATASET = "broden"
DEFAULT_CONCEPT_SET = os.path.join(REPO_ROOT, "data", "20k.txt")
DEFAULT_SAVE_DIR = os.path.join(REPO_ROOT, "results")
DEFAULT_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_BATCH_SIZE = 64
CLIP_MODEL_NAME = "ViT-B/32"


def load_concept_set(concept_set_path: str) -> list[str]:
    """
    Load a list of concept strings from a plain-text file.

    Each line in the file should contain exactly one concept (word or phrase).

    Args:
        concept_set_path: Path to the .txt concept set file.

    Returns:
        A list of concept strings (lowercased, whitespace-stripped).

    Raises:
        FileNotFoundError: If the concept set file does not exist.
    """
    if not os.path.exists(concept_set_path):
        raise FileNotFoundError(
            f"Concept set file not found: {concept_set_path}\n"
            "Make sure to run from the CLIP-dissect repository root "
            "or provide the correct path."
        )
    with open(concept_set_path, "r", encoding="utf-8") as f:
        concepts = [line.strip().lower() for line in f if line.strip()]
    print(f"[INFO] Loaded {len(concepts)} concepts from '{concept_set_path}'")
    return concepts


def compute_clip_text_embeddings(
    concepts: list[str],
    clip_model,
    device: str,
    batch_size: int = 256,
) -> torch.Tensor:
    """
    Compute normalized CLIP text embeddings for a list of concept strings.

    Uses the bundled CLIP tokenizer and text encoder. Embeddings are computed
    in batches to avoid memory overflow for large concept sets.

    Args:
        concepts:   List of concept strings.
        clip_model: A loaded CLIP model (from clip.load()).
        device:     Torch device string, e.g. 'cuda' or 'cpu'.
        batch_size: Number of concepts to encode per batch.

    Returns:
        Tensor of shape (num_concepts, embedding_dim) — L2-normalized.
    """
    clip_model.eval()
    all_embeddings = []

    print(f"[INFO] Computing CLIP text embeddings for {len(concepts)} concepts ...")
    with torch.no_grad():
        for start in range(0, len(concepts), batch_size):
            batch = concepts[start : start + batch_size]
            tokens = clip.tokenize(batch, truncate=True).to(device)
            text_features = clip_model.encode_text(tokens)
            text_features = F.normalize(text_features, dim=-1)
            all_embeddings.append(text_features.cpu())
            if (start // batch_size) % 10 == 0:
                print(f"  ... processed {min(start + batch_size, len(concepts))}/{len(concepts)} concepts")

    embeddings = torch.cat(all_embeddings, dim=0)  # (N_concepts, D)
    print(f"[INFO] Text embedding matrix shape: {embeddings.shape}")
    return embeddings


def compute_neuron_activations(
    model: torch.nn.Module,
    layer_name: str,
    dataloader: DataLoader,
    device: str,
    pool_mode: str = "avg",
) -> torch.Tensor:
    """
    Compute pooled activations of a specific layer for all images in a dataloader.

    Uses PyTorch forward hooks to capture intermediate layer outputs.
    Spatial dimensions are pooled (avg or max) to produce a single scalar
    per neuron per image.

    Args:
        model:      PyTorch model in eval mode.
        layer_name: Dot-separated layer name accessible via model.named_modules(),
                    e.g. 'layer4' or 'layer4.1.conv2'.
        dataloader: DataLoader yielding (image_tensor, label) batches.
        device:     Torch device string.
        pool_mode:  'avg' for average pooling or 'max' for max pooling over spatial dims.

    Returns:
        Tensor of shape (num_images, num_neurons) — pooled activations.

    Raises:
        ValueError: If the layer_name is not found in the model.
    """
    # Locate the target layer by name
    target_layer = None
    for name, module in model.named_modules():
        if name == layer_name:
            target_layer = module
            break

    if target_layer is None:
        available = [n for n, _ in model.named_modules() if n]
        raise ValueError(
            f"Layer '{layer_name}' not found in model.\n"
            f"Available layers: {available[:20]} ..."
        )

    # Register a forward hook to capture activations
    activation_buffer = []

    def hook_fn(module, input, output):
        # output shape: (batch, channels, H, W) for conv layers
        # or (batch, features) for linear layers
        if output.dim() == 4:
            # Spatial pooling
            if pool_mode == "avg":
                pooled = output.mean(dim=(2, 3))
            else:
                pooled = output.amax(dim=(2, 3))
        else:
            pooled = output
        activation_buffer.append(pooled.detach().cpu())

    hook = target_layer.register_forward_hook(hook_fn)

    model.eval()
    print(f"[INFO] Collecting activations from layer '{layer_name}' ...")
    try:
        with torch.no_grad():
            for batch_idx, (images, _) in enumerate(dataloader):
                images = images.to(device)
                _ = model(images)
                if batch_idx % 20 == 0:
                    print(f"  ... processed batch {batch_idx + 1}/{len(dataloader)}")
    finally:
        hook.remove()

    activations = torch.cat(activation_buffer, dim=0)  # (N_images, N_neurons)
    print(f"[INFO] Activation matrix shape: {activations.shape}")
    return activations


def compute_neuron_clip_similarity(
    activations: torch.Tensor,
    clip_text_embeddings: torch.Tensor,
    clip_model,
    dataloader: DataLoader,
    device: str,
    batch_size: int = 64,
) -> torch.Tensor:
    """
    Compute the similarity between each neuron and each concept.

    For each neuron, we compute the weighted average of CLIP image embeddings,
    weighted by the neuron's activation for each image. The resulting vector
    is then compared (cosine similarity) against all concept text embeddings.

    Args:
        activations:          Tensor (N_images, N_neurons) of pooled neuron activations.
        clip_text_embeddings: Tensor (N_concepts, D) of normalized CLIP text embeddings.
        clip_model:           Loaded CLIP model.
        dataloader:           DataLoader over probing images (same order as activations).
        device:               Torch device string.
        batch_size:           Batch size for CLIP image encoding.

    Returns:
        Tensor of shape (N_neurons, N_concepts) — cosine similarity scores.
    """
    clip_model.eval()

    # 1. Compute CLIP image embeddings for all probe images
    print("[INFO] Computing CLIP image embeddings for all probe images ...")
    image_embeddings_list = []

    with torch.no_grad():
        for batch_idx, (images, _) in enumerate(dataloader):
            images = images.to(device)
            img_feats = clip_model.encode_image(images)
            img_feats = F.normalize(img_feats, dim=-1)
            image_embeddings_list.append(img_feats.cpu())
            if batch_idx % 20 == 0:
                print(f"  ... processed batch {batch_idx + 1}/{len(dataloader)}")

    image_embeddings = torch.cat(image_embeddings_list, dim=0)  # (N_images, D)
    print(f"[INFO] Image embedding matrix shape: {image_embeddings.shape}")

    # 2. For each neuron, compute activation-weighted average of image embeddings
    # activations: (N_images, N_neurons), image_embeddings: (N_images, D)
    activations_norm = F.relu(activations)  # Only positive activations
    act_sum = activations_norm.sum(dim=0, keepdim=True) + 1e-8  # (1, N_neurons)
    activations_normalized = activations_norm / act_sum  # (N_images, N_neurons)

    # Weighted sum: (N_neurons, D)
    neuron_embeddings = activations_normalized.T @ image_embeddings  # (N_neurons, D)
    neuron_embeddings = F.normalize(neuron_embeddings, dim=-1)
    print(f"[INFO] Neuron embedding matrix shape: {neuron_embeddings.shape}")

    # 3. Cosine similarity between neuron embeddings and concept text embeddings
    # (N_neurons, D) x (D, N_concepts) = (N_neurons, N_concepts)
    similarity = neuron_embeddings @ clip_text_embeddings.T
    print(f"[INFO] Similarity matrix shape: {similarity.shape}")
    return similarity


def save_descriptions_csv(
    similarity: torch.Tensor,
    concepts: list[str],
    layer_name: str,
    save_path: str,
) -> None:
    """
    Save the top-1 neuron descriptions (best-matching concept) to a CSV file.

    For each neuron, the concept with the highest cosine similarity score is
    selected as the neuron's description.

    Args:
        similarity:  Tensor (N_neurons, N_concepts) of cosine similarity scores.
        concepts:    List of concept strings (length N_concepts).
        layer_name:  Name of the dissected layer (written to the CSV).
        save_path:   Full path where the CSV file will be written.

    Output CSV columns:
        - layer:       Layer name
        - unit:        Neuron index (0-based)
        - description: Best-matching concept string
        - similarity:  Cosine similarity score (float)
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    best_indices = similarity.argmax(dim=1)   # (N_neurons,)
    best_scores = similarity.max(dim=1).values  # (N_neurons,)

    print(f"[INFO] Saving descriptions to '{save_path}' ...")
    with open(save_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["layer", "unit", "description", "similarity"])
        for unit_idx in range(len(best_indices)):
            concept_idx = best_indices[unit_idx].item()
            score = best_scores[unit_idx].item()
            writer.writerow([
                layer_name,
                unit_idx,
                concepts[concept_idx],
                f"{score:.6f}",
            ])
    print(f"[INFO] Saved {len(best_indices)} neuron descriptions.")


def dissect_layer(
    target_model: torch.nn.Module,
    clip_model,
    layer_name: str,
    dataloader: DataLoader,
    concepts: list[str],
    clip_text_embeddings: torch.Tensor,
    device: str,
    save_path: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    pool_mode: str = "avg",
) -> None:
    """
    Full CLIP-Dissect pipeline for a single model layer.

    Steps:
        1. Compute pooled neuron activations for all probe images.
        2. Compute CLIP image embeddings and activation-weighted concept similarities.
        3. Save per-neuron descriptions to CSV.

    Args:
        target_model:         PyTorch model (eval mode).
        clip_model:           Loaded CLIP model.
        layer_name:           Name of the layer to dissect.
        dataloader:           DataLoader over probe images.
        concepts:             List of concept strings.
        clip_text_embeddings: Precomputed normalized CLIP text embeddings (N_concepts, D).
        device:               Torch device string.
        save_path:            Path for the output CSV file.
        batch_size:           Batch size (unused here, controlled by dataloader).
        pool_mode:            Spatial pooling mode ('avg' or 'max').
    """
    print(f"\n{'='*60}")
    print(f"  Dissecting layer: {layer_name}")
    print(f"{'='*60}")

    # Step 1: Neuron activations
    activations = compute_neuron_activations(
        model=target_model,
        layer_name=layer_name,
        dataloader=dataloader,
        device=device,
        pool_mode=pool_mode,
    )

    # Step 2: Compute similarity
    similarity = compute_neuron_clip_similarity(
        activations=activations,
        clip_text_embeddings=clip_text_embeddings,
        clip_model=clip_model,
        dataloader=dataloader,
        device=device,
    )

    # Step 3: Save descriptions
    save_descriptions_csv(
        similarity=similarity,
        concepts=concepts,
        layer_name=layer_name,
        save_path=save_path,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the CLIP-Dissect demo script."""
    parser = argparse.ArgumentParser(
        description="CLIP-Dissect: Describe neuron functionalities using CLIP."
    )
    parser.add_argument(
        "--target_model",
        type=str,
        default=DEFAULT_TARGET_MODEL,
        help="Name of the target model to dissect (default: resnet50).",
    )
    parser.add_argument(
        "--d_probe",
        type=str,
        default=DEFAULT_PROBE_DATASET,
        help="Probing dataset name: 'broden' or 'imagenet_val' (default: broden).",
    )
    parser.add_argument(
        "--concept_set",
        type=str,
        default=DEFAULT_CONCEPT_SET,
        help="Path to concept set .txt file (default: data/20k.txt).",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Batch size for dataloader (default: 64).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=DEFAULT_DEVICE,
        help="Torch device: 'cuda', 'cuda:0', 'cpu' (default: auto-detect).",
    )
    parser.add_argument(
        "--pool_mode",
        type=str,
        choices=["avg", "max"],
        default="avg",
        help="Spatial pooling mode for conv layer activations (default: avg).",
    )
    parser.add_argument(
        "--
```

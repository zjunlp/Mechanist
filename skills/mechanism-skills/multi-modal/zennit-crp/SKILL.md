---
name: zennit-crp
description: Use this skill when working with Concept Relevance Propagation (CRP) and Relevance Maximization for explainable AI in PyTorch models, including generating concept-conditional heatmaps, feature visualizations, attribution graphs, and identifying which latent concepts neural networks use for predictions.
---

# Zennit-CRP: Concept Relevance Propagation Skill

## When to Use

Activate this skill when:
- Generating **explainability heatmaps** for deep learning model predictions
- Computing **concept-conditional attributions** (CRP) to understand which latent features drive predictions
- Performing **Relevance Maximization (RelMax)** or **Activation Maximization (ActMax)** to find representative samples for neuron/channel concepts
- Building **attribution graphs** to trace relevance flows through network layers
- Analyzing **channel-level importance** in convolutional or linear layers
- Comparing what concepts a model uses vs. what activates a neuron (relevance vs. activation)
- Working with LRP (Layer-wise Relevance Propagation) via zennit composites
- Any task involving keywords: CRP, LRP, XAI, explainable AI, feature visualization, relevance propagation, concept attribution, channel relevance, RelMax, ActMax

## Quick Reference

- **Paper:** [Nature Machine Intelligence (Open Access)](https://www.nature.com/articles/s42256-023-00711-8)
- **PyPI:** https://pypi.org/project/zennit-crp/
- **GitHub:** https://github.com/rachtibat/zennit-crp
- **Tutorials:** https://github.com/rachtibat/zennit-crp/tree/master/tutorials
- **Zennit (dependency):** https://github.com/chr5tphr/zennit
- **Citation:** Achtibat et al., "From attribution maps to human-understandable explanations through Concept Relevance Propagation", Nature Machine Intelligence, 2023

## Installation / Setup

### Prerequisites
- Python 3.7+
- PyTorch (with CUDA support recommended for large datasets)
- A working model in PyTorch (`torch.nn.Module`)

### Install from PyPI (recommended, includes fast image utilities)
```shell
pip install zennit-crp[fast_img]
```

### Install from Source (to access tutorials)
```shell
git clone https://github.com/rachtibat/zennit-crp
pip install ./zennit-crp
```

### Install zennit separately if needed
```shell
pip install zennit
```

## Core Features

- **Conditional Attributions (CRP):** Generate concept-conditional relevance heatmaps by masking relevance flows during backpropagation, isolating the contribution of individual latent concepts to the model output.
- **ChannelConcept:** Define each channel in Conv2D/Linear layers as a distinct concept with built-in relative importance scoring.
- **Custom Concepts:** Extend the abstract `Concept` class to define your own notion of what constitutes a concept (beyond channels).
- **Relevance Maximization (RelMax):** Select dataset samples that maximize the relevance criterion for a given neuron/channel — a more faithful alternative to Activation Maximization (ActMax).
- **Activation Maximization (ActMax):** Classic approach: select samples that most strongly activate a given unit.
- **Feature Visualization:** The `FeatureVisualization` class precomputes and caches reference images (RelMax/ActMax) for all concepts across all layers on a full dataset.
- **Attribution Graph:** Trace relevance as a directed graph through model layers to understand information flow from output back to input.
- **Model Graph Analysis:** Automatically parse PyTorch JIT-traced model graphs to determine layer connectivity for attribution routing.
- **LRP Integration:** Built on top of **zennit** composites (e.g., `EpsilonPlusFlat`, `EpsilonAlpha2Beta1`) and canonizers (e.g., `SequentialMergeBatchNorm`).
- **Caching System:** `ImageCache` and abstract `Cache` classes for efficient storage and retrieval of reference images.
- **Image Utilities:** `plot_grid` and related helpers in `crp.image` for visualizing attribution results and reference image grids.
- **Statistics Module:** Tools in `crp.statistics` for aggregating concept relevance statistics across datasets.

## Usage Examples

### Conditional Attributions (CRP Quickstart)

```python
from crp.attribution import CondAttribution
from crp.concepts import ChannelConcept
from crp.helper import get_layer_names

from zennit.composites import EpsilonPlusFlat
from zennit.canonizers import SequentialMergeBatchNorm
import torch.nn as nn

# define LRP rules and canonizers in zennit
composite = EpsilonPlusFlat([SequentialMergeBatchNorm()])

# load CRP toolbox
attribution = CondAttribution(model)

# here, each channel is defined as a concept
# or define your own notion!
cc = ChannelConcept()

# get layer names of Conv2D and MLP layers
layer_names = get_layer_names(model, [nn.Conv2d, nn.Linear])

# get a conditional attribution for channel 50 in layer features.27 wrt. output 1
conditions = [{'features.27': [50], 'y': [1]}]

attr = attribution(data, conditions, composite, record_layer=layer_names)

# heatmap and prediction
attr.heatmap, attr.prediction
# activations and relevances for each layer name
attr.activations, attr.relevances

# relative importance of each concept for final prediction
rel_c = cc.attribute(attr.relevances['features.40'])
# most relevant channels in features.40
concept_ids = torch.argsort(rel_c, descending=True)
```

### Feature Visualization (RelMax / ActMax)

```python
from crp.visualization import FeatureVisualization
from crp.image import plot_grid

# define which concept is used in each layer
layer_map = {name: cc for name in layer_names}

# compute visualization (it takes for VGG16 and ImageNet testset on Titan RTX ~30 min)
fv = FeatureVisualization(attribution, dataset, layer_map)
fv.run(composite, 0, len(dataset))

# visualize MaxRelevance reference images for top-5 concepts
ref_c = fv.get_max_reference(concept_ids[:5], 'features.40', 'relevance', composite=composite)

plot_grid(ref_c)
```

## Key APIs / Models

### Classes
| Class | Module | Description |
|-------|--------|-------------|
| `CondAttribution` | `crp.attribution` | Main engine for conditional (CRP) and unconditional LRP attributions |
| `AttributionGraph` | `crp.attribution` | Traces attribution as a directed graph through network layers |
| `ChannelConcept` | `crp.concepts` | Defines each channel as a concept; computes per-channel relative relevance |
| `Concept` | `crp.concepts` | Abstract base class for custom concept definitions |
| `FeatureVisualization` | `crp.visualization` | Precomputes RelMax/ActMax reference images for all concepts/layers |
| `ModelGraph` | `crp.graph` | Parses PyTorch JIT graph to find layer connectivity |
| `GraphNode` | `crp.graph` | Metadata node in the model graph |
| `Cache` | `crp.cache` | Abstract base class for caching reference images |
| `ImageCache` | `crp.cache` | Concrete cache for PIL Image reference images |

### Key Functions
| Function | Module | Description |
|----------|--------|-------------|
| `get_layer_names(model, types)` | `crp.helper` | Returns names of layers matching given `nn.Module` types |
| `trace_model_graph(model, sample, layer_names)` | `crp.graph` | Builds `ModelGraph` by tracing the PyTorch JIT graph |
| `plot_grid(reference_images)` | `crp.image` | Visualizes a grid of reference images |

### Zennit Composites (used with CRP)
- `EpsilonPlusFlat` — LRP-ε for middle layers, LRP-0+ for early layers
- `EpsilonAlpha2Beta1` — LRP with alpha-beta rules
- `GuidedBackprop` — Guided backpropagation composite

### Zennit Canonizers
- `SequentialMergeBatchNorm` — Folds BatchNorm into preceding Conv/Linear layers

### Condition Dictionary Format
```python
# Condition on specific channels and output class
conditions = [{'layer_name': [channel_ids], 'y': [class_ids]}]

# Unconditional (standard LRP)
conditions = [{'y': [1]}]

# Multi-layer condition
conditions = [{'features.27': [50, 100], 'features.15': [32], 'y': [1]}]
```

## Common Patterns & Best Practices

### 1. Always merge BatchNorm before attribution
When your model uses BatchNorm layers, include `SequentialMergeBatchNorm()` in the canonizers list to ensure numerically stable LRP:
```python
composite = EpsilonPlusFlat([SequentialMergeBatchNorm()])
```

### 2. Record intermediate activations/relevances
Pass `record_layer=layer_names` to `attribution()` to capture activations and relevances at every layer for downstream analysis:
```python
attr = attribution(data, conditions, composite, record_layer=layer_names)
# Access per-layer data:
print(attr.relevances['features.27'].shape)
print(attr.activations['features.27'].shape)
```

### 3. Sort concepts by relevance for top-k analysis
```python
rel_c = cc.attribute(attr.relevances['features.40'])
top_k_concepts = torch.argsort(rel_c, descending=True)[:10]
```

### 4. Run FeatureVisualization once, query many times
`fv.run(...)` is expensive (precomputes over entire dataset). Run it once and save results. Then use `fv.get_max_reference(...)` for fast retrieval.

### 5. Use `'relevance'` mode over `'activation'` for faithful explanations
RelMax selects samples based on how useful a concept is for the model's classification task, making it more faithful than activation-based selection in adversarial scenarios.

### 6. Layer naming convention
Layer names follow PyTorch's `named_modules()` format (e.g., `'features.27'`, `'classifier.6'`). Use `get_layer_names(model, [nn.Conv2d, nn.Linear])` to enumerate valid names automatically.

### 7. Batched conditions
`CondAttribution` supports a list of condition dicts (one per sample in the batch), enabling efficient batched conditional attribution.
```python
conditions = [
    {'features.27': [50], 'y': [1]},
    {'features.27': [100], 'y': [3]},
]
attr = attribution(batch_data, conditions, composite, record_layer=layer_names)
```

## Reference-Image Cropping for Foundation-Model Embedding

`fv.get_max_reference(...)` returns whole input images. When the downstream goal is to **embed each reference image into a vision foundation model** (CLIP, SigLIP, DINOv2, ...) so that every neuron gets a concept vector in that model's semantic space, the full image is usually too noisy — the foundation model embeds the background, not the concept. The standard fix is to crop each reference image to the high-relevance region using the CRP heatmap itself. The recipe is identical across encoders; only the Gaussian blur kernel scales with input resolution.

### Standard pipeline

```python
import torch
from torchvision.transforms.functional import gaussian_blur
from crp.image import get_crop_range

def _square_box(r1, r2, c1, c2):
    """Symmetric expansion of a tight bbox into a square box (no inflate)."""
    dr, dc = r2 - r1, c2 - c1
    if dr > dc:
        pad = (dr - dc) // 2
        c1 -= pad; c2 += pad
        if c1 < 0:
            c2 -= c1; c1 = 0
    elif dc > dr:
        pad = (dc - dr) // 2
        r1 -= pad; r2 += pad
        if r1 < 0:
            r2 -= r1; r1 = 0
    return r1, r2, c1, c2

def crop_to_concept(image, heatmap, *, kernel_size, crop_th, square=True):
    """Blur the heatmap, threshold at `crop_th * max`, return the tight bbox.

    image:    (C, H, W) input tensor in the same resolution as the heatmap.
    heatmap:  (H, W)    per-pixel relevance from CondAttribution.
    """
    h = gaussian_blur(heatmap.unsqueeze(0), kernel_size=kernel_size)[0]
    h = h.abs() / (h.abs().max() + 1e-8)
    r1, r2, c1, c2 = get_crop_range(h, crop_th)
    if square:
        r1, r2, c1, c2 = _square_box(r1, r2, c1, c2)
    return image[..., r1:r2, c1:c2]
```

Pattern: **blur → abs → normalize-by-max → threshold → tight bbox → (optional) squarify**.

- *Blur* prevents 1-2 noisy hot pixels at the image border from anchoring the bbox.
- *abs + normalize* turns signed LRP relevance into a [0, 1] saliency.
- *Threshold at `crop_th × max`* keeps every pixel above a fraction of peak relevance — `crop_th` is the only knob controlling crop tightness.
- *Squarify* avoids non-square crops being resize-distorted by the downstream encoder; expansion is symmetric and stays inside the image, so there is no padding around the heatmap region.

### Presets

zennit-crp's `vis_opaque_img` and `vis_img_heatmap` ship with defaults tuned for **human heatmap inspection** — small kernel, strict thresholds, rectangular box. Embedding crops into a vision foundation model wants the opposite: bigger blur (smoother bbox boundary), 10× more permissive thresholds (more context for the encoder), forced square box (no resize distortion).

| Use case | encoder side `H` | `kernel_size` | `crop_th` | `vis_th` | `alpha` | `square` |
|---|---|---|---|---|---|---|
| Human heatmap inspection (zennit-crp default) | n/a | 19 | 0.10 | 0.20 | 0.3 | no |
| **CLIP / OpenCLIP / MobileCLIP / EVA-CLIP** | 224 | 51 | 0.01 | 0.02 | 0.4 | yes |
| **SigLIP / SigLIP-2** | 384 | 87 | 0.01 | 0.02 | 0.4 | yes |
| **DINOv2** (vision-only, high-res fine-tune) | 518 | 117 | 0.01 | 0.02 | 0.4 | yes |

Scaling rule for a non-standard encoder side `H`: `kernel ≈ 0.23 × H`, rounded to the nearest odd integer (`torchvision.transforms.functional.gaussian_blur` requires odd kernels). For DINOv2-base at 224 or SigLIP-base at 256, plug `H` into the same rule rather than reading the table literally.

The three sub-1 thresholds are encoder-invariant: 1 % of max relevance keeps essentially all of the concept's mass while excluding background, which is a property of natural-image LRP/CRP heatmaps, not of any specific encoder. The same `crop_th` / `vis_th` / `alpha` values transfer across CLIP, SigLIP, DINOv2, and any other natural-image foundation model.

### Picking a preset

- **Building a UMAP / cluster view for a person to look at** → human-inspection defaults. Tight crops are fine because the human eye fills in context, and you usually want to *see* exactly where on the image the network looks.
- **CLIP / OpenCLIP / MobileCLIP / EVA-CLIP for image-text concept labelling** → 224 preset. Default choice when each neuron should be labelled with a text concept via cosine similarity in CLIP space.
- **SigLIP / SigLIP-2 for higher-resolution image-text embedding** → 384 preset. Use when CLIP-224 patches lose too much detail — fine-grained categories, small objects, dense scenes, medical or satellite imagery.
- **DINOv2 (or any vision-only foundation model) for clustering / similarity** → high-res preset. Use when you want a semantic embedding without the text-alignment bias that CLIP-family models inherit from contrastive pre-training (e.g., comparing what two networks *visually* group together, independent of how that grouping maps to language).

### Why the embedding thresholds are 10× more permissive than human-inspection defaults

`vis_opaque_img`'s `crop_th=0.1` keeps only pixels above 10 % of max relevance — typically just the brightest concept core. A person looking at the heatmap fills in surrounding context from memory. A foundation encoder cannot: cropped that tightly, CLIP / SigLIP / DINOv2 see a meaningless texture patch and embed noise. Dropping `crop_th` to `0.01` recovers everything at ≥1 % of max relevance, making the crop large enough for the encoder to actually recognize what concept is there.

### CRP heatmap source

For CNN channels, `CondAttribution` returns an input-space heatmap directly. For **Vision Transformers**, CRP through self-attention is not implemented in zennit-crp at the time of writing; substitute the heatmap with the upsampled spatial-token activation map (bilinear-interpolated to image resolution) and feed it through `crop_to_concept` as-is. Treat ViT crops as a fallback — they are an activation-map proxy, not true relevance.

## Demo Scripts

### `scripts/conditional_attribution_demo.py`

```python
#!/usr/bin/env python3
"""
Conditional Attribution Demo using zennit-crp (Concept Relevance Propagation)

This script demonstrates how to:
  1. Set up a PyTorch model with zennit LRP composites
  2. Compute concept-conditional relevance heatmaps using CRP
  3. Identify the most relevant channels/concepts in a given layer
  4. Record per-layer activations and relevances

Requires:
    pip install zennit-crp[fast_img] torch torchvision

Usage:
    python conditional_attribution_demo.py
"""

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy as np

# CRP imports
from crp.attribution import CondAttribution
from crp.concepts import ChannelConcept
from crp.helper import get_layer_names

# Zennit LRP composites and canonizers
from zennit.composites import EpsilonPlusFlat
from zennit.canonizers import SequentialMergeBatchNorm


# ---------------------------------------------------------------------------
# Model Setup
# ---------------------------------------------------------------------------

def load_model() -> nn.Module:
    """
    Load a pretrained VGG16 model from torchvision.

    Returns:
        model (nn.Module): A pretrained VGG16 in eval mode.
    """
    model = models.vgg16(pretrained=True)
    model.eval()
    return model


def create_dummy_input(batch_size: int = 2) -> torch.Tensor:
    """
    Create a random image batch as a stand-in for real data.
    Replace this with actual image loading for real use.

    Args:
        batch_size: Number of images in the batch.

    Returns:
        Tensor of shape (batch_size, 3, 224, 224) with requires_grad=True.
    """
    # In real usage, load actual images and apply standard ImageNet preprocessing:
    # transform = transforms.Compose([
    #     transforms.Resize(256),
    #     transforms.CenterCrop(224),
    #     transforms.ToTensor(),
    #     transforms.Normalize(mean=[0.485, 0.456, 0.406],
    #                          std=[0.229, 0.224, 0.225]),
    # ])
    # img = Image.open("path/to/image.jpg").convert("RGB")
    # data = transform(img).unsqueeze(0)

    data = torch.randn(batch_size, 3, 224, 224, requires_grad=True)
    return data


# ---------------------------------------------------------------------------
# LRP Setup
# ---------------------------------------------------------------------------

def build_composite() -> EpsilonPlusFlat:
    """
    Build a zennit EpsilonPlusFlat composite with BatchNorm canonizer.
    EpsilonPlusFlat uses:
        - LRP-epsilon for middle layers (numerically stable)
        - LRP-0+ (flat) for the input/first layers (avoids gradient shattering)

    Returns:
        composite (EpsilonPlusFlat): Ready-to-use LRP composite.
    """
    canonizers = [SequentialMergeBatchNorm()]
    composite = EpsilonPlusFlat(canonizers)
    return composite


# ---------------------------------------------------------------------------
# CRP Attribution
# ---------------------------------------------------------------------------

def run_conditional_attribution(
    model: nn.Module,
    data: torch.Tensor,
    target_layer: str = "features.28",
    concept_ids: list = None,
    output_class: int = 1,
) -> dict:
    """
    Run Concept Relevance Propagation (CRP) for specified concept IDs
    in a given layer, conditioned on a target output class.

    Args:
        model:        The PyTorch model (eval mode).
        data:         Input tensor, shape (B, C, H, W), requires_grad=True.
        target_layer: Name of the layer to condition on (e.g., 'features.28').
        concept_ids:  List of channel indices to condition on. Defaults to [50].
        output_class: The output class index to attribute from.

    Returns:
        Dictionary containing:
            'heatmap'     - Input-space relevance heatmap tensor
            'prediction'  - Model output logits
            'relevances'  - Dict[layer_name -> relevance tensor]
            'activations' - Dict[layer_name -> activation tensor]
            'rel_c'       - Per-channel relative relevance in target_layer
            'top_concepts'- Sorted channel indices by descending relevance
    """
    if concept_ids is None:
        concept_ids = [50]

    # --- Build composite and concept object ---
    composite = build_composite()
    cc = ChannelConcept()

    # --- Discover layer names for Conv2d and Linear layers ---
    layer_names = get_layer_names(model, [nn.Conv2d, nn.Linear])
    print(f"[INFO] Found {len(layer_names)} Conv2d/Linear layers.")
    print(f"[INFO] First 5 layer names: {layer_names[:5]}")

    # --- Initialize CondAttribution ---
    attribution = CondAttribution(model)

    # --- Define conditions ---
    # Each entry in the list corresponds to one sample in the batch.
    # 'y' specifies the output neuron to propagate from.
    # The target_layer key specifies which channel(s) to condition on.
    conditions = [
        {target_layer: concept_ids, "y": [output_class]}
        for _ in range(data.shape[0])
    ]
    print(f"[INFO] Running CRP with conditions: {conditions[0]}")

    # --- Run attribution ---
    # record_layer captures activations AND relevances at each named layer
    attr = attribution(
        data,
        conditions,
        composite,
        record_layer=layer_names,
    )

    # --- Extract results ---
    heatmap = attr.heatmap       # shape: (B, H, W) - input-space relevance
    prediction = attr.prediction  # shape: (B, num_classes) - raw logits

    print(f"[INFO] Heatmap shape:    {heatmap.shape}")
    print(f"[INFO] Prediction shape: {prediction.shape}")

    # --- Compute per-channel relative relevance in the last feature layer ---
    last_layer = layer_names[-1]
    if last_layer in attr.relevances:
        rel_c = cc.attribute(attr.relevances[last_layer])
        top_concepts = torch.argsort(rel_c, descending=True)
        print(f"[INFO] Top-5 concept IDs in '{last_layer}': {top_concepts[:5].tolist()}")
    else:
        rel_c = None
        top_concepts = None
        print(f"[WARN] Layer '{last_layer}' not found in recorded relevances.")

    return {
        "heatmap": heatmap,
        "prediction": prediction,
        "relevances": attr.relevances,
        "activations": attr.activations,
        "rel_c": rel_c,
        "top_concepts": top_concepts,
        "layer_names": layer_names,
    }


# ---------------------------------------------------------------------------
# Unconditional Attribution (standard LRP)
# ---------------------------------------------------------------------------

def run_unconditional_attribution(
    model: nn.Module,
    data: torch.Tensor,
    output_class: int = 1,
) -> object:
    """
    Run standard (unconditional) LRP attribution without concept masking.

    Args:
        model:        The PyTorch model.
        data:         Input tensor.
        output_class: Output class to propagate from.

    Returns:
        Attribution result object with .heatmap and .prediction.
    """
    composite = build_composite()
    attribution = CondAttribution(model)
    layer_names = get_layer_names(model, [nn.Conv2d, nn.Linear])

    # No layer conditions — only specify output class
    conditions = [{"y": [output_class]} for _ in range(data.shape[0])]

    attr = attribution(data, conditions, composite, record_layer=layer_names)
    print(f"[INFO] Unconditional heatmap shape: {attr.heatmap.shape}")
    return attr


# ---------------------------------------------------------------------------
# Channel Concept: Relative Importance
# ---------------------------------------------------------------------------

def analyze_concept_importance(
    relevances_dict: dict,
    layer_name: str,
) -> torch.Tensor:
    """
    Compute the relative importance of each channel (concept) in a layer.

    Args:
        relevances_dict: Dict mapping layer_name -> relevance tensor from attr.relevances.
        layer_name:      The layer to analyze.

    Returns:
        rel_c (Tensor): Per-channel relative relevance scores, shape (num_channels,).
    """
    cc = ChannelConcept()

    if layer_name not in relevances_dict:
        available = list(relevances_dict.keys())
        raise KeyError(
            f"Layer '{layer_name}' not in recorded relevances. "
            f"Available layers (first 5): {available[:5]}"
        )

    layer_relevance = relevances_dict[layer_name]
    print(f"[INFO] Layer '{layer_name}' relevance tensor shape: {layer_relevance.shape}")

    # cc.attribute collapses spatial dims and normalizes across channels
    rel_c = cc.attribute(layer_relevance)
    print(f"[INFO] rel_c shape: {rel_c.shape}")
    print(f"[INFO] Top-5 concept indices: {torch.argsort(rel_c, descending=True)[:5].tolist()}")
    print(f"[INFO] Top-5 concept relevances: {torch.sort(rel_c, descending=True).values[:5].tolist()}")

    return rel_c


# ---------------------------------------------------------------------------
# Main Demo
# ---------------------------------------------------------------------------

def main():
    """
    Main demonstration of CRP conditional attribution workflow.
    """
    print("=" * 60)
    print("  Zennit-CRP: Conditional Attribution Demo")
    print("=" * 60)

    # 1. Load model
    print("\n[STEP 1] Loading VGG16 model...")
    model = load_model()

    # 2. Create dummy input
    print("\n[STEP 2] Creating dummy input batch (2 images, 224x224)...")
    print("         Replace with real image data for actual use.")
    data = create_dummy_input(batch_size=2)

    # 3. Inspect available layer names
    print("\n[STEP 3] Discovering layer names...")
    layer_names = get_layer_names(model, [nn.Conv2d, nn.Linear])
    print(f"         Total layers: {len(layer_names)}")
    print(f"         All layers: {layer_names}")

    # Pick a target layer for conditioning (second-to-last conv layer in VGG16)
    target_layer = "features.28"  # Conv2d in VGG16 block 5
    print(f"\n         Target layer for CRP conditioning: '{target_layer}'")

    # 4. Run conditional attribution
    print("\n[STEP 4] Running conditional CRP attribution...")
    results = run_conditional_attribution(
        model=model,
        data=data,
        target_layer=target_layer,
        concept_ids=[50, 100],  # condition on channels 50 and 100
        output_class=1,
    )

    # 5. Analyze concept importance in another layer
    print("\n[STEP 5] Analyzing per-channel importance in 'features.26'...")
    try:
        rel_c = analyze_concept_importance(results["relevances"], "features.26")
        top5_ids = torch.argsort(rel_c, descending=True)[:5].tolist()
        print(f"         Most relevant concept IDs: {top5_ids}")
    except KeyError as e:
        print(f"         [WARN] {e}")

    # 6. Run unconditional LRP for comparison
    print("\n[STEP 6] Running unconditional LRP (no concept masking)...")
    attr_unconditional = run_unconditional_attribution(model, data, output_class=1)

    # 7. Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Heatmap shape:       {results['heatmap'].shape}")
    print(f"  Prediction shape:    {results['prediction'].shape}")
    print(f"  Layers recorded:     {len(results['relevances'])}")
    if results["top_concepts"] is not None:
        print(f"  Top concept IDs:     {results['top_concepts'][:5].tolist()}")
    print(f"  Unconditional hmap:  {attr_unconditional.heatmap.shape}")
    print("\n[DONE] Demo complete.")
    print("       Next step: see feature_visualization_demo.py for RelMax/ActMax.")


if __name__ == "__main__":
    main()
```

### `scripts/feature_visualization_demo.py`

```python
#!/usr/bin/env python3
"""
Feature Visualization Demo using zennit-crp (RelMax / ActMax)

This script demonstrates how to:
  1. Build a FeatureVisualization object over a dataset
  2. Run precomputation of RelMax and ActMax reference images
  3. Query top-k reference images for specific concept IDs
  4. Visualize concept reference images with plot_grid

Requires:
    pip install zennit-crp[fast_img] torch torchvision

Usage:
    python feature_visualization_demo.py

Note:
    Full precomputation on ImageNet + VGG16 takes ~30 min on a GPU (Titan RTX).
    This demo uses a tiny synthetic dataset for illustration.
    Replace `SyntheticDataset` with your real `torch.utils.data.Dataset`.
"""

import torch
import torch.nn as nn
import torchvision.models as models
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path

# CRP imports
from crp.attribution import CondAttribution
from crp.concepts import ChannelConcept
from crp.helper import get_layer_names
from crp.visualization import FeatureVisualization
from crp.image import plot_grid

# Zennit imports
from zennit.composites import EpsilonPlusFlat
from zennit.canonizers import SequentialMergeBatchNorm


# ---------------------------------------------------------------------------
# Synthetic Dataset (replace with your real dataset)
# ---------------------------------------------------------------------------

class SyntheticDataset(Dataset):
    """
    A minimal synthetic dataset for demonstration purposes.

    Replace this with your actual dataset, e.g.:
        from torchvision.datasets import ImageNet
        dataset = ImageNet(root='/path/to/imagenet', split='val',
                           transform=transform)

    The dataset must return (image_tensor, label) tuples,
    where image_tensor has shape (C, H, W).
    """

    def __init__(self, num_samples: int = 50, num_classes: int = 10):
        """
        Args:
            num_samples: Total number of synthetic images.
            num_classes: Number of output classes.
        """
        self.num_samples = num_samples
        self.num_classes = num_classes
        # Simulate ImageNet-like 224x224 RGB images
        self.data = torch.randn(num_samples, 3, 224, 224)
        self.labels = torch.randint(0, num_classes, (num_samples,))

    def __len__(self) -> int:
        return self.num_samples

    def __getitem__(self, idx: int):
        return self.data[idx], self.labels[idx]


# ---------------------------------------------------------------------------
# Model and Composite Setup
# ---------------------------------------------------------------------------

def load_model_and_composite():
    """
    Load VGG16 and build the LRP composite.

    Returns:
        model (nn.Module): VGG16 in eval mode.
        composite (EpsilonPlusFlat): LRP composite with BN canonizer.
    """
    model = models.vgg16(pretrained=True)
    model.eval()
    composite = EpsilonPlusFlat([SequentialMergeBatchNorm()])
    return model, composite


# ---------------------------------------------------------------------------
# Feature Visualization
# ---------------------------------------------------------------------------

def build_feature_visualization(
    model: nn.Module,
    dataset: Dataset,
    layer_names: list,
    save_path: str = "./fv_cache",
) -> FeatureVisualization:
    """
    Construct a FeatureVisualization object for the given model and dataset.

    Args:
        model:       The PyTorch model in eval mode.
        dataset:     A torch Dataset returning (image, label) tuples.
        layer_names: List of layer name strings to compute visualizations for.
        save_path:   Directory path where precomputed results are cached to disk.

    Returns:
        fv (FeatureVisualization): Configured feature visualization object.
    """
    attribution = CondAttribution(model)
    cc = ChannelConcept()

    # Map each layer to the ChannelConcept (one concept per channel)
    layer_map = {name: cc for name in layer_names}

    fv = FeatureVisualization(
        attribution=attribution,
        dataset=dataset,
        layer_map=layer_map,
        path=save_path,  # Cache directory — will be created if it doesn't exist
    )
    return fv


def run_precomputation(
    fv: FeatureVisualization,
    composite,
    start: int = 0,
    stop: int = None,
    batch_size: int = 8,
) -> None:
    """
    Run the precomputation of RelMax and ActMax reference statistics
    over [start, stop) samples of the dataset.

    This step is expensive for large datasets (e.g., ~30 min for ImageNet + VGG16
    on a Titan RTX GPU). Results are cached to disk for fast retrieval later.

    Args:
        fv:         FeatureVisualization object.
        composite:  zennit LRP composite to use during backward pass.
        start:      Dataset start index.
        stop:       Dataset stop index (exclusive). None = len(dataset).
        batch_size: Number of samples per batch during precomputation.
    """
    if stop is None:
        stop = len(fv.dataset)

    print(f"[INFO] Starting precomputation for samples [{start}, {stop})...")
    print(f"[INFO] Batch size: {batch_size}")
    print(f"       This may take a while for large datasets.")

    fv.run(composite, start, stop, batch_size=batch_size)
    print("[INFO] Precomputation complete. Results cached to disk.")


def retrieve_max_references(
    fv: FeatureVisualization,
    concept_ids: list,
    layer_name: str,
    composite,
    mode: str = "relevance",
    top_n: int = 6,
) -> dict:
    """
    Retrieve reference images (RelMax or ActMax) for a set of concept IDs.

    Args:
        fv:          FeatureVisualization object (after fv.run() has been called).
        concept_ids: List of channel/concept indices to visualize.
        layer_name:  The layer name where these concepts reside.
        composite:   zennit composite (used to compute relevance maps for refs).
        mode:        'relevance' for RelMax, 'activation' for ActMax.
        top_n:       Number of top reference images per concept to retrieve.

    Returns:
        ref_c (dict): Dictionary mapping concept_id -> list of reference images/arrays.
    """
    print(f"[INFO] Retrieving '{mode}' references for concepts {concept_ids}")
    print(f"       Layer: '{layer_name}', top-{top_n} samples per concept.")

    ref_c = fv.get_max_reference(
        concept_ids=concept_ids,
        layer_name=layer_name,
        mode=mode,            # 'relevance' = RelMax, 'activation' = ActMax
        composite=composite,
        r_range=(0, top_n),   # indices of top references to retrieve
    )

    return ref_c


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def visualize_references(ref_c: dict, title: str = "Concept References") -> None:
    """
    Display a grid of concept reference images using crp.image.plot_grid.

    Args:
        ref_c:  Reference image dict from fv.get_max_reference().
        title:  Optional title for the plot.
    """
    print(f"[INFO] Plotting reference grid: '{title}'")
    try:
        fig = plot_grid(ref_c)
        # Save to file instead of displaying (useful in headless environments)
        output_path = f"./{title.replace(' ', '_')}.png"
        fig.savef
```

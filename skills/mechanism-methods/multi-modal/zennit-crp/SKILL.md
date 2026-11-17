---
name: zennit-crp
description: "Use this skill when working with Concept Relevance Propagation (CRP) and Relevance Maximization for explainable AI in PyTorch models, including generating concept-conditional heatmaps, feature visualizations, attribution graphs, and identifying which latent concepts neural networks use for predictions."
---

## Method and use

Use concept-conditional relevance maps, reference images, and attribution graphs to inspect visual computations. Choose suitable composites and canonizers for the architecture. Conditional attribution and activating examples can support explanation and crop selection without independently proving causal necessity.


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


See [`scripts/conditional_attribution_demo.py`](scripts/conditional_attribution_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/feature_visualization_demo.py`


See [`scripts/feature_visualization_demo.py`](scripts/feature_visualization_demo.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

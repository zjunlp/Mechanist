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

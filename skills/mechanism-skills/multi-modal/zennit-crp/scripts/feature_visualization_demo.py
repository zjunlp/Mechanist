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
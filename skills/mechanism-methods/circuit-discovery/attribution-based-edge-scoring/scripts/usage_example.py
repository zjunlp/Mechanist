#!/usr/bin/env python3
"""
Demonstration script for EAP-IG library usage.

This script constructs a computational graph for a TransformerLens GPT-2 model,
runs Edge Attribution Patching with Integrated Gradients (EAP-IG-inputs) to score
nodes or edges, selects a top-n circuit, and evaluates its impact on a simple task.

You must install this library and TransformerLens prior to running:
pip install . transformer_lens

Replace the model loading step with your preferred TransformerLens autoregressive model.
"""

import torch
from torch.utils.data import DataLoader
from transformer_lens import HookedTransformer

from eap.graph import Graph
from eap.attribute import attribute
from eap.evaluate import evaluate_graph
from eap.utils import EAPDataset


def accuracy_metric(preds: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """
    Simple accuracy metric.

    Args:
        preds: Model logits tensor of shape (batch, seq_len, vocab_size)
        labels: Ground truth labels tensor of shape (batch, seq_len)

    Returns:
        Tensor with scalar accuracy (fraction correct)
    """
    pred_tokens = preds.argmax(dim=-1)
    correct = (pred_tokens == labels).float()
    return correct.mean()


def main():
    # Load a pretrained GPT-2 small model from TransformerLens
    # This requires the transformer_lens package: pip install transformer_lens
    model_name = "gpt2-small"
    print(f"Loading TransformerLens model '{model_name}' ...")
    model = HookedTransformer.from_pretrained(model_name)

    # Prepare an example dataset for the "greater-than" synthetic task provided by EAPDataset
    dataset = EAPDataset("greater-than")
    dataloader = dataset.to_dataloader(batch_size=16, shuffle=True)

    # Build computational graph from the model
    print("Building computational graph from model ...")
    graph = Graph.from_model(model)

    # Compute attribution scores with EAP-IG on inputs mode (5 integrated gradient steps)
    print("Computing attribution scores with EAP-IG (inputs) ...")
    attribute(
        model=model,
        graph=graph,
        dataloader=dataloader,
        metric=accuracy_metric,
        method="EAP-IG-inputs",
        ig_steps=5,
        intervention="none",
    )

    # Select top 10 nodes/edges to define the circuit
    top_n = 10
    print(f"Selecting top {top_n} scoring components as circuit ...")
    graph.apply_topn(top_n)

    # Evaluate circuit by ablating outside nodes/edges and measuring accuracy
    print("Evaluating circuit faithfulness on dataset ...")
    results = evaluate_graph(
        model=model,
        graph=graph,
        dataloader=dataloader,
        metric=accuracy_metric,
        intervention="none",
    )
    print("Circuit evaluation results:", results)


if __name__ == "__main__":
    main()

# EAP-IG Python Library API Reference

This reference documents the main classes and functions from the `eap-ig` library
(residing primarily under the `eap` namespace). The library enables circuit discovery
and analysis in autoregressive transformer language models using attribution methods.

---

## Module: eap.graph

### Class: Node
Represents a node in the computational graph corresponding to a model component.

**Attributes:**

- `in_hook`: Hook into the model inputs of this node
- `out_hook`: Hook into the model outputs of this node
- `layer`: The model layer number (int)
- `type`: Type of node, e.g. 'mlp', 'attn', 'logit'
- `scores`: Attribution scores stored per analysis

---

### Class: LogitNode(Node)
Represents the logits output node of a transformer model.

---

### Class: MLPNode(Node)
Represents an MLP block node in the computational graph.

---

### Class: Graph
Represents the entire computational graph of the model with nodes and edges.

**Class method:**

```python
Graph.from_model(model: HookedTransformer) -> Graph
```
Constructs a computation graph from a HookedTransformer autoregressive model.

**Methods:**

```python
Graph.apply_topn(n: int) -> None
```
Select the top-n scoring nodes/edges as the circuit members.

---

## Module: eap.attribute

### Function:

```python
attribute(
    model: HookedTransformer,
    graph: Graph,
    dataloader: DataLoader,
    metric: callable,
    method: str = 'EAP-IG-inputs',
    ig_steps: int = 5,
    intervention: str = 'none',
    intervention_dataloader: DataLoader = None
) -> None
```

Computes attribution scores on graph components representing their indirect effect on the
model metric by applying variants of Edge Attribution Patching and Integrated Gradients.

**Parameters:**

- `model` (HookedTransformer): The autoregressive transformer model.
- `graph` (Graph): The computational graph object built from the model.
- `dataloader` (DataLoader): DataLoader returning (input, corrupted_input, labels) batches.
- `metric` (callable): Function that evaluates model outputs and returns a scalar performance metric.
- `method` (str): Attribution method to use. Options:
  - `'exact'`
  - `'EAP'`
  - `'EAP-IG-inputs'`
  - `'EAP-IG-activations'`
  - `'clean-corrupted'`
- `ig_steps` (int): Number of integrated gradient steps for IG-based methods.
- `intervention` (str): Type of ablation; one of `'none'`, `'zero'`, `'mean'`, `'mean-positional'`.
- `intervention_dataloader` (DataLoader): Optional dataloader for intervention averaging.

---

## Module: eap.attribute_node

This module implements node- and neuron-wise attributions similarly to `eap.attribute`

**Key functions:**

```python
make_hooks_and_matrices(
    model: HookedTransformer,
    graph: Graph,
    batch_size: int
) -> object
```
Prepares hooks and matrices to record activations for node/neuron level analysis.

```python
get_scores_exact(
    model: HookedTransformer,
    graph: Graph,
    dataloader: DataLoader
) -> None
```
Exact computation of indirect effects per node/neuron.

```python
get_scores_eap(
    model: HookedTransformer,
    graph: Graph,
    dataloader: DataLoader
) -> None
```
Compute indirect effects per node/neuron using EAP approximation.

---

## Module: eap.evaluate

### Functions:

```python
evaluate_graph(
    model: HookedTransformer,
    graph: Graph,
    dataloader: DataLoader,
    metric: callable,
    intervention: str = 'none'
) -> dict
```
Evaluate the performance of the circuit by corrupting/ablating graph components not in the circuit and measuring model metric.

Parameters:

- `model`: The autoregressive transformer model.
- `graph`: Circuit graph with nodes/edges selected.
- `dataloader`: DataLoader returning evaluation batches.
- `metric`: Performance metric function.
- `intervention`: Ablation type ('none', 'zero', 'mean', 'mean-positional').

Returns:

- Dictionary with evaluation results including metric values and drop from baseline.

```python
evaluate_baseline(
    model: HookedTransformer,
    dataloader: DataLoader,
    metrics: list[callable]
) -> list[float]
```
Compute baseline performance metrics on clean inputs.

---

## Module: eap.utils

### Class: EAPDataset

Helper dataset class providing pre-built tasks and datasets, e.g., 'greater-than'.

**Constructor:**

```python
EAPDataset(task_name: str)
```

**Methods:**

```python
to_dataloader(
    batch_size: int = 32,
    shuffle: bool = True
) -> DataLoader
```
Returns a PyTorch DataLoader for the specified dataset.

---

## Module: eap.visualization

Functions and classes to help render graphs and circuits visually with colors and layout hints.

---

# Notes

- All functions expecting `model` require a TransformerLens `HookedTransformer`.
- Attribution methods can be computationally expensive depending on `ig_steps` and model size.
- Respects TransformerLens residual stream assumptions (pre-layernorm only).

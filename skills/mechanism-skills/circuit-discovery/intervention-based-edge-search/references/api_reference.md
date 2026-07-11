# Automatic Circuit DisCovery (ACDC) API Reference

---

## Module Hierarchy

- `acdc`
  - `TLACDCCorrespondence.py`
  - `TLACDCEdge.py`
  - `TLACDCExperiment.py`
  - `TLACDCInterpNode.py`
  - `acdc_utils.py`
  - other submodules (greaterthan, induction, ioi, logic_gates, tracr_task)
- `experiments`
- `subnetwork_probing`

---

## Class: TLACDCCorrespondence
*Source:* `acdc/TLACDCCorrespondence.py`

Represents the computational graph correspondence for transformer circuits.

**Example signature overview:**

```python
class TLACDCCorrespondence:
    def __init__(self, ...):
        """
        Initialize the correspondence object,
        storing nodes and edges for a computational graph representation.
        """
        pass

    def add_node(self, node: 'TLACDCInterpNode') -> None:
        """Add a node to the correspondence graph."""

    def add_edge(self, edge: 'Edge') -> None:
        """Add an edge to the correspondence graph."""

    def get_subgraph(self, criteria: dict) -> 'TLACDCCorrespondence':
        """Return a subgraph matching selection criteria."""

    def visualize(self, filename: str = None) -> None:
        """
        Visualize the graph using Graphviz.
        If filename is passed, save to file.
        """
```

---

## Class: EdgeType
*Source:* `acdc/TLACDCEdge.py`

An enumeration or class representing the different types/properties edges can have in the computational graph.

**Typical attributes:**

```python
class EdgeType:
    # e.g. possible edge categories like attention, MLP etc.
    ATTENTION = ...
    MLP = ...
    RESIDUAL = ...
```

---

## Class: Edge
*Source:* `acdc/TLACDCEdge.py`

Represents an edge between computational nodes.

**Constructor:**

```python
class Edge:
    def __init__(self,
                 parent_node: 'TLACDCInterpNode',
                 child_node: 'TLACDCInterpNode',
                 edge_type: EdgeType,
                 weight: float = 1.0):
        """
        Initialize an Edge connecting two nodes, with optional weight.
        """
```

**Attributes:**

- `parent_node`: `TLACDCInterpNode` - source node of the edge.
- `child_node`: `TLACDCInterpNode` - destination node of the edge.
- `edge_type`: `EdgeType` - category of the edge.
- `weight`: `float` - edge weight or importance score.

---

## Class: TorchIndex
*Source:* `acdc/TLACCEdge.py`

Represents indices within PyTorch tensors relevant for mapping nodes/edges.

**Purpose:** Maps between computational graph node indices and PyTorch tensor indices.

---

## Class: TLACDCExperiment
*Source:* `acdc/TLACDCExperiment.py`

Manages the lifecycle of an ACDC experiment, including model loading, data handling, graph construction, and interpretation.

**Key methods:**

```python
class TLACDCExperiment:
    def __init__(self, config: dict):
        """
        Initialize experiment with config specifying model, dataset, parameters.
        """

    def run(self, run_name: str = None) -> None:
        """
        Run the full experiment, including training/interpreting circuits.
        Logs results to wandb or locally.
        """

    def load_model(self, model_name: str) -> None:
        """Load the transformer model to analyze."""

    def build_graph(self) -> None:
        """Construct the computational graph from model hooks."""

    def save_results(self, output_dir: str) -> None:
        """Save experiment output and graphs."""

    def load_results(self, path: str) -> None:
        """Load saved experiment results from disk."""
```

---

## Class: TLACDCInterpNode
*Source:* `acdc/TLACDCInterpNode.py`

Represents a single computational node in the ACDC graph (e.g., an attention head output or MLP hidden feature).

**Functions:**

```python
class TLACDCInterpNode:
    def __init__(self, layer: int, node_type: str, index: int):
        """Initialize node with layer, type, and index."""

    def __str__(self) -> str:
        """String representation of node."""

def parse_interpnode(s: str) -> TLACDCInterpNode:
    """
    Parse string to a TLACDCInterpNode instance.
    """

def heads_to_nodes_to_mask(heads: list[tuple[int,int]],
                           return_dict: bool = True) -> dict:
    """
    Convert a list of attention heads to a mask over nodes.
    """
```

---

## Function: check_transformer_lens_version()
*Source:* `acdc/__init__.py`

Checks if the installed TransformerLens library version meets requirements.

---

## CLI Entrypoints (Scripts)

### `acdc/main.py`

Main entry point to run ACDC pipeline.

```bash
python acdc/main.py [options]
```

Common options enable different experiments or specify config files.

---

### Experiment Launching Scripts

- `experiments/launch_induction.py`  
  Launches induction experiments reproducing Pareto frontier results.

- `experiments/launch_sixteen_heads.py`  
  Launches experiments involving sixteen attention heads.

- `subnetwork_probing/train.py`  
  Training script for subnetwork probing experiments.

---

## Usage Notes

- Most APIs are designed for internal usage with experimentation workflows.
- Computational graph classes can be manipulated for custom circuit discovery.
- Outputs support integration with Weights & Biases (`wandb`) for logging and visualization.
- Use notebook demos or scripts to get started with graph editing and visualization.

---

# End of API Reference
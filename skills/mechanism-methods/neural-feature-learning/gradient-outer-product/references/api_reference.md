# Recursive Feature Machines (RFM) API Reference

## Module: `rfm`

Install via:
```bash
pip install git+https://github.com/aradha/recursive_feature_machines.git@pip_install
```

---

## Class: `LaplaceRFM`

A Recursive Feature Machine using the Laplace (exponential) kernel. Iteratively learns a feature matrix `M` that adapts the kernel metric to the data, enabling backpropagation-free feature learning analogous to neural networks.

**Reference:** [Science 2024 - Mechanism for feature learning in neural networks and backpropagation-free machine learning models](https://www.science.org/doi/10.1126/science.adi5639)

---

### Constructor

```python
LaplaceRFM(
    bandwidth: float,
    device: torch.device,
    mem_gb: int,
    diag: bool = False
)
```

**Parameters:**

| Parameter   | Type           | Description |
|-------------|----------------|-------------|
| `bandwidth` | `float`        | Bandwidth parameter for the Laplace kernel. Controls the length scale of the kernel. Typical value: `1.0`. |
| `device`    | `torch.device` | Compute device. Use `torch.device("cuda")` for GPU or `torch.device("cpu")` for CPU. |
| `mem_gb`    | `int`          | Available memory in gigabytes. Used to manage kernel matrix computation in chunks. For GPU, set to `total_GPU_memory_GB - 1`. |
| `diag`      | `bool`         | If `True`, uses a diagonal approximation of the feature matrix `M` for memory-efficient computation on large datasets. Default: `False`. |

**Example:**
```python
import torch
from rfm import LaplaceRFM

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
mem_gb = 7  # e.g., 8GB GPU with 1GB reserved

model = LaplaceRFM(bandwidth=1.0, device=device, mem_gb=mem_gb, diag=False)
```

---

### Method: `fit`

```python
model.fit(
    train_data: tuple[torch.Tensor, torch.Tensor],
    test_data: tuple[torch.Tensor, torch.Tensor],
    iters: int,
    classification: bool
) -> None
```

Trains the RFM model by iteratively updating the feature matrix `M` and solving the kernel regression/classification problem.

**Parameters:**

| Parameter        | Type                                      | Description |
|-----------------|-------------------------------------------|-------------|
| `train_data`    | `tuple[torch.Tensor, torch.Tensor]`       | Tuple of `(X_train, y_train)`. `X_train` shape: `(n, d)`. `y_train` shape: `(n, c)` for multi-output or `(n,)` for single output. |
| `test_data`     | `tuple[torch.Tensor, torch.Tensor]`       | Tuple of `(X_test, y_test)`. Same shape conventions as train data. |
| `iters`         | `int`                                     | Number of recursive feature learning iterations. More iterations refine the feature matrix `M`. Typical range: 3–10. |
| `classification`| `bool`                                    | If `True`, evaluates accuracy (classification). If `False`, evaluates regression loss (MSE or similar). |

**Returns:** `None`

**Side Effects:**
- Updates internal feature matrix `M` after each iteration
- Prints training/test metrics at each iteration

**Example:**
```python
import torch
from rfm import LaplaceRFM

device = torch.device("cpu")
model = LaplaceRFM(bandwidth=1.0, device=device, mem_gb=8, diag=False)

n, d = 1000, 100
X_train = torch.randn(n, d)
y_train = (X_train[:, 0] > 0).float().unsqueeze(1)
X_test = torch.randn(n, d)
y_test = (X_test[:, 0] > 0).float().unsqueeze(1)

model.fit(
    (X_train, y_train),
    (X_test, y_test),
    iters=5,
    classification=False
)
```

---

## Memory Management Notes

The `mem_gb` parameter controls how kernel matrices are computed in chunks to avoid out-of-memory errors.

**Recommended settings:**

| Hardware          | `mem_gb` value                                      |
|-------------------|-----------------------------------------------------|
| CPU only          | 8 (or available system RAM in GB)                  |
| GPU (8GB VRAM)    | 7                                                   |
| GPU (16GB VRAM)   | 15                                                  |
| GPU (40GB VRAM)   | 39                                                  |

**Auto-detection pattern:**
```python
import torch

if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    DEV_MEM_GB = torch.cuda.get_device_properties(DEVICE).total_memory // 1024**3 - 1
else:
    DEVICE = torch.device("cpu")
    DEV_MEM_GB = 8
```

---

## Diagonal vs Full Kernel Matrix

| Mode         | `diag` value | Use case |
|--------------|-------------|----------|
| Full matrix  | `False`     | Small to medium datasets; most accurate |
| Diagonal     | `True`      | Large datasets; memory-efficient approximation |

---

## Dependencies

| Package       | Version  | Notes                        |
|---------------|----------|------------------------------|
| Python        | 3.8+     | Required                     |
| PyTorch       | 1.13     | Stable; other versions may work |
| torchvision   | 0.14.0   | Required                     |
| hickle        | 5.0.2    | Required for data I/O        |
| tqdm          | latest   | Progress bars during training |

---

## Notebooks

Two reference notebooks are provided in the repository:

| Notebook         | Description                              |
|------------------|------------------------------------------|
| `low_rank.ipynb` | Example on low-rank polynomial functions |
| `svhn.ipynb`     | Example on the SVHN image dataset        |

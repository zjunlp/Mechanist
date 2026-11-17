# TP4: Feature Learning in Infinite-Width Neural Networks — API Reference

## Module: `TP4MAML/inf`

### `inf/utils.py`

#### Function: `safe_sqrt`
```python
safe_sqrt(arr: torch.Tensor, eps: float) -> torch.Tensor
```
Numerically stable element-wise square root. Clamps negative values near zero before applying sqrt.

**Parameters:**
- `arr` (torch.Tensor): Input tensor, may contain small negative values due to floating-point errors.
- `eps` (float): Threshold below which values are clamped to zero.

**Returns:** `torch.Tensor` — Element-wise sqrt of clamped arr.

---

#### Function: `safe_acos`
```python
safe_acos(arr: torch.Tensor, eps: float) -> torch.Tensor
```
Numerically stable element-wise arccos. Clamps values to `[-1+eps, 1-eps]` before applying acos.

**Parameters:**
- `arr` (torch.Tensor): Input tensor with values nominally in [-1, 1].
- `eps` (float): Margin for clamping.

**Returns:** `torch.Tensor` — Element-wise arccos result.

---

#### Function: `F00ReLU`
```python
F00ReLU(c: torch.Tensor, v: torch.Tensor, v2: torch.Tensor) -> torch.Tensor
```
Computes the arc-cosine (ReLU) kernel value used in GP/NTK computations for infinite-width networks.

**Parameters:**
- `c` (torch.Tensor): Cosine similarity between input vectors.
- `v` (torch.Tensor): Variance of first input.
- `v2` (torch.Tensor): Variance of second input.

**Returns:** `torch.Tensor` — Kernel value K(x, x').

**Notes:** Used internally by `InfGP1LP` and `InfNTK1LP` for kernel matrix computation.

---

#### Class: `MyLinear`
```python
class MyLinear(nn.Module)
```
Custom linear layer implementing infinite-width scaling conventions (NTK or muP parameterization).

**Constructor:**
```python
MyLinear(in_features: int, out_features: int, bias: bool = True)
```

**Parameters:**
- `in_features` (int): Size of each input sample.
- `out_features` (int): Size of each output sample.
- `bias` (bool): If True, adds a learnable bias.

**Methods:**
- `forward(x: torch.Tensor) -> torch.Tensor`: Standard linear forward with appropriate scaling.

---

### `inf/inf1lp.py`

#### Class: `InfGP1LP`
```python
class InfGP1LP
```
Infinite-width Gaussian Process limit of a 1-hidden-layer perceptron. Implements exact GP inference in the infinite-width limit using the arc-cosine kernel.

**Constructor:**
```python
InfGP1LP(input_dim: int, output_dim: int)
```

**Parameters:**
- `input_dim` (int): Dimensionality of input features.
- `output_dim` (int): Number of output classes/dimensions.

**Key Methods:**
- `forward(x: torch.Tensor) -> torch.Tensor`: Compute GP predictive mean for inputs x.
- `kernel(x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor`: Compute GP kernel matrix K(x1, x2).

**Notes:** Does not maintain explicit weights; prediction is via kernel regression.

---

#### Class: `FinGP1LP`
```python
class FinGP1LP(nn.Module)
```
Finite-width baseline 1-hidden-layer perceptron for comparison with infinite-width limits.

**Constructor:**
```python
FinGP1LP(input_dim: int, output_dim: int, width: int)
```

**Parameters:**
- `input_dim` (int): Dimensionality of input features.
- `output_dim` (int): Number of output classes/dimensions.
- `width` (int): Number of hidden units.

**Methods:**
- `forward(x: torch.Tensor) -> torch.Tensor`: Standard MLP forward pass.

---

#### Class: `InfNTK1LP`
```python
class InfNTK1LP
```
Infinite-width Neural Tangent Kernel limit of a 1-hidden-layer perceptron. Implements NTK regression / gradient flow in the infinite-width limit.

**Constructor:**
```python
InfNTK1LP(input_dim: int, output_dim: int)
```

**Parameters:**
- `input_dim` (int): Dimensionality of input features.
- `output_dim` (int): Number of output classes/dimensions.

**Key Methods:**
- `forward(x: torch.Tensor) -> torch.Tensor`: Compute NTK predictive output.
- `ntk_kernel(x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor`: Compute NTK matrix.

---

### `inf/optim.py`

#### Class: `InfSGD`
```python
class InfSGD(torch.optim.Optimizer)
```
SGD optimizer with scaling appropriate for infinite-width (NTK/muP) parameterization. Adjusts learning rates per parameter group according to width scaling.

**Constructor:**
```python
InfSGD(
    params,
    lr: float,
    momentum: float = 0,
    dampening: float = 0,
    weight_decay: float = 0,
    nesterov: bool = False
)
```

**Parameters:**
- `params`: Iterable of parameters or parameter groups.
- `lr` (float): Learning rate.
- `momentum` (float): SGD momentum factor.
- `dampening` (float): Dampening for momentum.
- `weight_decay` (float): L2 penalty coefficient.
- `nesterov` (bool): Enables Nesterov momentum.

**Methods:**
- `step(closure=None)`: Performs a single optimization step with infinite-width scaling.

---

#### Class: `InfMultiStepLR`
```python
class InfMultiStepLR(torch.optim.lr_scheduler._LRScheduler)
```
Multi-step learning rate scheduler compatible with `InfSGD`.

**Constructor:**
```python
InfMultiStepLR(
    optimizer: InfSGD,
    milestones: List[int],
    gamma: float = 0.1,
    last_epoch: int = -1
)
```

**Parameters:**
- `optimizer` (InfSGD): The InfSGD optimizer instance.
- `milestones` (List[int]): List of epoch indices at which to decay lr.
- `gamma` (float): Multiplicative factor of learning rate decay.
- `last_epoch` (int): The index of the last epoch.

**Methods:**
- `step()`: Update learning rate according to schedule.
- `get_last_lr() -> List[float]`: Return last computed learning rates.

---

### `inf/dynamicarray.py`

#### Class: `DynArr`
```python
class DynArr
```
Dynamically growing array for storing intermediate activations during infinite-width forward passes where size is not known in advance.

**Constructor:**
```python
DynArr()
```

**Methods:**
- `append(tensor: torch.Tensor)`: Append a tensor to the array.
- `__len__() -> int`: Return current length.
- `__getitem__(idx: int) -> torch.Tensor`: Index into stored tensors.

---

#### Class: `CycArr`
```python
class CycArr
```
Fixed-capacity cyclic (ring buffer) array. Overwrites oldest entries when full.

**Constructor:**
```python
CycArr(capacity: int)
```

**Parameters:**
- `capacity` (int): Maximum number of elements before overwriting.

**Methods:**
- `append(tensor: torch.Tensor)`: Append tensor, overwriting oldest if full.
- `__len__() -> int`: Return current number of stored elements (up to capacity).
- `__getitem__(idx: int) -> torch.Tensor`: Index into stored tensors.

---

## Module: `TP4MAML/meta`

### `meta/cached_omniglot.py`

#### Class: `CachedOmniglot`
```python
class CachedOmniglot
```
Omniglot meta-learning dataset with disk caching for fast repeated loading. Compatible with torchmeta task-sampling API.

**Constructor:**
```python
CachedOmniglot(
    root: str,
    num_classes_per_task: int,
    transform=None,
    target_transform=None,
    class_augmentations=None,
    meta_train: bool = False,
    meta_val: bool = False,
    meta_test: bool = False,
    dataset_transform=None
)
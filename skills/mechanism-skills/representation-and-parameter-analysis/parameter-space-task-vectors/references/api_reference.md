# Task Vectors API Reference

Repository: [mlfoundations/task_vectors](https://github.com/mlfoundations/task_vectors)  
Paper: [Editing Models with Task Arithmetic (ICLR 2023)](https://arxiv.org/abs/2212.04089)

---

## Module: `task_vectors` (`src/task_vectors.py`)

### Class: `TaskVector`

Represents a direction in the weight space of a pre-trained model, computed as
the element-wise difference between fine-tuned and pre-trained weights.

**Constructor:**
```python
TaskVector(
    pretrained_checkpoint: str,
    finetuned_checkpoint: str,
    vector: dict = None
)
```

**Parameters:**
- `pretrained_checkpoint` (str): Path to the `.pt` file of the pre-trained (zero-shot) model.
- `finetuned_checkpoint` (str): Path to the `.pt` file of the fine-tuned model.
- `vector` (dict, optional): Pre-computed weight-difference dictionary. If provided, checkpoints are not loaded.

**Attributes:**
- `vector` (dict): Maps parameter name (str) → tensor difference (torch.Tensor).

---

#### `__neg__(self) -> TaskVector`

Negate all tensors in the task vector.

```python
neg_tv = -task_vector
```

**Returns:** A new `TaskVector` with all values negated.

**Effect when applied:** Degrades model performance on the target task while having minimal impact on control tasks.

---

#### `__add__(self, other: TaskVector) -> TaskVector`

Element-wise addition of two task vectors.

```python
combined = task_vector_A + task_vector_B
```

**Parameters:**
- `other` (TaskVector): The task vector to add.

**Returns:** A new `TaskVector` representing the sum.

**Effect when applied:** The resulting model performs better on both tasks simultaneously.

---

#### `__radd__(self, other) -> TaskVector`

Right-add to support Python's built-in `sum()`.

```python
combined = sum([tv1, tv2, tv3])  # calls __radd__ for the initial 0 + tv1
```

**Parameters:**
- `other` (int | TaskVector): Either `0` (from `sum` initialization) or another `TaskVector`.

**Returns:** `self` if `other == 0`, otherwise `self + other`.

---

#### `__sub__(self, other: TaskVector) -> TaskVector`

Element-wise subtraction (implemented as `self + (-other)`).

```python
analogy = task_vector_C + task_vector_B - task_vector_A
```

**Parameters:**
- `other` (TaskVector): The task vector to subtract.

**Returns:** A new `TaskVector`.

---

#### `apply_to(pretrained_checkpoint: str, scaling_coef: float = 1.0) -> nn.Module`

Apply the task vector to a pre-trained model by adding `scaling_coef * vector` to its weights.

```python
image_encoder = task_vector.apply_to(pretrained_checkpoint, scaling_coef=0.8)
```

**Parameters:**
- `pretrained_checkpoint` (str): Path to the pre-trained `.pt` checkpoint.
- `scaling_coef` (float): Scalar multiplier controlling the magnitude of the task vector applied. Typical range: 0.3–1.0. Default: `1.0`.

**Returns:** Modified image encoder (`nn.Module`) with updated weights.

**Notes:**
- A `scaling_coef` of `0.0` returns the unmodified pre-trained model.
- A `scaling_coef` of `1.0` moves fully to the fine-tuned weight space.
- Values in (0, 1) interpolate between pre-trained and fine-tuned behavior.

---

## Module: `eval` (`src/eval.py`)

### Function: `eval_single_dataset`

```python
eval_single_dataset(
    image_encoder: nn.Module,
    dataset_name: str,
    args: argparse.Namespace
) -> dict
```

Evaluate an image encoder on a single dataset using zero-shot classification.

**Parameters:**
- `image_encoder` (nn.Module): The image encoder to evaluate (e.g., returned by `TaskVector.apply_to`).
- `dataset_name` (str): Name of the dataset. Supported values: `'Cars'`, `'DTD'`, `'EuroSAT'`, `'GTSRB'`, `'MNIST'`, `'RESISC45'`, `'SUN397'`, `'SVHN'`, `'ImageNet'`, `'CIFAR10'`, `'CIFAR100'`, `'STL10'`.
- `args` (argparse.Namespace): Configuration namespace. Must contain:
  - `args.data_location` (str): Root path to dataset files.
  - `args.model` (str): Model identifier (e.g., `'ViT-L-14'`).
  - `args.save` (str): Directory for saving intermediate outputs.

**Returns:**
- `dict`: Evaluation metrics, typically containing accuracy and/or top-5 accuracy.

**Example:**
```python
from eval import eval_single_dataset
from args import parse_arguments

args = parse_arguments()
args.data_location = '/data'
args.model = 'ViT-L-14'
args.save = 'checkpoints/ViT-L-14'

metrics = eval_single_dataset(image_encoder, 'MNIST', args)
print(metrics)
```

---

## Module: `args` (`src/args.py`)

### Function: `parse_arguments`

```python
parse_arguments() -> argparse.Namespace
```

Parse command-line arguments (or return defaults when called with no CLI args).

**Returns:**
- `argparse.Namespace` with fields including:
  - `data_location` (str): Path to dataset root.
  - `model` (str): CLIP model identifier.
  - `save` (str): Checkpoint save directory.
  - `batch_size` (int): Evaluation batch size.
  - `workers` (int): DataLoader worker count.

**Example:**
```python
from args import parse_arguments

args = parse_arguments()
args.data_location = '/path/to/data'
args.model = 'ViT-L-14'
args.save = 'checkpoints/ViT-L-14'
```

---

## Module: `modeling` (`src/modeling.py`)

Contains CLIP model wrappers used internally by `TaskVector.apply_to` and `eval_single_dataset`.

### Class: `ImageEncoder`

Wraps a CLIP vision encoder for feature extraction and classification.

**Constructor (inferred):**
```python
ImageEncoder(args: argparse.Namespace, keep_lang: bool = False)
```

**Parameters:**
- `args` (argparse.Namespace): Must include `args.model`.
- `keep_lang` (bool): Whether to retain the language encoder alongside the vision encoder.

---

## Module: `heads` (`src/heads.py`)

Contains classification head utilities for constructing zero-shot classifiers.

### Class: `ClassificationHead`

Builds a linear classification head from CLIP text embeddings.

**Constructor (inferred):**
```python
ClassificationHead(normalize: bool, weights: torch.Tensor)
```

**Parameters:**
- `normalize` (bool): Whether to L2-normalize features before classification.
- `weights` (torch.Tensor): Weight matrix derived from CLIP text embeddings for each class.

---

## Module: `datasets` (`src/datasets/`)

### Supported Datasets

| Class | File | Dataset |
|-------|------|---------|
| `Cars` | `cars.py` | Stanford Cars |
| `CIFAR10` | `cifar10.py` | CIFAR-10 |
| `CIFAR100` | `cifar100.py` | CIFAR-100 |
| `DTD` | `dtd.py` | Describable Textures Dataset |
| `EuroSAT` | `eurosat.py` | EuroSAT |
| `GTSRB` | `gtsrb.py` | German Traffic Sign Recognition Benchmark |
| `ImageNet` | `imagenet.py` | ImageNet |
| `MNIST` | `mnist.py` | MNIST |
| `RESISC45` | `resisc45.py` | RESISC45 Remote Sensing |
| `STL10` | `stl10.py` | STL-10 |
| `SUN397` | `sun397.py` | SUN397 |
| `SVHN` | `svhn.py` | Street View House Numbers |

Each dataset class is instantiated with:
```python
dataset = DatasetClass(
    preprocess,           # torchvision transform
    location=data_root,  # root data directory
    batch_size=128,
    num_workers=4
)
```

And exposes:
- `dataset.train_loader` — `DataLoader` for training split.
- `dataset.test_loader`  — `DataLoader` for test/validation split.
- `dataset.classnames`   — List of human-readable class name strings.
- `dataset.templates`    — List of prompt templates for zero-shot CLIP classification.

---

### Helper Functions in `src/datasets/common.py`

#### `maybe_dictionarize(batch) -> dict`

Normalize a batch (which may be a tuple or dict) into a consistent dict format.

```python
maybe_dictionarize(batch: tuple | dict) -> dict
```

**Returns:** Dict with at least `'images'` and `'labels'` keys.

---

#### `get_features_helper(image_encoder, dataloader, device) -> Tuple[Tensor, Tensor]`

Extract image features from a dataloader using a given encoder.

```python
get_features_helper(
    image_encoder: nn.Module,
    dataloader: DataLoader,
    device: torch.device
) -> Tuple[torch.Tensor, torch.Tensor]
```

**Returns:** `(features, labels)` tensors for the full dataloader.

---

#### `get_features(is_train, image_encoder, dataset) -> Tuple[Tensor, Tensor]`

Extract features from either the train or test split of a dataset.

```python
get_features(
    is_train: bool,
    image_encoder: nn.Module,
    dataset
) -> Tuple[torch.Tensor, torch.Tensor]
```

**Parameters:**
- `is_train` (bool): If `True`, use `dataset.train_loader`; otherwise use `dataset.test_loader`.
- `image_encoder` (nn.Module): Encoder to extract features.
- `dataset`: Dataset instance with `.train_loader` and `.test_loader`.

**Returns:** `(features, labels)`.

---

### Class: `SubsetSampler` (`src/datasets/common.py`)

A PyTorch sampler that yields only a specified subset of indices.

```python
SubsetSampler(indices: List[int])
```

**Parameters:**
- `indices` (List[int]): The indices to sample.

---

### Class: `ImageFolderWithPaths` (`src/datasets/common.py`)

Extends `torchvision.datasets.ImageFolder` to also return file paths alongside images and labels.

```python
ImageFolderWithPaths(root: str, transform=None)
```

**Returns per item:** `(image_tensor, label_int, file_path_str)`

---

### Class: `FeatureDataset` (`src/datasets/common.py`)

Wraps pre-extracted feature tensors as a `torch.utils.data.Dataset`.

```python
FeatureDataset(features: torch.Tensor, labels: torch.Tensor)
```

**Parameters:**
- `features` (torch.Tensor): Shape `[N, D]` feature matrix.
- `labels` (torch.Tensor): Shape `[N]` integer labels.

---

## Module: `finetune` (`src/finetune.py`)

Contains the fine-tuning loop used to produce the fine-tuned checkpoints from which task vectors are derived.

Typical usage (command line):
```bash
python src/finetune.py --model ViT-L-14 --dataset MNIST --data-location /data --save checkpoints
```

Key arguments (passed via `parse_arguments()`):
- `--model`: CLIP model variant.
- `--dataset`: Dataset name.
- `--data-location`: Root data directory.
- `--save`: Where to write `finetuned.pt`.
- `--lr`, `--wd`, `--epochs`, `--batch-size`: Standard training hyperparameters.

---

## Checkpoint Format

Checkpoints are standard PyTorch `.pt` files loaded via `torch.load`.

**Zero-shot checkpoint** (`zeroshot.pt`): Pre-trained CLIP image encoder state dict.  
**Fine-tuned checkpoint** (`finetuned.pt`): Image encoder state dict after task-specific fine-tuning.

Both checkpoints must share identical architecture (same model variant) for task vector arithmetic to be valid.

---

## Arithmetic Operator Summary

| Operation | Python Syntax | Effect on Applied Model |
|-----------|--------------|------------------------|
| Create | `TaskVector(pt_ckpt, ft_ckpt)` | Vector = ft_weights − pt_weights |
| Negate | `-tv` | Degrades target task; minimal control task effect |
| Add | `tv_a + tv_b` | Improves both tasks simultaneously |
| Sum list | `sum([tv_a, tv_b, tv_c])` | Improves all listed tasks |
| Subtract | `tv_c - tv_a` | Analogy building block |
| Analogy | `tv_c + tv_b - tv_a` | Transfers "A→B" relationship to C→D |
| Apply | `tv.apply_to(pt_ckpt, scaling_coef)` | Returns modified `nn.Module` |

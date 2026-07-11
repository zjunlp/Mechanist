---
name: image
description: 'Canonical ImageNet eval preprocessing — square 256×256 resize → 224 center crop → ImageNet mean/std — for CV experiments probing ImageNet-pretrained backbones (ResNet, ViT, VGG, EfficientNet). Use this skill whenever a `torchvision.transforms` / `PIL` pipeline is being written, audited, or debugged for inference-time eval: feature extraction, activation hooks, mechanistic interpretability, top-k-activating-image retrieval, neuron labeling, or reproducibility checks. Apply it even when the user does not say "preprocessing" — triggers include `Resize`, `CenterCrop`, `T.Compose`, "ImageNet eval", "my activations changed between runs", or "results differ from the paper". Covers the `Resize(256)` (int, short-side) vs `Resize((256, 256))` (tuple, square) trap.'
---

# ImageNet Eval Preprocessing

## Drop-in snippet

```python
import torchvision.transforms as T

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD  = (0.229, 0.224, 0.225)

def imagenet_eval_transform(crop: int = 224) -> T.Compose:
    """Canonical ImageNet eval preprocessing.

    Pipeline:
        1. Square resize to 256 x 256       (NOT short-side resize)
        2. Center crop to `crop` x `crop`   (default 224)
        3. ToTensor                          (RGB / 255 -> [0, 1])
        4. Normalize with ImageNet mean/std
    """
    return T.Compose([
        T.Resize((256, 256), antialias=True),   # tuple => square resize
        T.CenterCrop(crop),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
```

`antialias=True` is set explicitly because PIL inputs default to it but tensor inputs do not, and the explicit flag removes a version-dependent warning across torchvision ≥0.15.

## The trap: `Resize(256)` vs `Resize((256, 256))`

Calling `T.Resize` with an **int** vs a **tuple** does two different things:

| Call | Behaviour | A `500 × 800` input becomes |
|---|---|---|
| `T.Resize(256)` (int) | Short-side resize, aspect ratio **preserved** | `256 × 410` |
| `T.Resize((256, 256))` (tuple) | Square resize, aspect ratio **NOT preserved** | `256 × 256` |

After the subsequent `T.CenterCrop(224)`, the two pipelines extract **different patches** from any non-square image. Most natural images (and most ImageNet validation images) are non-square, so the divergence applies to virtually the whole dataset.

For mechanistic interpretability and any work that ranks images by activation magnitude, this is a silent reproducibility hazard: the *top-k maximally activating images* set shifts when the crop shifts, which propagates to every downstream artefact — semantic embeddings, neuron labels, clarity / polysemanticity scores, faithfulness ablations. Numbers will look reasonable; they just will not match a reference pipeline that uses the other convention.

## Why square resize (and when another convention is correct)

Square resize forces every input into a deterministic, source-aspect-agnostic 224×224 patch. That property is what you usually want for:

- Reproducibility across heterogeneous datasets (the same recipe works for portrait, landscape, and square inputs).
- Cross-architecture comparisons where ResNet, ViT, VGG, and EfficientNet should see exactly the same pixels.
- Hooked activation collection where rank stability of top-k matters more than honouring source aspect ratio.

Three other conventions are also legitimate; the choice between them is *intentional*, not a default:

| Convention | Pipeline | Use when |
|---|---|---|
| **Square 256→224** (this skill) | `Resize((256, 256)) + CenterCrop(224)` + ImageNet mean/std | Probing a frozen ImageNet backbone for interpretability / concept work. |
| **Classic ResNet** | `Resize(256) + CenterCrop(224)` + ImageNet mean/std | Reproducing a pre-2022 paper that explicitly used short-side 256. |
| **torchvision V2 weights** | `Resize(232) + CenterCrop(224)` + ImageNet mean/std | Reproducing the accuracy reported for `*_Weights.IMAGENET1K_V2`. |
| **CLIP image tower** | `Resize(224, BICUBIC) + CenterCrop(224)` + CLIP mean `[0.48145, 0.45783, 0.40821]` std `[0.26863, 0.26130, 0.27578]` | Feeding a CLIP encoder. Mixing ImageNet stats into a CLIP encoder is a different bug class with the same shape. |

## How to apply

### New experiment

Paste `imagenet_eval_transform` into a `data_utils.py` (or equivalent) and pass it to your `Dataset` / `DataLoader`. Do this as the default for any ImageNet probing pipeline; reach for a different convention only if the row in the table above motivates it.

### Audit an existing repo

Run:

```bash
grep -rn "Resize\|CenterCrop\|RandomCrop\|transforms\.\|image_processor" experiments/
```

For each hit, decide based on the call:

- `T.Resize(256)` / `T.Resize(size=256)` — short-side resize. If the experiment intends the square-resize convention, patch to `T.Resize((256, 256), antialias=True)`. If the experiment intends classic ResNet eval, leave it but document the intent.
- `T.Resize((256, 256))` — already square; leave alone.
- `T.Resize(232)` paired with `IMAGENET1K_V2` weights — intentional torchvision V2 reproduction; do not change without a reason.
- HF `image_processor(...)` or timm `resolve_data_config(...)` — model's own native pipeline. This skill does not apply; overriding it can break the input distribution the model was trained on.
- `RandomResizedCrop` / `RandomHorizontalFlip` in an eval-time pass — likely a training-augmentation transform leaking into eval. Investigate.

When patching, leave a one-line comment so the next reader knows the choice is deliberate:

```python
T.Resize((256, 256), antialias=True),   # square resize per skills/image
```

### Pick a convention when the paper is silent

If a paper just says "ImageNet preprocessing" with no further detail, two defaults are reasonable:

- Use the model's own `image_processor` / `transforms()` when reporting accuracy with its trained weights — that matches what the model was evaluated on.
- Use this skill's `imagenet_eval_transform` when doing mechanistic probing on top of a frozen backbone — that gives every architecture the same pixels.

Surface the ambiguity rather than picking silently. The two pipelines diverge on non-square images, and the divergence only becomes visible downstream, often after a wasted run.

---
name: clip-dissect
description: "Use this skill when you need to automatically describe or interpret the functionality of individual neurons in deep neural networks (DNNs) using CLIP-based semantic analysis, perform mechanistic interpretability research on vision models, dissect convolutional or transformer-based image classifiers, identify what visual concepts activate specific neurons, or compare neuron descriptions across different probing datasets and concept sets."
---

## Method and use

Label vision units by relating their activation patterns to concept embeddings. Concept vocabulary and probing distribution constrain descriptions. For component semantic vectors, compare embedding relevant image regions with whole-image references; labels remain correlational until tested.


# CLIP-Dissect Skill

## When to Use

Activate this skill when:
- You need to **automatically describe** what individual neurons in a deep vision network respond to
- You are performing **mechanistic interpretability** or **explainable AI** research on CNNs or Vision Transformers
- You want to understand **neuron-level representations** in models like ResNet-50, ResNet-18, ViT, or custom models
- You need to **compare neuron descriptions** against baselines like NetDissect or MILAN
- You want to probe neural network layers using a **concept set** (e.g., 3k, 10k, 20k English words)
- You are working with **Broden** or **ImageNet** as a probing dataset
- You need to evaluate how well neuron descriptions **predict class-level behavior** in a model
- Keywords: `neuron dissection`, `CLIP`, `neural network interpretability`, `concept-based explanations`, `network dissection`, `probe dataset`, `activation analysis`, `feature visualization`

---

## Quick Reference

- **Paper:** [CLIP-Dissect: Automatic Description of Neuron Representations in Deep Vision Networks](https://arxiv.org/abs/2204.10965) — ICLR 2023 Spotlight
- **Repository:** https://github.com/Trustworthy-ML-Lab/CLIP-dissect
- **CLIP Source:** https://github.com/openai/CLIP
- **Broden Dataset:** Downloaded via `bash dlbroden.sh` (based on [NetDissect-Lite](https://github.com/CSAILVision/NetDissect-Lite))
- **Concept Sets:** Google 10k/20k words (https://github.com/first20hours/google-10000-english), EF 3k words (https://www.ef.edu/english-resources/english-vocabulary/top-3000-words/)
- **PyTorch Install:** https://pytorch.org/get-started/previous-versions/

---

## Installation / Setup

### Prerequisites
- Python 3.10
- PyTorch >= 1.12.0 (also compatible with 2.0), Torchvision >= 0.13
- CUDA-compatible GPU recommended (CPU inference supported)

### Step-by-Step Installation

```bash
# Step 1: Clone the repository
git clone https://github.com/Trustworthy-ML-Lab/CLIP-dissect.git
cd CLIP-dissect

# Step 2: Install Python 3.10 (if not already installed)
# Using conda:
conda create -n clip_dissect python=3.10
conda activate clip_dissect

# Step 3: Install PyTorch and Torchvision (tested with 1.12.0, also works with 2.0)
# Visit https://pytorch.org/get-started/previous-versions/ for exact commands.
# Example for CUDA 11.3:
pip install torch==1.12.0+cu113 torchvision==0.13.0+cu113 --extra-index-url https://download.pytorch.org/whl/cu113

# Step 4: Install remaining dependencies
pip install -r requirements.txt

# Step 5: Download the Broden dataset (images only)
bash dlbroden.sh

# Step 6 (Optional): Download ResNet-18 pretrained on Places-365
bash dlzoo_example.sh
```

### ImageNet Setup (Optional)
To evaluate using ImageNet validation set, set the correct path in `data_utils.py`:
```python
DATASET_ROOTS = {
    "imagenet_val": "/path/to/your/imagenet/val",
    ...
}
```

---

## Core Features

- **Automatic Neuron Description:** Assigns human-readable concept labels to individual neurons in any layer of a DNN using CLIP's vision-language embeddings.
- **Efficient Similarity Computation:** Uses cosine similarity between neuron activation patterns and CLIP text embeddings of candidate concepts.
- **Multi-Layer Dissection:** Dissect multiple layers of a target model in a single run (e.g., `layer1`, `layer2`, `layer3`, `layer4`, `fc` for ResNet-50).
- **Flexible Probing Datasets:** Supports Broden, ImageNet validation set, and custom torchvision-compatible datasets.
- **Flexible Concept Sets:** Bundled concept sets with 3k, 10k, and 20k English words; supports custom `.txt` concept files.
- **Activation Caching:** Automatically caches computed activations in `saved_activations/` to avoid recomputation on repeated runs.
- **Model Agnostic:** Works with any PyTorch model — ResNet, ViT, custom architectures — by implementing a simple loader function.
- **Experiment Notebooks:** Reproduces all paper figures and tables via Jupyter notebooks in `experiments/`.
- **Comparison Baselines:** Includes pre-computed results from NetDissect and MILAN for direct comparison.
- **Device Flexibility:** Runs on CUDA GPU or CPU via `--device` argument.

---

## Usage Examples

### Quickstart — Dissect ResNet-50 (ImageNet) with Broden

Dissects 5 layers of ResNet-50 pretrained on ImageNet using Broden as the probing dataset. Results saved in `results/resnet50_{datetime}/descriptions.csv`.

```bash
python describe_neurons.py
```

### Dissect a Custom Model

1. Implement your model loader in `data_utils.py` under `get_target_model`:

```python
def get_target_model(target_name, device):
    if target_name == "my_custom_model":
        model = MyCustomModel()
        model.load_state_dict(torch.load("path/to/weights.pth"))
        model.eval()
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        return model, preprocess
```

2. Run dissection:

```bash
python describe_neurons.py --target_model my_custom_model
```

### Using a Custom Probing Dataset

1. Implement dataset loading in `data_utils.py` under `get_data`:

```python
def get_data(dataset_name, preprocess):
    if dataset_name == "my_dataset":
        return MyDataset(root="/path/to/data", transform=preprocess)
```

2. Add dataset name to `--d_probe` choices in `describe_neurons.py`.

3. Run:

```bash
python describe_neurons.py --d_probe my_dataset
```

### Using a Custom Concept Set

```bash
python describe_neurons.py --concept_set /path/to/my_concepts.txt
```

Each line of the `.txt` file should contain one concept word or phrase.

### Specifying Device

```bash
# Use CPU instead of GPU
python describe_neurons.py --device cpu

# Use a specific GPU
python describe_neurons.py --device cuda:1
```

### Reproducing Paper Results

```bash
# Reproduce Table 1 (ResNet-50 ImageNet quantitative results)
jupyter notebook experiments/table1_quantitative_rn50.ipynb

# Reproduce Table 2 (ResNet-18 Places quantitative results)
jupyter notebook experiments/table2_quantitative_rn18.ipynb

# Reproduce Figure 1, 6, 7, 9 (qualitative comparisons)
jupyter notebook experiments/fig_1_6_7_9_qualitative_comparison.ipynb
```

### Full CLI Reference

```bash
python describe_neurons.py \
    --target_model resnet50 \
    --d_probe broden \
    --concept_set data/20k.txt \
    --batch_size 200 \
    --device cuda \
    --pool_mode avg \
    --save_dir results/
```

---

## Key APIs / Models

### Target Models Supported
| Model Name | Architecture | Dataset |
|---|---|---|
| `resnet50` | ResNet-50 | ImageNet (torchvision pretrained) |
| `resnet18_places` | ResNet-18 | Places-365 (downloaded via `dlzoo_example.sh`) |
| Custom models | Any PyTorch model | User-defined |
| ViT variants | Vision Transformer | Supported (see `fig11_vit_qualitative.ipynb`) |

### Probing Datasets
| Dataset Name | Description |
|---|---|
| `broden` | Broden dataset — diverse visual concepts (downloaded via `dlbroden.sh`) |
| `imagenet_val` | ImageNet validation set (user must provide path) |
| Custom | User-defined torchvision Dataset |

### Concept Sets (bundled in `data/`)
| File | Size | Source |
|---|---|---|
| `data/3k.txt` | 3,000 words | EF English vocabulary |
| `data/10k.txt` | 10,000 words | Google 10k English |
| `data/20k.txt` | 20,000 words | Google 20k English |

### Core Functions

#### `describe_neurons.py` (main entry point)

## Demo Scripts

### `scripts/run_clip_dissect.py`


See [`scripts/run_clip_dissect.py`](scripts/run_clip_dissect.py) for the reference template. Adapt its model, data, and measurement assumptions.


## Supporting material

- [Method papers](article_references.md).
- [Family papers](../article_references.md).

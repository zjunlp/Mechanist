#!/usr/bin/env python3
"""
TP4 MAML Training Demo

Shows how to invoke MAML training programmatically (mirroring train.py usage).
Demonstrates the dataset loading and metalearner API.

Requires: torch, torchmeta (see TP4MAML/meta/requirements.txt)
Run from TP4MAML/meta/: python ../../scripts/maml_training_demo.py
"""

import sys
import os
import argparse

# Adjust paths for running from repo root
MAML_META_PATH = os.path.join(os.path.dirname(__file__), '..', 'TP4MAML', 'meta')
MAML_INF_PATH = os.path.join(os.path.dirname(__file__), '..', 'TP4MAML')
sys.path.insert(0, MAML_META_PATH)
sys.path.insert(0, MAML_INF_PATH)


def build_omniglot_dataset(data_folder: str, num_ways: int = 5, num_shots: int = 1,
                            num_shots_test: int = 15):
    """
    Build Omniglot meta-learning dataset using CachedOmniglot.

    Args:
        data_folder: Path to Omniglot data directory.
        num_ways: Number of classes per episode (N-way).
        num_shots: Number of support examples per class (K-shot).
        num_shots_test: Number of query examples per class.

    Returns:
        Tuple of (meta_train_dataset, meta_val_dataset, meta_test_dataset)
    """
    try:
        from cached_omniglot import CachedOmniglot
        import torchmeta
        from torchmeta.transforms import ClassSplitter, Categorical
        from torchvision.transforms import Compose, Resize, ToTensor

        transform = Compose([Resize(28), ToTensor()])

        meta_train = CachedOmniglot(
            data_folder,
            num_classes_per_task=num_ways,
            transform=transform,
            target_transform=Categorical(num_ways),
            class_augmentations=[torchmeta.transforms.Rotation([90, 180, 270])],
            meta_train=True,
            dataset_transform=ClassSplitter(
                shuffle=True,
                num_support_per_class=num_shots,
                num_query_per_class=num_shots_test
            )
        )
        print(f"CachedOmniglot meta-train: {len(meta_train)} tasks")
        return meta_train

    except ImportError as e:
        print(f"Could not build Omniglot dataset (missing torchmeta or data): {e}")
        return None
    except Exception as e:
        print(f"Dataset error: {e}")
        return None


def demonstrate_metalearner_api():
    """
    Show the API surface of MAML and InfMAML metalearners.
    """
    print("=== MAML / InfMAML API ===\n")

    try:
        from maml.metalearners.maml import MAML
        print(f"MAML class: {MAML.__module__}.{MAML.__name__}")
        print(f"  __init__ signature: see references/api_reference.md")
        print(f"  Key methods: train(), evaluate(), get_outer_loss()")
    except ImportError as e:
        print(f"MAML import failed: {e}")

    try:
        from maml.metalearners.infmaml import InfMAML
        print(f"\nInfMAML class: {InfMAML.__module__}.{InfMAML.__name__}")
        print(f"  Extends MAML for infinite-width networks using InfGP1LP/InfNTK1LP")
    except ImportError as e:
        print(f"InfMAML import failed: {e}")

    try:
        from maml.metalearners.meta_sgd import MetaSGD
        print(f"\nMetaSGD class: {MetaSGD.__module__}.{MetaSGD.__name__}")
        print(f"  Meta-SGD variant with per-parameter learned learning rates")
    except ImportError as e:
        print(f"MetaSGD import failed: {e}")


def show_training_command_equivalents():
    """
    Print the equivalent train.py CLI commands for common configurations.
    """
    print("\n=== Equivalent train.py Commands ===\n")

    configs = [
        {
            "description": "5-way 1-shot Omniglot, finite MAML",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 1 --num-steps 5"
        },
        {
            "description": "5-way 1-shot Omniglot, infinite-width MAML (GP limit)",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 1 --num-steps 5 --inf --use-gp"
        },
        {
            "description": "5-way 5-shot Omniglot, infinite-width MAML (NTK limit)",
            "cmd": "python train.py --dataset omniglot --num-ways 5 --num-shots 5 --num-steps 5 --inf"
        },
        {
            "description": "Run all experiments (uses train_all.sh)",
            "cmd": "cd TP4MAML && bash train_all.sh"
        },
    ]

    for cfg in configs:
        print(f"# {cfg['description']}")
        print(f"  {cfg['cmd']}\n")


def show_word2vec_commands():
    """
    Show Word2Vec experiment commands.
    """
    print("=== Word2Vec Experiment Commands ===\n")

    steps = [
        ("Build C binaries", "cd Word2Vec && make"),
        ("Prepare text8 data", "bash Word2Vec/scripts/create-text8-data.sh"),
        ("Prepare fil9 data", "bash Word2Vec/scripts/create-fil9-data.sh"),
        ("Train text8 (finite)", "bash Word2Vec/scripts/train-text8.sh"),
        ("Train text8 (infinite)", "bash Word2Vec/scripts/train-text8-inf.sh"),
        ("Train fil9 (finite)", "bash Word2Vec/scripts/train-fil9.sh"),
        ("Train fil9 (infinite)", "bash Word2Vec/scripts/train-fil9-inf.sh"),
        ("Evaluate embeddings", "bash Word2Vec/scripts/evaluate.sh"),
    ]

    for name, cmd in steps:
        print(f"# {name}")
        print(f"  {cmd}\n")


if __name__ == "__main__":
    print("TP4 MAML Training Demo\n")
    demonstrate_metalearner_api()
    show_training_command_equivalents()
    show_word2vec_commands()

    # Optionally build dataset if data path provided
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
        print(f"\n=== Building Omniglot Dataset from {data_folder} ===")
        dataset = build_omniglot_dataset(data_folder, num_ways=5, num_shots=1)
        if dataset is not None:
            print("Dataset built successfully.")
    else:
        print("\nTip: Pass a data folder path as argument to test dataset loading.")
        print("  python maml_training_demo.py /path/to/omniglot/data")

#!/usr/bin/env python3
"""
SAE-Steering: Evaluation Pipeline Demo

This script demonstrates the three-step evaluation pipeline for measuring
control effectiveness of SAE-based steering on reasoning benchmarks.

Pipeline steps:
  1. eval_step1_generate_no_steering.py  — Generate no-steering baseline
  2. eval_step2_generate_steering.py     — Generate steered outputs per feature
  3. eval_step3_judge.py                 — Judge effectiveness with LLM judges

Also demonstrates:
  - Loading pre-identified feature files
  - Running all strategies in sequence
  - Reading and summarizing judge output CSVs

Requires:
  - pip install -r requirements.txt (from the SAE-Steering repo)
  - A supported LLM at MODEL_PATH
  - A compatible SAE checkpoint at SAE_PATH
  - LLM judge API credentials configured in sae_utils.py
  - Pre-generated 'answer' column in the test CSV (provided for R1-Llama-8B / Qwen3-8B)

Usage:
  python run_evaluation_pipeline.py
"""

import os
import sys
import subprocess
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# CONFIGURATION — Replace these with your actual paths
# ---------------------------------------------------------------------------
MODEL_PATH   = "/path/to/DeepSeek-R1-Distill-Llama-8B"  # or Qwen3-8B
SAE_PATH     = "/path/to/sae_checkpoint"
DATASET_DIR  = "dataset"
EVAL_DIR     = "eval_outputs"

# Test set: "aime" or "gpqa"
BENCHMARK = "aime"
TEST_SET_PATH        = f"{DATASET_DIR}/{BENCHMARK}_test.csv"
NO_STEERING_PATH     = f"{EVAL_DIR}/{BENCHMARK}_no_steering.csv"
STEERED_DIR          = f"{EVAL_DIR}/{BENCHMARK}_steered"
JUDGED_DIR           = f"{EVAL_DIR}/{BENCHMARK}_judged"

# Pre-identified features for DeepSeek-R1-Distill-Llama-8B
SELECTED_FEATURES_PATH = f"{DATASET_DIR}/selected_features_r1_llama.csv"
# For Qwen3-8B, use: f"{DATASET_DIR}/selected_features_qwen3.csv"
# ---------------------------------------------------------------------------


def ensure_dirs():
    """Create all required output directories."""
    for d in [EVAL_DIR, STEERED_DIR, JUDGED_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)
    print(f"[setup] Evaluation output directories ready.")


def load_selected_features(path: str) -> List[Tuple[int, str]]:
    """
    Load the selected features CSV and return a list of (feature_idx, strategy) tuples.

    Args:
        path: Path to selected_features_*.csv

    Returns:
        List of (feature_idx, strategy_name) tuples.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Selected features file not found: '{path}'")

    df = pd.read_csv(path)
    print(f"[features] Loaded {len(df)} selected features from '{path}':")
    print(df.to_string(index=False))

    # Expect columns: feature_idx (int), strategy (str)
    # Adjust column names if your CSV uses different headers
    features = []
    for _, row in df.iterrows():
        feat_idx = int(row.get("feature_idx", row.iloc[0]))
        strategy = str(row.get("strategy", row.iloc[1]))
        features.append((feat_idx, strategy))

    return features


def run_step1_no_steering():
    """
    Step 1: Generate no-steering baseline.

    Builds a continuation prompt from the model's initial answer + 'Wait' token,
    then generates a baseline continuation without any SAE steering.

    Returns:
        Path to the no-steering output CSV.
    """
    print("\n" + "="*60)
    print("STEP 1: Generate No-Steering Baseline")
    print("="*60)

    cmd = [
        sys.executable, "eval_step1_generate_no_steering.py",
        "--model_path",    MODEL_PATH,
        "--sae_path",      SAE_PATH,
        "--test_set_path", TEST_SET_PATH,
        "--output_path",   NO_STEERING_PATH,
    ]
    print(f"[step1] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, text=True)
    print(f"[step1] Baseline saved to: '{NO_STEERING_PATH}'")

    if os.path.exists(NO_STEERING_PATH):
        df = pd.read_csv(NO_STEERING_PATH)
        print(f"[step1] Baseline CSV has {len(df)} rows and columns: {list(df.columns)}")

    return NO_STEERING_PATH


def run_step2_steering(feature_idx: int, strategy: str) -> str:
    """
    Step 2: Generate steered outputs for a given feature index.

    Args:
        feature_idx: The SAE feature index to use as the steering vector.
        strategy: Human-readable strategy name (used for logging only).

    Returns:
        Path to the steered output CSV for this feature.
    """
    output_path = f"{STEERED_DIR}/{feature_idx}.csv"

    print(f"\n[step2] Steering with feature_idx={feature_idx} (strategy='{strategy}')")
    cmd = [
        sys.executable, "eval_step2_generate_steering.py",
        "--model_path",       MODEL_PATH,
        "--sae_path",         SAE_PATH,
        "--no_steering_path", NO_STEERING_PATH,
        "--feature_idx",      str(feature_idx),
        "--output_path",      output_path,
    ]
    print(f"[step2] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, text=True)
    print(f"[step2] Steered outputs saved to: '{output_path}'")

    return output_path


def run_step3_judge(feature_idx: int, strategy: str, steered_path: str) -> Optional[pd.DataFrame]:
    """
    Step 3: Judge control effectiveness using LLM judges.

    Uses majority vote across three LLM judges (GPT-4o, Gemini-2.5-Flash, DeepSeek-V3)
    to compute a control effectiveness score.

    Args:
        feature_idx: The SAE feature index (used for output file naming).
        strategy: The strategy name passed to the judge prompt.
        steered_path: Path to the steered outputs CSV from Step 2
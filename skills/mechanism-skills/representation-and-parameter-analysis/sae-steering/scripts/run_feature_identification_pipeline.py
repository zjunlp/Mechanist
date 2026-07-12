#!/usr/bin/env python3
"""
SAE-Steering: Feature Identification Pipeline Demo

This script demonstrates how to run the full two-stage feature identification
pipeline of SAE-Steering programmatically, mirroring what the CLI scripts do.

It covers:
  - Stage 1: Logit-based recall to get candidate SAE features
  - Stage 2a: Generating steered validation outputs per candidate feature
  - Stage 2b: Judging and ranking features, selecting top-k per strategy

Requires:
  - pip install -r requirements.txt (from the SAE-Steering repo)
  - A supported LLM (DeepSeek-R1-Distill-Llama-8B or Qwen3-8B) at model_path
  - A compatible SAE checkpoint at sae_path
  - LLM judge API credentials configured in sae_utils.py

Usage:
  python run_feature_identification_pipeline.py

NOTE: Replace all placeholder paths with actual paths on your system.
"""

import os
import sys
import subprocess
import pickle
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION — Replace these with your actual paths
# ---------------------------------------------------------------------------
MODEL_PATH = "/path/to/DeepSeek-R1-Distill-Llama-8B"   # or Qwen3-8B
SAE_PATH   = "/path/to/sae_checkpoint"                   # SAE checkpoint dir
DATASET_DIR = "dataset"
OUTPUT_DIR  = "pipeline_outputs"

CANDIDATE_FEATURES_PATH = f"{OUTPUT_DIR}/candidate_features.pkl"
VALIDATION_OUTPUTS_DIR  = f"{OUTPUT_DIR}/validation_outputs"
SELECTED_FEATURES_PATH  = f"{OUTPUT_DIR}/selected_features.csv"

JUDGE_MODEL = "gpt-4o"
TOP_K = 3
# ---------------------------------------------------------------------------


def ensure_dirs():
    """Create all required output directories."""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(VALIDATION_OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
    print(f"[setup] Output directories ready under '{OUTPUT_DIR}/'")


def run_stage1_logit_recall():
    """
    Stage 1: Logit-based recall.

    Calls find_feat_stage1_logit_recall.py as a subprocess with the
    appropriate arguments. Produces candidate_features.pkl containing
    a list of (feature_idx, strategy_name) pairs.

    Returns:
        Path to the candidate features pickle file.
    """
    print("\n" + "="*60)
    print("STAGE 1: Logit-Based Recall")
    print("="*60)

    cmd = [
        sys.executable, "find_feat_stage1_logit_recall.py",
        "--model_path", MODEL_PATH,
        "--sae_path",   SAE_PATH,
        "--output_path", CANDIDATE_FEATURES_PATH,
    ]
    print(f"[stage1] Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    print(f"[stage1] Exit code: {result.returncode}")

    if os.path.exists(CANDIDATE_FEATURES_PATH):
        with open(CANDIDATE_FEATURES_PATH, "rb") as f:
            candidates = pickle.load(f)
        print(f"[stage1] Found {len(candidates)} candidate (feature_idx, strategy) pairs.")
        for feat_idx, strategy in candidates[:5]:
            print(f"  feature_idx={feat_idx:6d}  strategy='{strategy}'")
        if len(candidates) > 5:
            print(f"  ... and {len(candidates) - 5} more.")
    else:
        print("[stage1] WARNING: Output file not found.")

    return CANDIDATE_FEATURES_PATH


def run_stage2a_steer_validation(total_parts: int = 1, part: int = 0):
    """
    Stage 2a: Generate steered outputs on the validation set.

    For each candidate feature, steers the model and saves outputs.
    Supports parallelization via total_parts / part arguments.

    Args:
        total_parts: Total number of parallel jobs (default 1 = no split).
        part: Index of this job (0-indexed).

    Returns:
        Path to the validation outputs directory.
    """
    print("\n" + "="*60)
    print(f"STAGE 2a: Steer Validation (part {part} of {total_parts})")
    print("="*60)

    cmd = [
        sys.executable, "find_feat_stage2a_steer_validation.py",
        "--model_path",             MODEL_PATH,
        "--sae_path",               SAE_PATH,
        "--candidate_features_path", CANDIDATE_FEATURES_PATH,
        "--validation_set_path",    f"{DATASET_DIR}/aime_his_50.csv",
        "--output_dir",             VALIDATION_OUTPUTS_DIR,
        "--total_parts",            str(total_parts),
        "--part",                   str(part),
    ]
    print(f"[stage2a] Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    print(f"[stage2a] Exit code: {result.returncode}")

    output_csvs = list(Path(VALIDATION_OUTPUTS_DIR).glob("*.csv"))
    print(f"[stage2a] Generated {len(output_csvs)} per-feature CSV file(s) in '{VALIDATION_OUTPUTS_DIR}/'")
    for csv_path in output_csvs[:3]:
        print(f"  {csv_path.name}")

    return VALIDATION_OUTPUTS_DIR


def run_stage2b_rank():
    """
    Stage 2b: Judge and rank features using an LLM judge.

    Calls find_feat_stage2b_rank.py to evaluate each candidate feature's
    steered outputs and select the top-k features per strategy.

    Returns:
        Path to the selected features CSV file.
    """
    print("\n" + "="*60)
    print("STAGE 2b: Judge and Rank Features")
    print("="*60)

    cmd = [
        sys.executable, "find_feat_stage2b_rank.py",
        "--validation_outputs_dir",  VALIDATION_OUTPUTS_DIR,
        "--candidate_features_path", CANDIDATE_FEATURES_PATH,
        "--output_path",             SELECTED_FEATURES_PATH,
        "--judge_model",             JUDGE_MODEL,
        "--top_k",                   str(TOP_K),
    ]
    print(f"[stage2b] Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    print(f"[stage2b] Exit code: {result.returncode}")

    if os.path.exists(SELECTED_FEATURES_PATH):
        df = pd.read_csv(SELECTED_FEATURES_PATH)
        print(f"[stage2b] Selected features saved to '{SELECTED_FEATURES_PATH}':")
        print(df.to_string(index=False))
    else:
        print("[stage2b] WARNING: Selected features file not found.")

    return SELECTED_FEATURES_PATH


def load_and_inspect_candidate_features(path: str):
    """
    Helper: Load and display the candidate features pickle.

    Args:
        path: Path to candidate_features.pkl

    Returns:
        List of (feature_idx, strategy_name) tuples.
    """
    if not os.path.exists(path):
        print(f"[inspect] File not found: {path}")
        return []

    with open(path, "rb") as f:
        candidates = pickle.load(f)

    print(f"\n[inspect] Loaded {len(candidates)} candidate features from '{path}':")
    strategies = {}
    for feat_idx, strategy in candidates:
        strategies.setdefault(strategy, []).append(feat_idx)

    for strategy, indices in strategies.items():
        print(f"  Strategy '{strategy}': {len(indices)} candidates — e.g. {indices[:3]}")

    return candidates


def load_and_inspect_selected_features(path: str):
    """
    Helper: Load and display the selected features CSV.

    Args:
        path: Path to selected_features.csv

    Returns:
        pandas DataFrame with selected feature rows.
    """
    if not os.path.exists(path):
        print(f"[inspect] File not found: {path}")
        return None

    df = pd.read_csv(path)
    print(f"\n[inspect] Selected features from '{path}':")
    print(df.to_string(index=False))
    return df


def use_preidentified_features(model_name: str = "r1_llama"):
    """
    Demonstrates loading the pre-identified features bundled with the repo,
    which can be used directly without running the identification pipeline.

    Args:
        model_name: One of 'r1_llama' or 'qwen3'.

    Returns:
        pandas DataFrame with the pre-identified selected features.
    """
    feature_files = {
        "r1_llama": f"{DATASET_DIR}/selected_features_r1_llama.csv",
        "qwen3":    f"{DATASET_DIR}/selected_features_qwen3.csv",
    }

    if model_name not in feature_files:
        raise ValueError(f"Unknown model_name '{model_name}'. Choose from: {list(feature_files.keys())}")

    path = feature_files[model_name]
    print(f"\n[preidentified] Loading pre-identified features for model='{model_name}' from '{path}'")

    if not os.path.exists(path):
        print(f"[preidentified] File not found: '{path}'. Make sure you are running from the repo root.")
        return None

    df = pd.read_csv(path)
    print(f"[preidentified] Loaded {len(df)} feature entries:")
    print(df.to_string(index=False))
    return df


def main():
    """
    Full feature identification pipeline demo.
    Runs Stage 1 → Stage 2a → Stage 2b in sequence.
    """
    print("SAE-Steering: Feature Identification Pipeline")
    print("=" * 60)
    print(f"  Model path : {MODEL_PATH}")
    print(f"  SAE path   : {SAE_PATH}")
    print(f"  Output dir : {OUTPUT_DIR}")
    print()

    # --- Check that repo scripts exist (sanity check) ---
    required_scripts = [
        "find_feat_stage1_logit_recall.py",
        "find_feat_stage2a_steer_validation.py",
        "find_feat_stage2b_rank.py",
    ]
    for script in required_scripts:
        if not os.path.exists(script):
            print(f"[ERROR] Required script not found: '{script}'")
            print("        Please run this script from the SAE-Steering repository root.")
            sys.exit(1)

    # --- Step 0: Ensure output directories exist ---
    ensure_dirs()

    # --- OPTION A: Use pre-identified features (fast path) ---
    print("\n[OPTION A] Loading pre-identified features (no pipeline needed):")
    preidentified = use_preidentified_features("r1_llama")

    # --- OPTION B: Run full identification pipeline ---
    print("\n[OPTION B] Running full feature identification pipeline:")
    print("  (Requires MODEL_PATH and SAE_PATH to be set correctly)")

    # Uncomment the lines below to actually run the pipeline:
    # candidate_path = run_stage1_logit_recall()
    # load_and_inspect_candidate_features(candidate_path)
    # validation_dir = run_stage2a_steer_validation(total_parts=1, part=0)
    # selected_path  = run_stage2b_rank()
    # load_and_inspect_selected_features(selected_path)

    print("\n[main] Done. To run the full pipeline, uncomment the lines in OPTION B.")
    print("[main] Next step: use selected features with eval_step2_generate_steering.py")


if __name__ == "__main__":
    main()

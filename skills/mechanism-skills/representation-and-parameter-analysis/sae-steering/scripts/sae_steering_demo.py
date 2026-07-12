#!/usr/bin/env python3
"""
SAE-Steering Demo Script
========================
Demonstrates how to use the SAE-Steering pipeline for controllable LLM reasoning.

This script shows:
1. How to run the full feature-identification pipeline (stages 1, 2a, 2b)
2. How to run the evaluation pipeline (steps 1, 2, 3)
3. How to work with pre-identified features for direct steering

Requirements:
    pip install -r requirements.txt  (from the SAE-Steering repository)

Usage:
    python sae_steering_demo.py --mode find_features   # Feature identification pipeline
    python sae_steering_demo.py --mode evaluate        # Evaluation pipeline
    python sae_steering_demo.py --mode judge_demo      # Single judge demo

Note:
    - Replace MODEL_PATH and SAE_PATH with actual paths to your model/SAE checkpoints.
    - The AIME/GPQA datasets are included in the `dataset/` folder of the repository.
    - API credentials must be set in sae_utils.py before running judging steps.
"""

import os
import sys
import argparse
import subprocess
import pickle
import csv
from pathlib import Path
from typing import List, Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Configuration — update these paths before running
# ─────────────────────────────────────────────────────────────────────────────

# Path to the SAE-Steering repository root
REPO_ROOT = Path(".")  # Change to the actual repo root if running from elsewhere

# Model and SAE checkpoint paths
MODEL_PATH = "/path/to/DeepSeek-R1-Distill-Llama-8B"   # Replace with actual path
SAE_PATH   = "/path/to/sae_checkpoint"                   # Replace with actual path

# Dataset paths (relative to REPO_ROOT)
AIME_VALIDATION = REPO_ROOT / "dataset" / "aime_his_50.csv"
AIME_TEST       = REPO_ROOT / "dataset" / "aime_test.csv"
GPQA_TEST       = REPO_ROOT / "dataset" / "gpqa_test.csv"

# Pre-identified features (ships with the repo)
SELECTED_FEATURES_R1_LLAMA = REPO_ROOT / "dataset" / "selected_features_r1_llama.csv"
SELECTED_FEATURES_QWEN3    = REPO_ROOT / "dataset" / "selected_features_qwen3.csv"

# Output directories
OUTPUT_DIR        = REPO_ROOT / "eval_outputs"
STEERED_DIR       = OUTPUT_DIR / "aime_steered"
JUDGED_DIR        = OUTPUT_DIR / "aime_judged"
VALIDATION_OUTDIR = REPO_ROOT / "validation_outputs"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: run a subprocess command and stream its output
# ─────────────────────────────────────────────────────────────────────────────

def run_command(cmd: List[str], description: str = "") -> int:
    """
    Run a shell command as a subprocess and stream stdout/stderr.

    Args:
        cmd:         List of command tokens (argv-style).
        description: Human-readable label for logging.

    Returns:
        Return code of the subprocess (0 = success).
    """
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print(f"{'='*60}")
    print(f"CMD: {' '.join(str(c) for c in cmd)}\n")

    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"[ERROR] Command returned exit code {result.returncode}")
    return result.returncode


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline A: Feature Identification  (Stages 1 → 2a → 2b)
# ─────────────────────────────────────────────────────────────────────────────

def run_stage1_logit_recall(
    model_path: str,
    sae_path: str,
    output_path: str = "candidate_features.pkl",
) -> int:
    """
    Stage 1 — Logit-Based Recall.

    Computes the logit contribution of every SAE feature and keeps only those
    that amplify at least one strategy-specific keyword's logit.

    Args:
        model_path:  Path to the language model checkpoint directory.
        sae_path:    Path to the SAE checkpoint directory / file.
        output_path: Where to save the candidate features pickle file.
                     Format: list of (feature_idx: int, strategy_name: str) tuples.

    Returns:
        Subprocess return code.  0 = success.

    Output:
        ``candidate_features.pkl`` — ~100 (feature_idx, strategy_name) pairs.
    """
    cmd = [
        sys.executable,
        str(REPO_ROOT / "find_feat_stage1_logit_recall.py"),
        "--model_path",  model_path,
        "--sae_path",    sae_path,
        "--output_path", output_path,
    ]
    return run_command(cmd, "Stage 1: Logit-Based Feature Recall")


def run_stage2a_steer_validation(
    model_path: str,
    sae_path: str,
    candidate_features_path: str,
    validation_set_path: str,
    output_dir: str,
    total_parts: int = 1,
    part: int = 0,
) -> int:
    """
    Stage 2a — Generate Steered Outputs on the Validation Set.

    For every candidate feature, steers the model and saves outputs.
    Supports sharding via ``total_parts`` / ``part`` for parallel jobs.

    Args:
        model_path:              Path to the language model checkpoint.
        sae_path:                Path to the SAE checkpoint.
        candidate_features_path: Path to the pickle produced by Stage 1.
        validation_set_path:     Path to the validation CSV (e.g. aime_his_50.csv).
        output_dir:              Directory to write per-feature CSV files.
        total_parts:             Total number of parallel shards (default 1 = no sharding).
        part:                    0-indexed shard index for this job.

    Returns:
        Subprocess return code.  0 = success.

    Output:
        ``{output_dir}/{feature_idx}.csv`` — one file per candidate feature.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "find_feat_stage2a_steer_validation.py"),
        "--model_path",              model_path,
        "--sae_path",                sae_path,
        "--candidate_features_path", candidate_features_path,
        "--validation_set_path",     validation_set_path,
        "--output_dir",              output_dir,
        "--total_parts",             str(total_parts),
        "--part",                    str(part),
    ]
    return run_command(cmd, f"Stage 2a: Steer Validation Set (shard {part}/{total_parts})")


def run_stage2b_rank_features(
    validation_outputs_dir: str,
    candidate_features_path: str,
    output_path: str = "selected_features.csv",
    judge_model: str = "gpt-4o",
    top_k: int = 3,
) -> int:
    """
    Stage 2b — Judge and Rank Candidate Features.

    Calls an LLM judge to score each steered output, then selects the top-k
    features per reasoning strategy.

    Args:
        validation_outputs_dir:  Directory containing per-feature CSVs from Stage 2a.
        candidate_features_path: Path to the pickle from Stage 1.
        output_path:             Where to save the selected features CSV.
        judge_model:             LLM judge model identifier (e.g. "gpt-4o").
        top_k:                   Number of top features to keep per strategy.

    Returns:
        Subprocess return code.  0 = success.

    Output:
        ``selected_features.csv`` — top-k features per strategy (feature_idx, strategy).
    """
    cmd = [
        sys.executable,
        str(REPO_ROOT / "find_feat_stage2b_rank.py"),
        "--validation_outputs_dir",  validation_outputs_dir,
        "--candidate_features_path", candidate_features_path,
        "--output_path",             output_path,
        "--judge_model",             judge_model,
        "--top_k",                   str(top_k),
    ]
    return run_command(cmd, "Stage 2b: Judge and Rank Features")


def run_feature_identification_pipeline(
    model_path: str,
    sae_path: str,
    parallel_parts: int = 1,
) -> None:
    """
    Run the complete feature-identification pipeline end-to-end.

    Executes:
        Stage 1  → ``candidate_features.pkl``
        Stage 2a → ``validation_outputs/{feature_idx}.csv``
        Stage 2b → ``selected_features.csv``

    Args:
        model_path:     Path to the LLM checkpoint.
        sae_path:       Path to the SAE checkpoint.
        parallel_parts: Number of parallel shards for Stage 2a.  Set >1 to
                        generate the Stage 2a commands for manual distribution
                        (this function runs only shard 0 when parallel_parts>1).
    """
    print("\n" + "="*70)
    print("  SAE-Steering: Feature Identification Pipeline")
    print("="*70)

    candidate_pkl    = "candidate_features.pkl"
    val_outputs_dir  = str(VALIDATION_OUTDIR)
    selected_csv     = "selected_features.csv"

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    rc = run_stage1_logit_recall(model_path, sae_path, candidate_pkl)
    if rc != 0:
        print("[ABORT] Stage 1 failed.")
        return

    # ── Stage 2a ─────────────────────────────────────────────────────────────
    if parallel_parts > 1:
        print(f"\n[INFO] parallel_parts={parallel_parts}: running shard 0 only.")
        print("       Launch the remaining shards manually, e.g.:")
        for p in range(1, parallel_parts):
            print(
                f"  python find_feat_stage2a_steer_validation.py "
                f"--model_path {model_path} --sae_path {sae_path} "
                f"--candidate_features_path {candidate_pkl} "
                f"--validation_set_path {AIME_VALIDATION} "
                f"--output_dir {val_outputs_dir} "
                f"--total_parts {parallel_parts} --part {p}"
            )

    rc = run_stage2a_steer_validation(
        model_path, sae_path, candidate_pkl,
        str(AIME_VALIDATION), val_outputs_dir,
        total_parts=parallel_parts, part=0,
    )
    if rc != 0:
        print("[ABORT] Stage 2a failed.")
        return

    # ── Stage 2b ─────────────────────────────────────────────────────────────
    rc = run_stage2b_rank_features(
        val_outputs_dir, candidate_pkl,
        selected_csv, judge_model="gpt-4o", top_k=3,
    )
    if rc != 0:
        print("[ABORT] Stage 2b failed.")
        return

    print(f"\n[DONE] Selected features saved to: {selected_csv}")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline B: Evaluation  (Steps 1 → 2 → 3)
# ─────────────────────────────────────────────────────────────────────────────

def run_eval_step1_no_steering(
    model_path: str,
    sae_path: str,
    test_set_path: str,
    output_path: str,
) -> int:
    """
    Evaluation Step 1 — Generate No-Steering Baseline.

    For each test problem, constructs a continuation prompt by appending the
    model's initial answer and a "Wait" token, then generates a baseline
    continuation without any SAE steering.

    Args:
        model_path:    Path to the LLM checkpoint.
        sae_path:      Path to the SAE checkpoint.
        test_set_path: Path to the test CSV (must include an ``answer`` column
                       with initial model responses).
        output_path:   Where to save the baseline outputs CSV.

    Returns:
        Subprocess return code.  0 = success.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "eval_step1_generate_no_steering.py"),
        "--model_path",    model_path,
        "--sae_path",      sae_path,
        "--test_set_path", test_set_path,
        "--output_path",   output_path,
    ]
    return run_command(cmd, "Eval Step 1: No-Steering Baseline Generation")


def run_eval_step2_steering(
    model_path: str,
    sae_path: str,
    no_steering_path: str,
    feature_idx: int,
    output_path: str,
) -> int:
    """
    Evaluation Step 2 — Generate Steered Outputs for One Feature.

    Runs the model with SAE steering enabled for the given feature index on
    all rows of the no-steering baseline CSV.

    Args:
        model_path:        Path to the LLM checkpoint.
        sae_path:          Path to the SAE checkpoint.
        no_steering_path:  Path to the baseline CSV from Step 1.
        feature_idx:       SAE feature index to use as the control vector.
        output_path:       Where to save the steered outputs CSV.

    Returns:
        Subprocess return code.  0 = success.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "eval_step2_generate_steering.py"),
        "--model_path",       model_path,
        "--sae_path",         sae_path,
        "--no_steering_path", no_steering_path,
        "--feature_idx",      str(feature_idx),
        "--output_path",      output_path,
    ]
    return run_command(cmd, f"Eval Step 2: Steered Generation (feature {feature_idx})")


def run_eval_step3_judge(
    steered_path: str,
    strategy: str,
    output_path: str,
) -> int:
    """
    Evaluation Step 3 — Judge Control Effectiveness with LLM Judges.

    Evaluates each steered output using majority vote across three LLM judges
    (GPT-4o, Gemini-2.5-Flash, DeepSeek-V3) and prints the overall control
    effectiveness score.

    Args:
        steered_path: Path to the steered outputs CSV from Step 2.
        strategy:     Name of the reasoning strategy being tested
                      (e.g. "Problem Understanding", "Backtracking").
        output_path:  Where to save per-row judge results CSV.

    Returns:
        Subprocess return code.  0 = success.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "eval_step3_judge.py"),
        "--steered_path", steered_path,
        "--strategy",     strategy,
        "--output_path",  output_path,
    ]
    return run_command(cmd, f"Eval Step 3: LLM Judge — strategy='{strategy}'")


def load_selected_features(features_csv: str) -> List[Tuple[int, str]]:
    """
    Load selected features from a CSV file.

    Expected CSV format: two columns — ``feature_idx`` (int) and
    ``strategy`` (str), with a header row.

    Args:
        features_csv: Path to the selected features CSV file.

    Returns:
        List of (feature_idx, strategy_name) tuples.

    Example:
        >>> features = load_selected_features("dataset/selected_features_r1_llama.csv")
        >>> for idx, strategy in features:
        ...     print(f"Feature {idx}: {strategy}")
        Feature 25475: Problem Understanding
        Feature 12345: Backtracking
    """
    features = []
    with open(features_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            features.append((int(row["feature_idx"]), row["strategy"]))
    return features


def run_evaluation_pipeline(
    model_path: str,
    sae_path: str,
    test_set: str = "aime",
    selected_features_csv: Optional[str] = None,
) -> None:
    """
    Run the complete evaluation pipeline using pre-identified features.

    Executes:
        Step 1 → baseline CSV (no steering)
        Step 2 → steered CSV per feature
        Step 3 → judge results CSV per feature + prints control effectiveness

    Args:
        model_path:            Path to the LLM checkpoint.
        sae_path:              Path to the SAE checkpoint.
        test_set:              Which dataset to use: "aime" or "gpqa".
        selected_features_csv: Path to the features CSV.  Defaults to the
                               R1-Llama pre-identified features.
    """
    print("\n" + "="*70)
    print("  SAE-Steering: Evaluation Pipeline")
    print("="*70)

    # Resolve paths
    if test_set == "aime":
        test_csv = str(AIME_TEST)
    elif test_set == "gpqa
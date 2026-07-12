#!/usr/bin/env python3
"""
SAE-Steering: Feature Identification Pipeline Demo

This script demonstrates how to run the full SAE-Steering feature identification
pipeline programmatically, covering:
  - Stage 1: Logit-based recall of candidate features
  - Stage 2a: Generating steered validation outputs per candidate
  - Stage 2b: LLM judging and ranking to select top-k features

Prerequisites:
    pip install -r requirements.txt

    Set your LLM judge API credentials in sae_utils.py:
        client = OpenAI(
            base_url="your_api_base_url",
            api_key="your_api_key",
        )

Usage:
    python run_feature_identification.py \
        --model_path /path/to/deepseek-r1-distill-llama-8b \
        --sae_path /path/to/sae_checkpoint \
        --output_dir ./feature_id_outputs \
        --judge_model gpt-4o \
        --top_k 3

Note:
    This script demonstrates the pipeline structure. The actual SAE and model
    loading is handled by the repository's sae_utils.py and the individual stage
    scripts. Replace placeholder paths with real model/SAE checkpoints.
"""

import argparse
import os
import pickle
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def run_stage1_logit_recall(
    model_path: str,
    sae_path: str,
    output_path: str,
) -> bool:
    """
    Run Stage 1: Logit-based recall of strategy-specific SAE features.

    Computes logit contributions of all SAE features and recalls those
    that amplify strategy keyword logits. Produces ~100 candidate
    (feature_idx, strategy_name) pairs.

    Args:
        model_path: Path to the LLM checkpoint (HuggingFace format).
        sae_path: Path to the SAE checkpoint.
        output_path: Output path for candidate_features.pkl.

    Returns:
        True if the stage completed successfully, False otherwise.
    """
    print(f"[Stage 1] Running logit-based recall...")
    print(f"  model_path: {model_path}")
    print(f"  sae_path:   {sae_path}")
    print(f"  output:     {output_path}")

    cmd = [
        sys.executable,
        "find_feat_stage1_logit_recall.py",
        "--model_path", model_path,
        "--sae_path", sae_path,
        "--output_path", output_path,
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"[Stage 1] Completed. Candidates saved to: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Stage 1] FAILED with return code {e.returncode}")
        return False


def run_stage2a_steer_validation(
    model_path: str,
    sae_path: str,
    candidate_features_path: str,
    validation_set_path: str,
    output_dir: str,
    total_parts: int = 1,
    part: int = 0,
) -> bool:
    """
    Run Stage 2a: Generate steered outputs on the validation set for each candidate.

    For each candidate feature, steers the model on the validation set and
    saves the outputs as one CSV per feature: output_dir/{feature_idx}.csv.

    Supports parallelization via total_parts / part arguments.

    Args:
        model_path: Path to the LLM checkpoint.
        sae_path: Path to the SAE checkpoint.
        candidate_features_path: Path to candidate_features.pkl from Stage 1.
        validation_set_path: Path to the validation CSV (e.g., dataset/aime_his_50.csv).
        output_dir: Directory to save per-feature output CSVs.
        total_parts: Total number of parallel jobs (default: 1 = no parallelism).
        part: Index of this job (0-indexed, default: 0).

    Returns:
        True if the stage completed successfully, False otherwise.
    """
    print(f"[Stage 2a] Generating steered validation outputs (part {part}/{total_parts})...")
    print(f"  candidates:     {candidate_features_path}")
    print(f"  validation_set: {validation_set_path}")
    print(f"  output_dir:     {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sys.executable,
        "find_feat_stage2a_steer_validation.py",
        "--model_path", model_path,
        "--sae_path", sae_path,
        "--candidate_features_path", candidate_features_path,
        "--validation_set_path", validation_set_path,
        "--output_dir", output_dir,
        "--total_parts", str(total_parts),
        "--part", str(part),
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"[Stage 2a] Completed. Per-feature CSVs in: {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Stage 2a] FAILED with return code {e.returncode}")
        return False


def run_stage2b_rank(
    validation_outputs_dir: str,
    candidate_features_path: str,
    output_path: str,
    judge_model: str = "gpt-4o",
    top_k: int = 3,
) -> bool:
    """
    Run Stage 2b: LLM judging and ranking of candidate features.

    Calls the configured LLM judge to evaluate each steered output CSV,
    then selects the top-k features per strategy.

    Args:
        validation_outputs_dir: Directory containing per-feature CSVs from Stage 2a.
        candidate_features_path: Path to candidate_features.pkl from Stage 1.
        output_path: Output path for selected_features.csv.
        judge_model: LLM judge model name (e.g., "gpt-4o").
        top_k: Number of top features to select per strategy (default: 3).

    Returns:
        True if the stage completed successfully, False otherwise.
    """
    print(f"[Stage 2b] Judging and ranking features with {judge_model}...")
    print(f"  validation_outputs_dir: {validation_outputs_dir}")
    print(f"  output:                 {output_path}")
    print(f"  top_k:                  {top_k}")

    cmd = [
        sys.executable,
        "find_feat_stage2b_rank.py",
        "--validation_outputs_dir", validation_outputs_dir,
        "--candidate_features_path", candidate_features_path,
        "--output_path", output_path,
        "--judge_model", judge_model,
        "--top_k", str(top_k),
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"[Stage 2b] Completed. Selected features saved to: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Stage 2b] FAILED with return code {e.returncode}")
        return False


def load_candidate_features(path: str) -> Optional[List[Tuple[int, str]]]:
    """
    Load candidate features from a pickle file produced by Stage 1.

    Args:
        path: Path to candidate_features.pkl.

    Returns:
        List of (feature_idx, strategy_name) tuples, or None if loading fails.
    """
    try:
        with open(path, "rb") as f:
            candidates = pickle.load(f)
        print(f"Loaded {len(candidates)} candidate features from {path}")
        # Show a sample
        for idx, (feat_idx, strategy) in enumerate(candidates[:5]):
            print(f"  [{idx}] feature_idx={feat_idx}, strategy='{strategy}'")
        if len(candidates) > 5:
            print(f"  ... and {len(candidates) - 5} more")
        return candidates
    except FileNotFoundError:
        print(f"ERROR: Candidate features file not found: {path}")
        return None
    except Exception as e:
        print(f"ERROR loading candidates: {e}")
        return None


def run_full_pipeline(
    model_path: str,
    sae_path: str,
    output_dir: str,
    validation_set_path: str = "dataset/aime_his_50.csv",
    judge_model: str = "gpt-4o",
    top_k: int = 3,
    n_parallel_jobs: int = 1,
) -> None:
    """
    Run the complete SAE-Steering feature identification pipeline.

    Executes Stage 1 → Stage 2a → Stage 2b in sequence, using outputs
    from each prior stage as inputs for the next.

    Args:
        model_path: Path to the LLM checkpoint.
        sae_path: Path to the SAE checkpoint.
        output_dir: Root directory for all intermediate and final outputs.
        validation_set_path: Path to the validation CSV.
        judge_model: LLM judge model identifier.
        top_k: Number of top features to select per strategy.
        n_parallel_jobs: If > 1, prints instructions for parallel Stage 2a jobs
                         but only runs part 0 directly.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate_features_path = str(output_dir / "candidate_features.pkl")
    validation_outputs_dir = str(output_dir / "validation_outputs")
    selected_features_path = str(output_dir / "selected_features.csv")

    print("=" * 60)
    print("SAE-Steering Feature Identification Pipeline")
    print("=" * 60)
    print(f"Model:      {model_path}")
    print(f"SAE:        {sae_path}")
    print(f"Output dir: {output_dir}")
    print()

    # --- Stage 1 ---
    if not run_stage1_logit_recall(model_path, sae_path, candidate_features_path):
        print("Pipeline aborted at Stage 1.")
        return

    # Show what we found
    candidates = load_candidate_features(candidate_features_path)
    if candidates is None:
        print("Pipeline aborted: could not load candidate features.")
        return

    # --- Stage 2a ---
    if n_parallel_jobs > 1:
        print(f"\n[Stage 2a] NOTE: Running only part 0/{n_parallel_jobs} here.")
        print("  To parallelize, run the following in separate jobs:")
        for part_i in range(n_parallel_jobs):
            print(
                f"    python find_feat_stage2a_steer_validation.py "
                f"--model_path {model_path} "
                f"--sae_path {sae_path} "
                f"--candidate_features_path {candidate_features_path} "
                f"--validation_set_path {validation_set_path} "
                f"--output_dir {validation_outputs_dir} "
                f"--total_parts {n_parallel_jobs} --part {part_i}"
            )
        # Run just part 0 for demo
        if not run_stage2a_steer_validation(
            model_path, sae_path, candidate_features_path,
            validation_set_path, validation_outputs_dir,
            total_parts=n_parallel_jobs, part=0,
        ):
            print("Pipeline aborted at Stage 2a.")
            return
    else:
        if not run_stage2a_steer_validation(
            model_path, sae_path, candidate_features_path,
            validation_set_path, validation_outputs_dir,
        ):
            print("Pipeline aborted at Stage 2a.")
            return

    # --- Stage 2b ---
    if not run_stage2b_rank(
        validation_outputs_dir, candidate_features_path,
        selected_features_path, judge_model=judge_model, top_k=top_k,
    ):
        print("Pipeline aborted at Stage 2b.")
        return

    print()
    print("=" * 60)
    print("Feature identification pipeline complete!")
    print(f"Selected features saved to: {selected_features_path}")
    print("Use this CSV directly as control vectors in the evaluation pipeline.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="SAE-Steering Feature Identification Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model_path", type=str, required=True,
        help="Path to the LLM checkpoint (HuggingFace format).",
    )
    parser.add_argument(
        "--sae_path", type=str, required=True,
        help="Path to the SAE checkpoint.",
    )
    parser.add_argument(
        "--output_dir", type=str, default="./feature_id_outputs",
        help="Root directory for all pipeline outputs.",
    )
    parser.add_argument(
        "--validation_set_path", type=str, default="dataset/aime_his_50.csv",
        help="Path to the validation CSV.",
    )
    parser.add_argument(
        "--judge_model", type=str, default="gpt-4o",
        help="LLM judge model name.",
    )
    parser.add_argument(
        "--top_k", type=int, default=3,
        help="Number of top features to select per strategy.",
    )
    parser.add_argument(
        "--n_parallel_jobs", type=int, default=1,
        help="Number of parallel jobs for Stage 2a (only runs part 0 in this script).",
    )

    args = parser.parse_args()

    run_full_pipeline(
        model_path=args.model_path,
        sae_path=args.sae_path,
        output_dir=args.output_dir,
        validation_set_path=args.validation_set_path,
        judge_model=args.judge_model,
        top_k=args.top_k,
        n_parallel_jobs=args.n_parallel_jobs,
    )


if __name__ == "__main__":
    main()

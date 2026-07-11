#!/usr/bin/env python3
"""
Programmatic usage example for ICA Lens artifact variant selection.

This script demonstrates actual Python API usage from `scripts.fetch_artifacts`
by calling the helper function:

    _with_database_variant(artifact_set, variant: str)

The example uses a small in-memory artifact manifest to show how an agent can
select the "mini" or "full" database view without invoking the full download
workflow.

Run from the repository root after dependencies are installed:

    uv sync
    uv run python scripts/artifact_variant_example.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def ensure_repo_root_on_path() -> Path:
    """
    Ensure repository-local Python modules can be imported.

    Returns:
        The resolved repository root path.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def import_variant_helper():
    """
    Import the artifact variant helper from the repository.

    Returns:
        The `_with_database_variant` function.

    Raises:
        RuntimeError: If import fails.
    """
    try:
        from scripts.fetch_artifacts import _with_database_variant
    except Exception as exc:
        raise RuntimeError(
            f"Failed to import `_with_database_variant` from `scripts.fetch_artifacts`: {exc}"
        ) from exc
    return _with_database_variant


def build_sample_artifact_set() -> dict[str, Any]:
    """
    Build a minimal artifact set structure for demonstration.

    Returns:
        A dictionary containing sample models and database variants.
    """
    return {
        "models": [
            {"name": "gpt2", "path": "artifacts/fetched/models/gpt2/"},
            {"name": "gemma2_2b", "path": "artifacts/fetched/models/gemma2_2b/"},
            {"name": "qwen3_5_2b_base", "path": "artifacts/fetched/models/qwen3_5_2b_base/"},
        ],
        "databases": {
            "mini": {
                "name": "ica_probe_mini.sqlite",
                "path": "artifacts/fetched/databases/ica_probe_mini.sqlite",
            },
            "full": {
                "name": "ica_probe_full.sqlite",
                "path": "artifacts/fetched/databases/ica_probe_full.sqlite",
            },
        },
    }


def try_variant(helper, artifact_set: dict[str, Any], variant: str) -> None:
    """
    Apply a requested database variant and print the resulting structure.

    Args:
        helper: Imported `_with_database_variant` function.
        artifact_set: Artifact manifest-like structure.
        variant: Variant name such as "mini" or "full".
    """
    try:
        result = helper(artifact_set, variant)
    except Exception as exc:
        print(f"[{variant}] helper raised an exception: {exc}")
        return

    print(f"\nVariant: {variant}")
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> int:
    """
    Run the artifact variant selection example.

    Returns:
        Exit code integer.
    """
    repo_root = ensure_repo_root_on_path()
    print(f"Repository root: {repo_root}")

    helper = import_variant_helper()
    artifact_set = build_sample_artifact_set()

    print("Original sample artifact set:")
    print(json.dumps(artifact_set, indent=2, sort_keys=True))

    for variant in ("mini", "full"):
        try_variant(helper, artifact_set, variant)

    print("\nExample completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

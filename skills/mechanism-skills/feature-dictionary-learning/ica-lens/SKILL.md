---
name: ica-lens
description: Use this skill when applying Independent Component Analysis as a training-free interpretability lens — decomposing a target activation site (residual stream, MLP output, attention-head output, or any cached hook point) into maximally non-Gaussian directions and treating each direction as a candidate monosemantic component for sparse-probing, targeted perturbation, annotation, and cross-comparison against trained SAE / transcoder / crosscoder features.
---

# ICA Lens: A Training-Free Interpretability Lens on Model Components

## When to Use

Activate this skill when the goal is to **characterise the interpretable structure of a component's activation distribution without paying the up-front cost of training a sparse dictionary**.

Typical triggers:

- A new model, layer, or hook point needs an initial inventory of candidate interpretable directions before committing to SAE / transcoder training.
- An existing SAE / transcoder feature set needs an *independent* baseline of interpretable directions to compare against (overlap, coverage, perturbation strength, sparse-probe accuracy under a matched budget).
- A specific concept or behaviour is suspected to live on a low-dimensional, non-Gaussian subspace of a residual / MLP / head-output state, and a fast, gradient-free extractor is needed to expose it.
- A study of *non-Gaussianity* itself — where interpretable structure concentrates across depth, modality, and model family — is the object of interest.
- Targeted perturbation / steering needs a direction handle whose discovery is decoupled from the model's training signal.
- An interpretability artefact needs to be browsed, annotated, or shared via an explorer UI rather than recomputed each session.

**Keywords:** ICA, Independent Component Analysis, FastICA, non-Gaussianity, dictionary-free interpretability, interpretable directions, component interpretability, residual-stream directions, MLP-output directions, attention-head directions, sparse probing, targeted probe perturbation, SAE alternative, SAE baseline, ICA explorer.

## Method in One Paragraph

The ICA Lens treats each cached activation $\mathbf{a} \in \mathbb{R}^{d_{\text{model}}}$ at a chosen hook point as a sample from an unknown source distribution and fits an unmixing matrix $\mathbf{W}_{\mathrm{ICA}}$ such that the components $\mathbf{f}(\mathbf{a}) = \mathbf{W}_{\mathrm{ICA}}\,\mathbf{a}$ are *maximally non-Gaussian* and mutually independent. The motivating observation is that **interpretable, token-selective directions in language models appear systematically less Gaussian than random directions in the same space**, so non-Gaussianity is a sufficient surrogate objective to recover candidate monosemantic axes without any reconstruction or sparsity loss. Compared with sparse-autoencoder-family methods, no over-complete dictionary is trained, no per-feature dead-direction / split-feature pathology is incurred, and the recovered directions can be evaluated by exactly the same downstream protocols — sparse probing, targeted probe perturbation, top-activating example mining, and feature dashboards.

## When to Prefer ICA Lens Over a Trained Dictionary

| Situation | ICA Lens | SAE / Transcoder / Crosscoder |
|---|---|---|
| First-pass inventory on a new site / model | preferred | overkill |
| Budget-constrained perturbation study | preferred (better TPP under budget) | weaker under matched budget |
| Need an independent baseline to score a learned dictionary against | preferred | the object under test |
| Need *more directions* than the activation has dimensions (over-complete) | not applicable (ICA returns $\le d_{\text{model}}$ components) | preferred |
| Need explicit input → output feature mapping for circuit replacement | not applicable | transcoder preferred |
| Need cross-site / cross-checkpoint shared basis | not applicable | crosscoder preferred |

The general rule: **start with ICA Lens, escalate to a learned dictionary only when ICA's resolution, over-completeness, or circuit-replacement guarantees are demonstrably insufficient.**

## Quick Reference

- **Repository:** https://github.com/liusida/ica-lens-paper
- **Paper:** https://arxiv.org/abs/2606.11722
- **Project page:** https://liusida.github.io/ica-lens-paper/
- **Hugging Face Space (hosted explorer):** https://huggingface.co/spaces/EEEAILab/ICAExplorer
- **Hugging Face artifacts dataset:** https://huggingface.co/datasets/sida/ica-lens-paper
- **Docs:**
  - `docs/quickstart.md`
  - `docs/fit_one_layer_qwen36_27b.md` — worked example for fitting ICA on a *new* model / layer (use as template)
  - `docs/reproduction.md`
  - `docs/troubleshooting.md`
  - `docs/artifact_contract.md`, `docs/artifact_datasets.md`, `docs/model_and_layer_conventions.md`

## Installation / Setup

### Prerequisites
- Python 3.10+
- PyTorch (CUDA recommended for activation capture and ICA fitting)
- `uv` package manager
- FastAPI-based explorer

### Clone the repository (required first — all commands below assume the repo root as cwd)
```bash
git clone https://github.com/liusida/ica-lens-paper.git
cd ica-lens-paper
```

### Minimal install (any task)
```bash
uv sync
```

### Extra steps required for *any* SAEBench-touching evaluation (TPP, sparse probe, SAE-overlap)
```bash
git submodule update --init --recursive
bash scripts/setup_saebench_envs.sh
```

## The Four Things You Actually Do With This Skill

### 1. Browse pre-fitted ICA components in the explorer

The released artifacts ship with non-Gaussianity scores, top-activating contexts, ERF entries, and SAE-overlap annotations for GPT-2 Small, Gemma 2 2B, and Qwen 3.5 2B Base. This is the fastest way to *answer interpretability questions on those models* without re-fitting anything.

```bash
uv sync
uv run python scripts/fetch_artifacts.py --models --databases
uv run python scripts/verify_artifacts.py
uv run python -m server.app --port 8001
```

Switch to the full database when you need token-coloured context examples:

```bash
uv run python scripts/fetch_artifacts.py --models --databases --database-variant full
uv run python scripts/verify_artifacts.py --database-variant full
ICA_EXPLORER_DB_PATH=artifacts/fetched/databases/ica_probe_full.sqlite \
uv run python -m server.app --port 8001
```

### 2. Fit ICA on a *new* component (your own model, layer, or hook point)

This is the central reusable workflow. The recipe is the same regardless of model: capture activations at the target hook point, then fit FastICA on them. Use `docs/fit_one_layer_qwen36_27b.md` as a template — it documents the only place model-specific config matters.

```bash
# 1. Capture activations at the chosen hook point(s)
uv run python workflows/01_capture_activations.py \
    --config configs/activations/<your_model>.toml \
    --output-root results/<your_run>/activations \
    --include-embedding

# 2. Fit FastICA on the captured activations
uv run python workflows/02_fit_ica.py \
    --config configs/fit_ica/<your_model>.toml \
    --activation-root results/<your_run>/activations \
    --output-root results/<your_run>/ica
```

The TOML configs control:
- which hook points / layers are captured (`configs/activations/*.toml`)
- the token budget and FastICA hyperparameters (`configs/fit_ica/*.toml`)
- model-tokenizer wiring (`configs/models/*.toml`)

Author a new TOML pair by copying the closest released model's pair and editing the hook-point list.

### 3. Score the fitted components

Once ICA components exist, the same downstream protocols apply regardless of which model produced them.

```bash
# Non-Gaussianity diagnostics (per-direction interpretability prior)
uv run python workflows/03_compute_nongaussianity.py \
    --models <your_model> --token-budget 1000000 \
    --activation-root results/<your_run>/activations \
    --ica-root results/<your_run>/ica \
    --output-root results/<your_run>/nongaussianity

# Top-activating examples + explorer DB (for browsing / annotation)
uv run python workflows/04_build_explorer_db.py \
    --models <your_model> --token-budget 1000000 \
    --activation-root results/<your_run>/activations \
    --ica-root results/<your_run>/ica \
    --output-db results/<your_run>/databases/ica_probe.sqlite
uv run python workflows/05_populate_erf.py \
    --models <your_model> --token-budget 1000000 \
    --db-path results/<your_run>/databases/ica_probe.sqlite \
    --ica-root results/<your_run>/ica

# Component-level evaluation against trained SAE features
uv run python workflows/06_compare_ica_sae_overlap.py \
    --models <your_model> --token-budget 1000000 \
    --ica-root results/<your_run>/ica \
    --output-root results/<your_run>/ica_sae_overlap

# Targeted Probe Perturbation (TPP) — the headline SAEBench score
uv run python workflows/07_run_saebench_tpp.py \
    --model <your_model> --token-budget 1000000 \
    --ica-root results/<your_run>/ica

# Sparse probing — recoverability of labelled properties from ICA components
uv run python workflows/08_run_saebench_sparse_probe.py \
    --model <your_model> --token-budget 1000000 \
    --ica-root results/<your_run>/ica --methods all
```

Use these as *interpretability instruments*, not just as paper-reproduction commands: the per-direction non-Gaussianity score is a cheap prior on which components to inspect first; SAE overlap localises which learned dictionary atoms a given ICA direction stands in for; TPP and sparse probing quantify the direction's causal handle on labelled behaviour.

### 4. Inspect your own components in the explorer

The explorer reads any SQLite that follows the artifact contract, so you can point it at a self-fitted run while keeping released artifacts available for cross-comparison:

```bash
ICA_EXPLORER_DB_PATH=results/<your_run>/databases/ica_probe.sqlite \
ICA_EXPLORER_ICA_ROOT=results/<your_run>/ica \
uv run python -m server.app --port 8001
```

For a low-cost end-to-end dry run of the entire pipeline (capture → fit → score → explorer DB), use the demo orchestrator before committing GPU time:

```bash
uv run python scripts/reproduce_all.py --mode demo --clean --force --erf-limit 1
```

## Programmatic Surface

### Construct the FastAPI app in-process

```python
from server.app import create_app

app = create_app()                       # honours ICA_EXPLORER_* env vars
# mount, test with fastapi.testclient.TestClient, or inspect routes
```

See bundled `scripts/explorer_app_usage.py` for a runnable demonstration including OpenAPI inspection.

### Programmatic artifact-variant selection

```python
from scripts.fetch_artifacts import _with_database_variant

selected = _with_database_variant(artifact_set, "full")
```

See bundled `scripts/artifact_variant_example.py`.

## Key APIs / Surfaces

### Workflow entry points (the operational interface)

| Entry point | Component-interpretability role |
|---|---|
| `workflows/01_capture_activations.py` | Stream a chosen hook point's activations to disk |
| `workflows/02_fit_ica.py` | Recover non-Gaussian directions at that hook point |
| `workflows/03_compute_nongaussianity.py` | Rank directions by interpretability prior |
| `workflows/04_build_explorer_db.py` | Index top-activating contexts per direction |
| `workflows/05_populate_erf.py` | Attach example-receptive-field entries to each direction |
| `workflows/06_compare_ica_sae_overlap.py` | Cross-reference ICA directions with trained-SAE features |
| `workflows/07_run_saebench_tpp.py` | Causal-handle quality under a perturbation budget |
| `workflows/08_run_saebench_sparse_probe.py` | Labelled-property recoverability from ICA components |

### Core server / scripts surface

| Symbol | Module | Description |
|---|---|---|
| `create_app(settings)` | `server/app.py` | FastAPI factory for the explorer |
| `ProbeRequest`, `SaeProbeRequest`, `AnnotationUpdate` | `server/app.py` | Explorer request / annotation models |
| `_model_settings(app, model_name)` | `server/app.py` | Per-model settings resolver |
| `_raw_gpt2_block_index_for_probe(app, model_name, layer)` | `server/app.py` | Layer-id translator |
| `main(argv)`, `_with_database_variant(artifact_set, variant)` | `scripts/fetch_artifacts.py` | Artifact fetch + variant selection |
| `main(argv)`, `_filter_database_checksums(reports, variant)` | `scripts/verify_artifacts.py` | Artifact verification |
| `main(argv)`, `_run_step(report, name, cmd)`, `_clean_generated()` | `scripts/reproduce_all.py` | Pipeline orchestration |
| `main(argv)`, `_selected_models(args, demo_cfg)`, `_run_model_demo()` | `scripts/run_demo.py` | Demo runner |

### Environment variables

| Variable | Effect |
|---|---|
| `ICA_EXPLORER_DB_PATH` | Selects which SQLite the explorer reads |
| `ICA_EXPLORER_ICA_ROOT` | Selects which fitted ICA directory the explorer reads components from |

### Released artifacts (use as ready-made components for the three covered models)

| Model | Activations config | Fit-ICA config | Released artifact path |
|---|---|---|---|
| GPT-2 Small | `configs/activations/gpt2.toml` | `configs/fit_ica/gpt2.toml` | `artifacts/fetched/models/gpt2/` |
| Gemma 2 2B | `configs/activations/gemma2_2b.toml` | `configs/fit_ica/gemma2_2b.toml` | `artifacts/fetched/models/gemma2_2b/` |
| Qwen 3.5 2B Base | `configs/activations/qwen3_5_2b_base.toml` | `configs/fit_ica/qwen3_5_2b_base.toml` | `artifacts/fetched/models/qwen3_5_2b_base/` |
| Qwen3.6-27B | worked-example template — see `docs/fit_one_layer_qwen36_27b.md` | same | not pre-shipped |

For any other model, follow the Qwen3.6-27B doc as the template.

## Related Tools

ICA Lens sits inside the `feature-dictionary-learning` family as the **dictionary-free baseline**. Pair it with the other family members along a cost–fidelity gradient:

- **SAELens** (`../SAE/`) — when over-complete coverage and per-feature monosemanticity are required at the same site.
- **Transcoder circuits** (`../transcoder/`) — when an interpretable *input → output* mapping is needed to slot into circuit-replacement / attribution graphs.
- **Crosscoders** (`../crosscoder/`) — when a *shared* basis across layers or fine-tuning checkpoints is the object of interest.
- **SAEBench** (submodule, shared infrastructure) — supplies the TPP and sparse-probe evaluators used by `workflows/07` and `workflows/08`; ICA-Lens results report on the same axes that SAE / transcoder evaluations use, so cross-comparison is one-to-one.

## Common Patterns & Best Practices

1. **Pick the site before the method.** ICA's quality depends entirely on the activation distribution at the chosen hook point — residual stream, MLP output, attention-head output, post-LN, etc. Decide where the interpretability claim lives, then capture exactly that hook point.
2. **Always start from released artifacts** for GPT-2 / Gemma 2 2B / Qwen 3.5 2B Base; only re-fit when extending to a new model, layer, or hook point.
3. **Use non-Gaussianity as the first filter** when triaging hundreds of components — rank by `workflows/03` output before opening the explorer.
4. **Score ICA and any candidate SAE on the same protocol** (TPP, sparse probe, SAE overlap) before claiming one is "more interpretable" than the other.
5. **Mini DB by default** for exploration; full DB only when token-coloured contexts are needed.
6. **Demo before full reproduction** — `scripts/reproduce_all.py --mode demo` validates the orchestration end-to-end before committing GPU time.
7. **Config-driven everything** — for a new model / layer, copy and edit a TOML pair (`configs/activations/*.toml` + `configs/fit_ica/*.toml`) rather than passing flags.
8. **Respect output layout** — fetched data under `artifacts/fetched/`, generated data under `results/`; the explorer assumes this split.
9. **Use the env vars** (`ICA_EXPLORER_DB_PATH`, `ICA_EXPLORER_ICA_ROOT`) to mix released and self-fitted artifacts in one explorer instance.
10. **Don't claim circuit-level mechanism from ICA alone** — ICA produces correlated, non-causal directions. Promote a candidate to a causal claim with targeted perturbation (`workflows/07`) or by switching to a transcoder for replacement-context circuit work.

## Demo Scripts

### `scripts/explorer_app_usage.py`

```python
#!/usr/bin/env python3
"""
Programmatic usage example for the ICA Lens FastAPI explorer.

Demonstrates importing `create_app`, building the FastAPI app, inspecting
registered routes, and fetching the generated OpenAPI schema via TestClient.

    uv sync
    uv run python scripts/explorer_app_usage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from fastapi.testclient import TestClient
except ImportError as exc:
    raise SystemExit(
        "fastapi is required to run this example. "
        "Install project dependencies with `uv sync` first."
    ) from exc


def ensure_repo_root_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def build_app():
    from server.app import create_app
    return create_app()


def summarize_routes(app: Any) -> list[dict[str, Any]]:
    route_summaries: list[dict[str, Any]] = []
    for route in getattr(app, "routes", []):
        methods = sorted(getattr(route, "methods", []) or [])
        path = getattr(route, "path", "<unknown>")
        name = getattr(route, "name", "<unnamed>")
        route_summaries.append({"name": name, "path": path, "methods": methods})
    return route_summaries


def fetch_openapi_schema(app: Any) -> dict[str, Any]:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        response.raise_for_status()
        return response.json()


def main() -> int:
    repo_root = ensure_repo_root_on_path()
    print(f"Repository root: {repo_root}")
    app = build_app()
    print("FastAPI app created successfully.")
    routes = summarize_routes(app)
    print(f"Registered routes: {len(routes)}")
    schema = fetch_openapi_schema(app)
    print(f"OpenAPI path count: {len(schema.get('paths', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### `scripts/artifact_variant_example.py`

```python
#!/usr/bin/env python3
"""
Programmatic usage example for ICA Lens artifact variant selection.

Demonstrates `_with_database_variant(artifact_set, variant)` from
`scripts.fetch_artifacts`, used to switch a manifest between the mini and
full SQLite explorer databases without running the full download flow.

    uv sync
    uv run python scripts/artifact_variant_example.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def ensure_repo_root_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def build_sample_artifact_set() -> dict[str, Any]:
    return {
        "models": [
            {"name": "gpt2", "path": "artifacts/fetched/models/gpt2/"},
            {"name": "gemma2_2b", "path": "artifacts/fetched/models/gemma2_2b/"},
            {"name": "qwen3_5_2b_base", "path": "artifacts/fetched/models/qwen3_5_2b_base/"},
        ],
        "databases": {
            "mini": {"path": "artifacts/fetched/databases/ica_probe_mini.sqlite"},
            "full": {"path": "artifacts/fetched/databases/ica_probe_full.sqlite"},
        },
    }


def main() -> int:
    ensure_repo_root_on_path()
    from scripts.fetch_artifacts import _with_database_variant

    artifact_set = build_sample_artifact_set()
    for variant in ("mini", "full"):
        selected = _with_database_variant(artifact_set, variant)
        print(f"\nVariant: {variant}")
        print(json.dumps(selected, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Attribution

- Sida Liu — Independent Researcher — `me@liusida.com`
- Feijiang Han — University of Maryland — `feijhan@umd.edu`

License: MIT.

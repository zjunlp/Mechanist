# ICA Lens API Reference

## Overview

The `liusida/ica-lens-paper` repository is organized into four main packages:
- `src/ica_lens/` — Reusable library code (capture, fit, analysis primitives)
- `workflows/` — Numbered, config-driven workflow entry points (capture → fit → analysis)
- `scripts/` — Artifact fetching, verification, environment setup, demo orchestration
- `server/` — FastAPI explorer application and static UI

This reference documents the confirmed public surface available to agents. It mirrors the conventions used in the `transcoder/` API reference (module → class → method) and resolves uncertainty by pointing at the concrete source file when the published analysis does not expose signatures.

---

## Module: `server.app`

**File:** `server/app.py`

FastAPI explorer application and request models for browsing fitted ICA directions.

### Class: `ProbeRequest`

```python
class ProbeRequest
```

Request model used by ICA-direction probe endpoints in the explorer server.

**Field details:** inspect `server/app.py` directly for the Pydantic schema; field-level definitions are not enumerated in the provided analysis summary.

---

### Class: `SaeProbeRequest`

```python
class SaeProbeRequest
```

Request model used by SAE-comparison probe endpoints in the explorer server.

**Field details:** inspect `server/app.py` directly.

---

### Class: `AnnotationUpdate`

```python
class AnnotationUpdate
```

Update payload model for annotating fitted directions in the explorer database.

**Field details:** inspect `server/app.py` directly.

---

### Function: `create_app`

```python
create_app(settings: Settings | None) -> FastAPI
```

Factory that constructs the FastAPI explorer application.

**Parameters:**
- `settings` (`Settings | None`): Optional configuration object. When `None`, defaults are read from environment variables such as `ICA_EXPLORER_DB_PATH` and `ICA_EXPLORER_ICA_ROOT`.

**Returns:**
- A `FastAPI` application instance ready to be served by `uvicorn` or wired into tests.

**Example:**
```python
from server.app import create_app

app = create_app()
# routes are registered against the resolved Settings
```

**CLI-adjacent usage:**
```bash
uv run python -m server.app --port 8001
```

---

### Function: `_model_settings`

```python
_model_settings(app: FastAPI, model_name: str)
```

Internal helper that resolves model-specific settings from the FastAPI app state.

**Parameters:**
- `app` (`FastAPI`): The explorer application instance.
- `model_name` (`str`): A repository model identifier such as `gpt2`, `gemma2_2b`, or `qwen3_5_2b_base`.

---

### Function: `_raw_gpt2_block_index_for_probe`

```python
_raw_gpt2_block_index_for_probe(app: FastAPI, model_name: str, layer: str)
```

Translates a probe-layer designation to the raw GPT-2 block index expected by the explorer's probe APIs.

**Parameters:**
- `app` (`FastAPI`): The explorer application instance.
- `model_name` (`str`): Target model identifier.
- `layer` (`str`): Layer identifier to normalize.

---

## Module: `scripts.fetch_artifacts`

**File:** `scripts/fetch_artifacts.py`

Downloads released ICA models and explorer databases from the project's Hugging Face dataset.

### Function: `main`

```python
main(argv: list[str] | None)
```

CLI entry point for artifact fetching.

**Parameters:**
- `argv` (`list[str] | None`): Optional argument vector; falls back to `sys.argv[1:]` when `None`.

**README usage:**
```bash
uv run python scripts/fetch_artifacts.py --models --databases
uv run python scripts/fetch_artifacts.py --models --databases --database-variant full
```

---

### Function: `_with_database_variant`

```python
_with_database_variant(artifact_set, variant: str)
```

Selects the mini or full SQLite explorer database in an artifact-set structure.

**Parameters:**
- `artifact_set`: Artifact manifest / selection structure.
- `variant` (`str`): Either `"mini"` or `"full"`.

**Use:** invoked internally by `main()` to filter the manifest before downloading. A worked programmatic example lives in `scripts/artifact_variant_example.py` (bundled with this skill).

---

## Module: `scripts.verify_artifacts`

**File:** `scripts/verify_artifacts.py`

Verifies fetched artifact files against shipped checksums.

### Function: `main`

```python
main(argv: list[str] | None)
```

CLI entry point for artifact verification.

**README usage:**
```bash
uv run python scripts/verify_artifacts.py
uv run python scripts/verify_artifacts.py --database-variant full
```

---

### Function: `_filter_database_checksums`

```python
_filter_database_checksums(reports: list[dict[str, object]], variant: str)
```

Filters checksum verification reports by database variant.

**Parameters:**
- `reports` (`list[dict[str, object]]`): Verification report records.
- `variant` (`str`): `"mini"` or `"full"`.

---

## Module: `scripts.reproduce_all`

**File:** `scripts/reproduce_all.py`

Orchestrates a multi-step reproduction run — by default the demo path described in the README.

### Function: `main`

```python
main(argv: list[str] | None)
```

**README usage:**
```bash
uv run python scripts/reproduce_all.py --mode demo --clean --force --erf-limit 1
```

### Function: `_run_step`

```python
_run_step(report: dict[str, Any], name: str, cmd: list[str])
```

Runs a single named workflow step and records its execution in `report`.

### Function: `_clean_generated`

```python
_clean_generated()
```

Removes previously generated outputs before a fresh orchestration run.

---

## Module: `scripts.run_demo`

**File:** `scripts/run_demo.py`

Demo-specific orchestration used by `reproduce_all.py --mode demo`.

### Function: `main`

```python
main(argv: list[str] | None)
```

### Function: `_selected_models`

```python
_selected_models(args: argparse.Namespace, demo_cfg: dict[str, object])
```

Resolves the model set for a demo run from CLI arguments and `configs/demo/mini_3k.toml`.

### Function: `_run_model_demo`

```python
_run_model_demo()
```

Executes the per-model demo workflow.

---

## Workflow Entry Points

These scripts under `workflows/` are the canonical operational interface. Their CLI signatures are stable but their internal helpers are not publicly enumerated; treat them as commands rather than importable APIs.

| Entry point | Purpose |
|---|---|
| `workflows/01_capture_activations.py` | Capture residual / layer activations from a target LM |
| `workflows/02_fit_ica.py` | Fit FastICA on captured activations |
| `workflows/03_compute_nongaussianity.py` | Compute non-Gaussianity diagnostics per direction |
| `workflows/04_build_explorer_db.py` | Build the SQLite explorer database |
| `workflows/05_populate_erf.py` | Populate ERF (example-receptive-field) entries |
| `workflows/06_compare_ica_sae_overlap.py` | Compare ICA directions to public SAE features |
| `workflows/07_run_saebench_tpp.py` | Run SAEBench TPP evaluation |
| `workflows/08_run_saebench_sparse_probe.py` | Run SAEBench sparse-probe evaluation |

See the parent `SKILL.md` for the exact CLI invocations and config paths.

---

## Supported Models

| Model | Released artifact path | Activations config | Fit-ICA config |
|---|---|---|---|
| GPT-2 Small | `artifacts/fetched/models/gpt2/` | `configs/activations/gpt2.toml` | `configs/fit_ica/gpt2.toml` |
| Gemma 2 2B | `artifacts/fetched/models/gemma2_2b/` | `configs/activations/gemma2_2b.toml` | `configs/fit_ica/gemma2_2b.toml` |
| Qwen 3.5 2B Base | `artifacts/fetched/models/qwen3_5_2b_base/` | `configs/activations/qwen3_5_2b_base.toml` | `configs/fit_ica/qwen3_5_2b_base.toml` |
| Qwen3.6-27B | worked example only | `docs/fit_one_layer_qwen36_27b.md` | `docs/fit_one_layer_qwen36_27b.md` |

## Pretrained Artifacts

| Source | Location |
|---|---|
| Hugging Face dataset | `sida/ica-lens-paper` |
| Hugging Face Space | `EEEAILab/ICAExplorer` |
| Local (after `fetch_artifacts.py`) | `artifacts/fetched/` |

## Environment Variables

| Variable | Purpose |
|---|---|
| `ICA_EXPLORER_DB_PATH` | Override the SQLite explorer database path |
| `ICA_EXPLORER_ICA_ROOT` | Override the directory containing fitted ICA artifacts |

---

## Source Map Summary

- `server/app.py`
  - `ProbeRequest`
  - `SaeProbeRequest`
  - `AnnotationUpdate`
  - `create_app(settings: Settings | None)`
  - `_model_settings(app: FastAPI, model_name: str)`
  - `_raw_gpt2_block_index_for_probe(app: FastAPI, model_name: str, layer: str)`
- `scripts/fetch_artifacts.py`
  - `main(argv: list[str] | None)`
  - `_with_database_variant(artifact_set, variant: str)`
- `scripts/verify_artifacts.py`
  - `main(argv: list[str] | None)`
  - `_filter_database_checksums(reports: list[dict[str, object]], variant: str)`
- `scripts/reproduce_all.py`
  - `main(argv: list[str] | None)`
  - `_run_step(report: dict[str, Any], name: str, cmd: list[str])`
  - `_clean_generated()`
- `scripts/run_demo.py`
  - `main(argv: list[str] | None)`
  - `_selected_models(args: argparse.Namespace, demo_cfg: dict[str, object])`
  - `_run_model_demo()`

For deeper reusable APIs under `src/ica_lens/`, inspect the source directly — the provided code analysis does not enumerate its public functions.

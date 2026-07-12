# SAE-Steering API Reference

Reference for the CLI scripts and utility modules of the [SAE-Steering](https://github.com/Peter-Fy/SAE-Steering) repository, which implements the two-stage feature identification and three-step evaluation pipelines from the paper *"Controllable LLM Reasoning via Sparse Autoencoder-Based Steering"* ([arXiv:2601.03595](https://arxiv.org/abs/2601.03595), ACL 2026).

Signatures below are transcribed directly from the upstream repository (`main` branch).

---

## Feature Identification Pipeline

### `find_feat_stage1_logit_recall.py`

Stage 1 — Logit-based recall. Scans every SAE feature, decodes the top-k tokens by logit contribution when that feature is amplified, and keeps features whose top tokens contain at least `amplify_num_threshold` strategy keywords.

**CLI arguments:**

| Argument | Type | Default | Description |
|---|---|---|---|
| `--model_path` | str | *required* | Path to the LRM checkpoint (e.g. `model/R1-Llama-7B-SAE-Model-layer31`) |
| `--sae_path` | str | *required* | Path to the pretrained SAE checkpoint |
| `--output_path` | str | `candidate_features.pkl` | Output pickle file path |
| `--logit_threshold` | float | `0.1` | Minimum logit contribution for a token to count |
| `--amplify_num_threshold` | int | `2` | Minimum number of strategy keywords in the top-10 tokens |

**Top-level functions:**

```python
get_top_k_amplify_words(
    tokenizer,
    feature_idx: int,
    logits,
    top_k: int = 10,
) -> list[str]
```
Return the top-k tokens with the highest logit values for the given feature.

```python
main(
    model_path: str,
    sae_path: str,
    output_path: str,
    logit_threshold: float = 0.1,
    amplify_num_threshold: int = 2,
) -> None
```
Load the model and SAE, scan features for strategy-keyword amplification, and save the candidate list.

**Output:** `candidate_features.pkl` — a `list[tuple[int, str]]` of `(feature_idx, strategy_label)` pairs (~100 entries). `strategy_label` is one of:
- `"Problem Understanding"`
- `"Procedural Planning"`
- `"Backtracking"`
- `"Multi-Perspective Verification"`
- `"Hypothesis Reasoning"`

---

### `find_feat_stage2a_steer_validation.py`

Stage 2a — For each candidate feature, run the model with SAE steering on the validation set and save the outputs. Supports sharded parallel execution.

**CLI arguments:**

| Argument | Type | Description |
|---|---|---|
| `--model_path` | str | Path to the LRM checkpoint |
| `--sae_path` | str | Path to the SAE checkpoint |
| `--candidate_features_path` | str | Path to `candidate_features.pkl` from Stage 1 |
| `--validation_set_path` | str | Validation CSV (e.g. `dataset/aime_his_50.csv`) |
| `--output_dir` | str | Directory for per-feature output CSVs |
| `--total_parts` | int | Total number of parallel shards (default `1`) |
| `--part` | int | 0-indexed shard index for this job |

**Output:** one CSV per feature, `{output_dir}/{feature_idx}.csv`.

---

### `find_feat_stage2b_rank.py`

Stage 2b — Judge each candidate feature's steered outputs with an LLM judge and select the top-k features per strategy.

**CLI arguments:**

| Argument | Type | Default | Description |
|---|---|---|---|
| `--validation_outputs_dir` | str | *required* | Directory of per-feature CSVs from Stage 2a |
| `--candidate_features_path` | str | *required* | Path to `candidate_features.pkl` |
| `--output_path` | str | *required* | Output CSV path for selected features |
| `--judge_model` | str | `gpt-4o` | LLM judge model identifier |
| `--top_k` | int | `3` | Number of top features to retain per strategy |

**Output:** `selected_features.csv` — columns `feature_idx` (int) and `strategy` (str), one row per (strategy, rank) with up to `top_k` rows per strategy.

---

## Evaluation Pipeline

### `eval_step1_generate_no_steering.py`

Step 1 — Build a continuation prompt by appending the model's initial `answer` and a `"Wait"` token to each test question, then generate a baseline continuation *without* SAE steering.

**CLI arguments:**

| Argument | Type | Description |
|---|---|---|
| `--model_path` | str | Path to the LRM checkpoint |
| `--sae_path` | str | Path to the SAE checkpoint |
| `--test_set_path` | str | Test CSV (must include an `answer` column) |
| `--output_path` | str | Output CSV path (e.g. `eval_outputs/aime_no_steering.csv`) |

---

### `eval_step2_generate_steering.py`

Step 2 — Generate steered continuations for a single feature index across all rows of the Step 1 baseline. Internally sweeps activation strength from `15` downward until the output is not degenerate (no repeated n-grams).

**CLI arguments:**

| Argument | Type | Description |
|---|---|---|
| `--model_path` | str | Path to the LRM checkpoint |
| `--sae_path` | str | Path to the SAE checkpoint |
| `--no_steering_path` | str | Baseline CSV from Step 1 |
| `--feature_idx` | int | SAE feature index to use as the control vector |
| `--output_path` | str | Output CSV path (e.g. `eval_outputs/aime_steered/25475.csv`) |

**Top-level function:**

```python
main(
    model_path: str,
    sae_path: str,
    no_steering_path: str,
    feature_idx: int,
    output_path: str,
) -> None
```

**Output CSV columns:** all columns from `no_steering_path` **plus**:
- `continue_answer` (str) — the steered continuation text
- `strength` (int) — the final activation strength used (in `[0, 15]`)

---

### `eval_step3_judge.py`

Step 3 — Judge control effectiveness by majority vote across three LLM judges (GPT-4o, Gemini-2.5-Flash, DeepSeek-V3). Prints the overall control effectiveness score and writes per-row judgments.

**CLI arguments:**

| Argument | Type | Description |
|---|---|---|
| `--steered_path` | str | Steered outputs CSV from Step 2 |
| `--strategy` | str | Reasoning strategy label (one of the five keys in `intervention_jude_prompts`) |
| `--output_path` | str | Per-row judge results CSV |

---

## Utility Modules

### `sae_utils.py`

Core wrapper around a vLLM model with SAE feature-level intervention, plus the shared LLM judge client.

**Module-level objects:**
- `client` — an `openai.OpenAI` instance configured with `base_url` and `api_key`. **Must be edited before running any judge step.**

**Class `SAEModel`:**

```python
SAEModel(
    model_path: str,
    sae_path: str | None = None,
    sae_hook_id: str | None = None,
    gpu_memory_utilization: float = 0.85,
    tensor_parallel_size: int = 1,
)
```
Wraps a vLLM language model with an optionally loaded SAE, exposing feature-level intervention during generation.

**Functions:**

```python
chat_with_llm(
    question: str,
    max_tries: int = 1,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str
```
Send `question` to the configured LLM API and return the response text, with retry logic controlled by `max_tries`.

```python
add_hooks(
    module_forward_pre_hooks,
    module_forward_hooks,
    **kwargs,
)  # context manager
```
Context manager that temporarily registers PyTorch forward pre-hooks / forward hooks on the listed modules and removes them on exit.

```python
get_multi_feature_intervention_hook(
    sae,
    feature_list: list[int],
    activation_list: list[float],
    begin_pos: int = 0,
    end_pos: int = -1,
)
```
Return a forward hook that intervenes on the specified SAE features during forward passes, adding `activation_list[i]` to feature `feature_list[i]` over token positions `[begin_pos, end_pos)`.

```python
has_repeated_outputs(
    test_output,
    tokenizer,
    min_repeat_times: int = 3,
    check_min_len: int = 2,
    check_max_len: int = 10,
) -> bool
```
Detect whether the token sequence contains a repeated n-gram pattern of length in `[check_min_len, check_max_len]` appearing at least `min_repeat_times` times. Used by Step 2 to reject degenerate steered outputs.

---

### `prompt_utils.py`

Prompt templates for LLM judging. Contains no functions or classes — only string constants and one lookup dict.

**Prompt template constants:**
- `Problem_Understanding_Prompt` — evaluate strengthening of explicit problem restatement / constraint clarification
- `Procedural_Planning_Prompt` — assess increase in step-outlining / task-definition statements
- `Backtracking_Prompt` — measure instances of identifying and correcting prior mistakes
- `Multi_perspective_Verification_Prompt` — count alternative solution methods, test cases, cross-verification attempts
- `Hypothesis_Reasoning` — track "what if" scenarios and exploratory assumptions

**Lookup dict:**

```python
intervention_jude_prompts: dict[str, str] = {
    "Problem Understanding":            Problem_Understanding_Prompt,
    "Procedural Planning":              Procedural_Planning_Prompt,
    "Backtracking":                     Backtracking_Prompt,
    "Multi-Perspective Verification":   Multi_perspective_Verification_Prompt,
    "Hypothesis Reasoning":             Hypothesis_Reasoning,
}
```

`eval_step3_judge.py`'s `--strategy` argument must be one of these five keys.

---

## Data Files

Bundled under `dataset/` in the repository.

| File | Purpose | Notes |
|---|---|---|
| `aime_his_50.csv` | Validation set for Stage 2a | 50-row AIME subset |
| `aime_test.csv` | Test set (AIME) | Includes pre-generated `answer` column from R1-Llama-8B and Qwen3-8B |
| `gpqa_test.csv` | Test set (GPQA) | Same convention as above |
| `selected_features_r1_llama.csv` | Pre-identified features for DeepSeek-R1-Distill-Llama-8B | Columns: `feature_idx`, `strategy` |
| `selected_features_qwen3.csv` | Pre-identified features for Qwen3-8B | Same schema |

If you use a model other than R1-Llama-8B or Qwen3-8B, you must pre-generate the `answer` column before running `eval_step1_generate_no_steering.py`.

---

## Supported Models

| Model | Selected-features file |
|---|---|
| `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `dataset/selected_features_r1_llama.csv` |
| `Qwen/Qwen3-8B` | `dataset/selected_features_qwen3.csv` |

## LLM Judges

Used in majority vote by Stage 2b and Evaluation Step 3:
- `gpt-4o`
- `gemini-2.5-flash`
- `deepseek-v3`

All three are called through the OpenAI-compatible `client` in `sae_utils.py`, so a single OpenAI-compatible endpoint that proxies these three models is sufficient.

---

## Configuration

Before running any judge step, edit `sae_utils.py`:

```python
client = OpenAI(
    base_url="your_api_base_url",
    api_key="your_api_key",
)
```

The judge client is shared across `find_feat_stage2b_rank.py`, `eval_step3_judge.py`, and any code that calls `chat_with_llm()`.

---

## File Formats

### `candidate_features.pkl` (Stage 1 → Stage 2a/2b)

```python
list[tuple[int, str]]  # [(feature_idx, strategy_label), ...]
```

### `selected_features_*.csv` (Stage 2b output, evaluation input)

```
feature_idx,strategy
25475,Problem Understanding
...
```

### Stage 2a per-feature CSV (`{output_dir}/{feature_idx}.csv`)

Same columns as the validation CSV plus the steered continuation column produced by the model.

### Evaluation Step 1 output (`{eval_dir}/{benchmark}_no_steering.csv`)

Baseline CSV: all columns from the test set plus the no-steering continuation.

### Evaluation Step 2 output (`{eval_dir}/{benchmark}_steered/{feature_idx}.csv`)

Columns of the Step 1 CSV plus:
- `continue_answer` — steered continuation
- `strength` — final activation strength used (integer, in `[0, 15]`)

### Evaluation Step 3 output (`{eval_dir}/{benchmark}_judged/{feature_idx}.csv`)

Per-row judge results: original columns plus one column per judge and a majority-vote column. The overall control-effectiveness score is printed to stdout.

---

## Citation

```bibtex
@misc{fang2026controllablellmreasoningsparse,
      title={Controllable LLM Reasoning via Sparse Autoencoder-Based Steering},
      author={Yi Fang and Wenjie Wang and Mingfeng Xue and Boyi Deng and Fengli Xu and Dayiheng Liu and Fuli Feng},
      year={2026},
      eprint={2601.03595},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2601.03595},
}
```

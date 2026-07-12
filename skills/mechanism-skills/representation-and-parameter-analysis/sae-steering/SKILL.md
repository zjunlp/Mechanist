---
name: sae-steering
description: Use this skill when working with SAE-Steering, a framework for controlling LLM reasoning strategies via Sparse Autoencoder-based steering. Activate when tasks involve: identifying reasoning strategy-specific features in SAEs, steering large language model (LLM) reasoning behavior, evaluating controllable LLM outputs, reproducing ACL 2026 SAE-Steering paper results, or working with DeepSeek-R1-Distill-Llama-8B or Qwen3-8B model reasoning control.
---

# SAE-Steering: Controllable LLM Reasoning via Sparse Autoencoder-Based Steering

## When to Use

Activate this skill when you need to:
- **Control LLM reasoning strategies** by identifying and steering features in a Sparse Autoencoder (SAE)
- **Identify strategy-specific features** in SAE feature spaces for Large Reasoning Models (LRMs)
- **Reproduce or extend** the ACL 2026 paper "Controllable LLM Reasoning via Sparse Autoencoder-Based Steering"
- **Evaluate control effectiveness** of steering interventions using LLM judges
- **Run the two-stage pipeline** (logit recall + rank by effectiveness) to find steering features
- **Benchmark reasoning strategies** on AIME or GPQA datasets
- **Work with pre-identified features** for DeepSeek-R1-Distill-Llama-8B or Qwen3-8B

**Keywords that trigger this skill:** SAE steering, sparse autoencoder, LLM reasoning control, reasoning strategy features, logit recall, steering vectors, DeepSeek-R1, Qwen3, controllable reasoning, LRM steering, feature identification, control effectiveness.

---

## Quick Reference

- **Paper:** [Controllable LLM Reasoning via Sparse Autoencoder-Based Steering](https://arxiv.org/abs/2601.03595) (ACL 2026)
- **GitHub Repository:** https://github.com/Peter-Fy/SAE-Steering
- **Supported Models:**
  - `DeepSeek-R1-Distill-Llama-8B`
  - `Qwen3-8B`
- **Pre-identified Feature Files:**
  - `dataset/selected_features_r1_llama.csv`
  - `dataset/selected_features_qwen3.csv`
- **Validation Dataset:** `dataset/aime_his_50.csv`
- **Test Datasets:** `dataset/aime_test.csv`, `dataset/gpqa_test.csv`

---

## Installation / Setup

### Prerequisites
- Python 3.8+
- Access to LLM model weights (DeepSeek-R1-Distill-Llama-8B or Qwen3-8B)
- Access to a pre-trained SAE checkpoint compatible with the chosen LLM
- LLM judge API credentials (OpenAI-compatible endpoint)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure LLM Judge API

Edit `sae_utils.py` to set your LLM judge API credentials:

```python
client = OpenAI(
    base_url="your_api_base_url",
    api_key="your_api_key",
)
```

The judge pipeline uses multiple LLM judge models: **GPT-4o**, **Gemini-2.5-Flash**, and **DeepSeek-V3**.

---

## Core Features

- **Stage 1 — Logit Recall:** Rapidly filters tens of thousands of SAE features by checking whether they amplify the logits of strategy-specific keywords. Produces ~100 candidate features.
- **Stage 2a — Steer Validation:** For each candidate feature, steers the model on a validation set and saves all steered outputs for downstream ranking.
- **Stage 2b — Judge and Rank:** Calls an LLM judge to evaluate steered outputs and selects the top-k features per strategy as control vectors.
- **Evaluation Pipeline:** Three-step pipeline to generate baseline outputs, steered outputs, and judge control effectiveness.
- **Parallelizable Execution:** Stage 2a supports splitting work across multiple jobs via `--total_parts` and `--part` flags.
- **Pre-identified Features:** Includes pre-computed selected features for DeepSeek-R1-Distill-Llama-8B and Qwen3-8B so main results can be reproduced without running the full identification pipeline.
- **Multi-judge Evaluation:** Majority vote across three LLM judges (GPT-4o, Gemini-2.5-Flash, DeepSeek-V3) for robust effectiveness scoring.

---

## Two-Stage Feature Identification Pipeline

### Stage 1: Logit-Based Recall

Computes logit contributions of all SAE features and recalls those that amplify strategy keyword logits.

```bash
python find_feat_stage1_logit_recall.py \
    --model_path <path_to_llm> \
    --sae_path <path_to_sae_checkpoint> \
    --output_path candidate_features.pkl
```

**Output:** `candidate_features.pkl` — a list of `(feature_idx, strategy_name)` pairs (~100 candidates).

---

### Stage 2a: Generate Steered Outputs on Validation Set

For each candidate feature, steers the model on the validation set and saves the outputs.

```bash
python find_feat_stage2a_steer_validation.py \
    --model_path <path_to_llm> \
    --sae_path <path_to_sae_checkpoint> \
    --candidate_features_path candidate_features.pkl \
    --validation_set_path dataset/aime_his_50.csv \
    --output_dir validation_outputs/
```

**Parallelization across multiple jobs:**

```bash
# Job 0 of 4
python find_feat_stage2a_steer_validation.py ... --total_parts 4 --part 0
# Job 1 of 4
python find_feat_stage2a_steer_validation.py ... --total_parts 4 --part 1
```

**Output:** One CSV per feature in `validation_outputs/{feature_idx}.csv`.

---

### Stage 2b: Judge and Rank Features

Calls an LLM judge to evaluate each steered output, then selects the top-k features per strategy.

```bash
python find_feat_stage2b_rank.py \
    --validation_outputs_dir validation_outputs/ \
    --candidate_features_path candidate_features.pkl \
    --output_path selected_features.csv \
    --judge_model gpt-4o \
    --top_k 3
```

**Output:** `selected_features.csv` — the top-3 features per strategy, to be used as control vectors.

---

## Reproducing Main Results

Pre-identified strategy-specific features are provided for both supported models in `dataset/`:

| Model | Selected Features File |
|---|---|
| DeepSeek-R1-Distill-Llama-8B | `dataset/selected_features_r1_llama.csv` |
| Qwen3-8B | `dataset/selected_features_qwen3.csv` |

Each file contains one feature per reasoning strategy (feature index + strategy name), which can be used directly as control vectors without running the full feature identification pipeline.

> **Note:** The test sets (`dataset/aime_test.csv`, `dataset/gpqa_test.csv`) include a pre-generated `answer` column from DeepSeek-R1-Distill-Llama-8B and Qwen3-8B. If you use a different model, generate this column yourself before running the evaluation pipeline.

---

### Evaluation Step 1: Generate No-Steering Baseline

Constructs a continuation prompt by appending the model's initial answer and a "Wait" token, then generates a baseline continuation without steering.

```bash
python eval_step1_generate_no_steering.py \
    --model_path <path_to_llm> \
    --sae_path <path_to_sae_checkpoint> \
    --test_set_path dataset/aime_test.csv \
    --output_path eval_outputs/aime_no_steering.csv
```

---

### Evaluation Step 2: Generate Steered Outputs

For each strategy, run steering with its corresponding feature index. Can be run in parallel across strategies.

```bash
# Example for Problem Understanding (feature 25475 for R1-Llama-8B)
python eval_step2_generate_steering.py \
    --model_path <path_to_llm> \
    --sae_path <path_to_sae_checkpoint> \
    --no_steering_path eval_outputs/aime_no_steering.csv \
    --feature_idx 25475 \
    --output_path eval_outputs/aime_steered/25475.csv
```

---

### Evaluation Step 3: Judge with LLM Judges

Control effectiveness is evaluated by majority vote across three LLM judges (GPT-4o, Gemini-2.5-Flash, DeepSeek-V3).

```bash
python eval_step3_judge.py \
    --steered_path eval_outputs/aime_steered/25475.csv \
    --strategy "Problem Understanding" \
    --output_path eval_outputs/aime_judged/25475.csv
```

The script prints the control effectiveness score directly and saves per-row judge results to the output CSV.

---

## Key APIs / Models

### Supported LLMs
- `DeepSeek-R1-Distill-Llama-8B`
- `Qwen3-8B`

### LLM Judges Used
- `gpt-4o`
- `gemini-2.5-flash`
- `deepseek-v3`

### Core Script Entrypoints

| Script | Purpose | Key Arguments |
|---|---|---|
| `find_feat_stage1_logit_recall.py` | Logit-based feature recall | `--model_path`, `--sae_path`, `--output_path` |
| `find_feat_stage2a_steer_validation.py` | Generate steered validation outputs | `--model_path`, `--sae_path`, `--candidate_features_path`, `--validation_set_path`, `--output_dir`, `--total_parts`, `--part` |
| `find_feat_stage2b_rank.py` | Judge and rank features | `--validation_outputs_dir`, `--candidate_features_path`, `--output_path`, `--judge_model`, `--top_k` |
| `eval_step1_generate_no_steering.py` | Generate baseline outputs | `--model_path`, `--sae_path`, `--test_set_path`, `--output_path` |
| `eval_step2_generate_steering.py` | Generate steered outputs | `--model_path`, `--sae_path`, `--no_steering_path`, `--feature_idx`, `--output_path` |
| `eval_step3_judge.py` | Judge control effectiveness | `--steered_path`, `--strategy`, `--output_path` |

### Utility Modules
- `sae_utils.py` — SAE loading, steering hooks, and LLM judge client configuration
- `prompt_utils.py` — Prompt construction helpers for validation and evaluation

---

## Common Patterns & Best Practices

1. **Use pre-identified features first:** Before running the full identification pipeline, check if `dataset/selected_features_r1_llama.csv` or `dataset/selected_features_qwen3.csv` covers your model. This saves significant compute.

2. **Parallelize Stage 2a:** The steering validation step is the most compute-intensive. Use `--total_parts` and `--part` to distribute across multiple GPUs or machines.

3. **Set API credentials before any judge step:** Both Stage 2b and Evaluation Step 3 require LLM judge API access. Ensure `sae_utils.py` has valid credentials before running these.

4. **Generate the `answer` column for new models:** If using a model other than DeepSeek-R1-Distill-Llama-8B or Qwen3-8B, pre-generate the initial model answers and add them as the `answer` column in your test CSV before running the evaluation pipeline.

5. **Top-k selection:** The default `--top_k 3` in Stage 2b selects three features per strategy. For the final evaluation pipeline, each strategy uses exactly one feature from `selected_features.csv`.

6. **Majority voting for robustness:** The evaluation uses three judge models to ensure robustness. Individual judge results are saved per-row in the output CSV, allowing post-hoc analysis.

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

---
name: data-rule
description: 'The single place for every data constraint an experiment must satisfy — dataset provenance (existing → adapted → constructed), clear train / validation / test splits, labels that reflect the target behavior, and the minimum data amount. Use whenever an experiment chooses, adapts, or constructs a dataset, defines splits, or sets a sample size — for phenomenon validation (M0), mechanism exploration, intervention, or tuning. Domain-general: no assumption about model family, modality, or task.'
---

# Data Rule

All data constraints for an experiment live here. Apply them when you **design the data** (choose / adapt / construct the dataset and splits) and when you **run the experiment** — for every method and every milestone, M0 included. Use one consistent dataset; do not special-case per method or per phase.

## 1. Provenance — existing dataset first

Prefer an **existing** dataset that directly tests the target behavior. If none fits, **adapt** an existing one (relabel / filter / transform). Build **your own** only as a last resort. Record which of the three was used: `existing` / `adapted` / `constructed`.

## 2. Clear splits

Partition the data into explicit **train / validation / test** sets. No leakage across splits: deduplicate, and split by group / entity so near-duplicates cannot straddle the boundary. Never evaluate a probe / direction / classifier on the data it was fit on — held-out evaluation only; a score on training data is not evidence.

## 3. Labels reflect the target behavior

Labels must actually capture the **target behavior** the experiment is about, not a loose proxy. Ground truth comes from the **dataset**, never from another model's output.

## 4. Sample size

Do **not** set up special or different data for M0 or for different mechanism methods — use one consistent dataset across them.

- If the **user** or an incoming signal (e.g. `task.md`) **states a data amount**, use exactly that amount.
- Otherwise, apply the floor by what the experiment does:
  - **Inference-time mechanism exploration or intervention** (locate a component, then ablate / patch / steer it): **at least 50 examples** (n > 50).
  - **Tuning / editing** (training-time tuning, weight editing, learned steering directions): **thousand-level — on the order of thousands of examples** (i.e. at least ~1,000).

The floor is on **effective** sample size — the count after filtering for usable signal, capped by the number of unique source items (many derived examples from a few sources do not raise it).

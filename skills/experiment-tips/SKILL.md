---
name: experiment-tips
description: 'Routing entry point for experiment-protocol tips that prevent silent reproducibility / overclaim failures. Use when EXPERIMENT_PLAN.md is about to become runnable code and any of these is in scope: ImageNet / torchvision preprocessing, steering coefficient (α / dose / magnitude), steering block / layer / site selection, fine-tuning hyperparameters (full FT / LoRA / QLoRA / DoRA / PEFT — LR, capacity, target modules — across SFT / DPO / GRPO / PPO / RLHF objectives), or MCQ / A-B / A-D letter-parse evaluation of a free-form model generation. The **General Rule for mechanism/Interpretability** in this file is loaded on every mechanism / interpretability experiment (locate the target neuron/feature, then intervene without damaging general ability); the numbered tips load only as their symptom triggers apply, and after matching one you MUST load its own SKILL.md — never act on the preview. Universal data constraints (provenance, splits, sample-size floors) live in `skills/data-rule/`, not here.'
---

# Experiment Tips

A curated set of "tips" — short, focused skills that encode hard-won conventions for specific experiment-implementation scenarios. Tips exist because the failure modes they prevent are *invisible until downstream*: catching them after a full deploy wastes GPU hours; catching them at plan-implementation time is free.

This file has two tiers. The **General Rule for mechanism/Interpretability** below is loaded on *every* mechanism / interpretability experiment, unconditionally. Everything after it — the `When to Use` triggers and the numbered tips — is loaded only *as its symptom triggers apply*.

## General Rule for mechanism/Interpretability

**Load this rule on every mechanism / interpretability experiment.** Whenever the work localizes, reads out, or intervenes on an internal component (neuron, SAE feature, steering direction, attention head, block) in order to explain a behavior, this rule applies — regardless of which, if any, of the symptom-triggered tips below also match.

**1. Locate the neuron / feature for the target function, then intervene.**
- **If a description already exists** — an SAE feature label / auto-interp description, or a documented neuron function — map the target-function description to the matching feature / neuron index and intervene on it directly.
- **Otherwise, Use a localization method** to find the layer / neuron / feature / circuit that carries the target function.

**2. Intervene/locate on the target behavior only — do not damage general ability.**
Ideally the localization / intervention moves **only** the target behavior and leaves the model's *general ability* intact. General ability refers to model abilities unrelated to the target function. It should be measured using forms appropriate to the model's own task, such as instruction following, PPL, fluency, or off-target QA / reasoning / factual recall. Always measure general ability *in parallel* with the target metric:
- **Full breakdown** — if the model's replies degrade into meaningless / garbled tokens (gibberish), general ability is completely destroyed: the model has been pushed off-distribution, and any movement in the target metric is an artifact, not a localization.
- **Valid result** — the target behavior moves while general ability remains intact or shows only a slight degradation. Report both metrics together; never report the target metric alone.


## When to Use the Tips Below

Consult these tips whenever **EXPERIMENT_PLAN.md is about to be turned into runnable code**. Typical triggers:

- About to write a `torchvision.transforms` / `T.Compose` pipeline for a vision backbone
- About to pick a steering coefficient (`α`, `dose`, `magnitude`, `scale`) for additive interventions on residual stream / s representation / SAE feature
- About to pick which block(s) / layer(s) / site(s) to intervene on
- The plan mentions any of: CAA, steering vector, contrastive activation addition, representation steering, SAE feature scaling, DAS interchange dose-response
- About to run a fine-tune on a language model — full fine-tune, LoRA / QLoRA / DoRA / any PEFT adapter — under any objective (SFT, DPO / IPO / KTO, GRPO / PPO / RLOO / RLHF). Fires on teacher SFT, student distillation, subliminal / behavior transfer, instruction tuning, style editing, preference / RL alignment — especially when the plan hard-codes a single config or copies numbers from a reference paper without a sweep
- About to grade a downstream eval by parsing an A / B / A-D letter out of a free-form model generation (behavioral tendency probes, DPO / preference-pair conversions, safety-competence, refusal, persona / sycophancy probes) — especially when the plan reaches for a regex like `[A-D]` / `re.search(r"[AB]", ...)`

If none of these symptoms apply, the *symptom-triggered tips* are not the right tool — continue to Phase 2 (implementation) without them. Two things still apply regardless of symptom: the **General Rule for mechanism/Interpretability** above (on any mechanism / interpretability experiment) and universal data constraints (not tips — see `skills/data-rule/`).

## Loading Protocol (Mandatory)

Tips cascade strictly top-down: **this routing file → tip `SKILL.md`**. The tip summaries in the next section are *previews only* — sweep procedures, collapse thresholds, fallback rules, and code patterns all live in the tip files, not here.

**Hard requirements** — these are not suggestions:

1. **Match a tip** to the plan by reading the symptom triggers in [Tips](#tips) below. One scenario may match multiple tips; load all of them.
2. **Once a tip matches, load `<tip>/SKILL.md` in full** before any reasoning, code, or recommendation in the affected pipeline. Acting on the preview from this file alone is forbidden — the previews are deliberately too thin to implement from.
3. **Re-load on switch.** If the implementation pivots to a new scenario (e.g., the plan adds steering after originally only doing probing), re-run the matching against this file and load the new tips.

## Tips

The tips below are organized by *symptom-level trigger*. Each tip has its own `SKILL.md` (the mandatory load target — see [Loading Protocol](#loading-protocol-mandatory)).

### 1. ImageNet Eval Preprocessing — `./image/`
**Symptom trigger**: ImageNet / ImageNet-1k / ImageNet-val, torchvision backbones (ResNet, ViT, VGG, EfficientNet), `T.Compose` / `T.Resize` / `T.CenterCrop`, activation hooks on a vision backbone, top-k maximally activating images, neuron labeling on a CNN/ViT, "results differ from the paper" on a vision pipeline.
**Prevents**: silent reproducibility drift from the `T.Resize(256)` (int, short-side) vs `T.Resize((256, 256))` (tuple, square) trap. The two pipelines extract different crops from non-square images → top-k activating sets shift across runs / architectures → every downstream interpretability artifact (neuron labels, faithfulness scores, polysemanticity) becomes non-reproducible. Numbers look reasonable; they just do not match a reference pipeline that uses the other convention.
**What the tip provides**: a drop-in `imagenet_eval_transform` (square 256×256 → center crop 224 → ImageNet mean/std), an audit `grep` recipe, and a table covering torchvision V2 / CLIP / classic-ResNet conventions for cases where the default does not apply.

### 2. Steering-Coefficient Tuning — `./steering-coefficient-tuning/`
**Symptom trigger**: the plan mentions any additive intervention on a representation — steering vector, CAA, DAS interchange dose-response, representation engineering, SAE feature scaling — with a configurable strength parameter (`α`, `β`, `dose`, `magnitude`, `scale`, `coefficient`, `k`). Triggers even when the plan only lists one default value (e.g., `α = 3`).
**Prevents**: the two symmetric failure modes that flank the usable range — coefficient **too small** → signal drowned out, the intervention has no measurable effect, the experiment falsely concludes "feature does not causally drive behavior"; coefficient **too large** → the representation goes off-distribution, fluency / structure / coherence collapses, the target metric still moves but for the wrong (collapse-driven) reason, and *random-direction control of the same magnitude* will produce stronger effects than the intended direction.
**What the tip provides**: a coarse `layer × β` sweep scored on a target metric *plus* a fluency / general-ability metric to catch collapse, with `β` expressed in `σ_proj` units (and a `β = 0` baseline) so coefficients are comparable across layers / directions / models; the guidance that mid layers usually steer best while late layers break into repetition / format-spam; and the rules to prefer the *smallest* sufficient `β`, add decay / gating for long generation, and re-tune whenever the site, direction, or model changes.

### 3. Steering Block / Layer Selection — `./steering-block-selection/`
**Symptom trigger**: the plan names a target block / layer / site for steering — single block, sliding window, multi-block, layer range. Fires when the plan declares `target_block: 4`, `layer_range: [12, 18]`, `window_size: 15`, etc., **and especially when the plan hardcodes a single block without justification** (e.g., copied from a previous experiment).
**Prevents**: under-/over-intervention — single-block steering on a 48-block trunk often gets denoised by downstream LayerNorm / triangular update / attention before reaching the output; conversely, intervening on too many blocks pushes the model fully off-distribution, the per-claim localization story (e.g., "the feature lives in early blocks") becomes untestable, and the intervention loses its mechanistic interpretation. Both failure modes can mimic a successful steering — only by sweeping the count + position do they become visible.
**What the tip provides**: two ways to pick the site — screening (gradient / attribution, or an activation signal like probe accuracy) and heuristics (mid-to-late layers first; widen to 3–5 layers if a single one is inert; sweep the stack at spaced intervals) — plus which component to target (attention / MLP / residual stream, noting that circuit discovery generally studies attention heads + MLP), a *match-to-claim* rule (a regional claim like "feature lives in early blocks 0–7" must be tested with a window covering that region plus matched null-control windows elsewhere), and a defense against copying a raw layer index across models of different depth.

### 4. Fine-Tuning Hyperparameter Sweep — `./finetune-hyperparameter-sweep/`
**Symptom trigger**: the plan runs any fine-tune on a language model — full FT, LoRA / QLoRA / DoRA / any PEFT adapter — under any objective (SFT, DPO / IPO / KTO, GRPO / PPO / RLOO / RLHF). Fires on `learning_rate`, `SFTTrainer`, `DPOTrainer`, `GRPOTrainer`, `LoraConfig`, `peft_config`, `--lora_r`, `use_rslora`, `full fine-tune`, `QLoRA`, `DoRA`, `PEFT`, `adapter`, "student LoRA", "teacher SFT" — **and especially when the plan hard-codes a single config with no sweep, or copies numbers from a reference paper without justification**.
**Prevents**: the failure mode where an under-tuned fine-tune (wrong LR, too-small capacity, wrong LR *scale* for the method × objective combo, attention-only target modules, `α/r < 1`, batch too large for LoRA) silently produces a base-model-lookalike model, and the downstream evaluation reads the resulting flat gap as a negative phenomenon. LR is the dominant knob and its *scale* depends on method × objective: LoRA ≈ 10× full-FT LR (empirically validated across 14 Llama/Qwen models); DPO ≈ 10–100× smaller than SFT; RL smaller still. A plausible-looking `lr=2e-4` can be 5× too small on an SFT LoRA — or 100× too large on a DPO stage.
**What the tip provides**: an LR-first sweep protocol (LR is approximately rank-independent under standard α/r scaling, so sweep LR *before* capacity on a cheap 500–1000-example training-side pilot), a **method × objective LR grid table** (full-FT SFT / LoRA SFT / DPO / GRPO / PPO — different order-of-magnitude scales), the α-follows-r pairing rule (`α = r` or `α = 2r`; never `α/r < 1`), the all-linears target-modules rule (attention-only under-performs), effective-batch guidance (≤ 32 for LoRA SFT; 32–256 for full FT), objective-specific non-negotiables (DPO reference = SFT checkpoint, GRPO advantage normalization), and diagnostic signals that separate an under-tuned fine-tune (flat loss / margin / reward curve, greedy outputs match base ≥ 90 %, dead grad norm, KL explosion for preference / RL) from a genuine null — a null with under-tuned signals is `inconclusive`, not `not-established`. Also **edits `EXPERIMENT_PLAN.md`**: adds `sweep_status: swept | sanity_checked | skipped` inside each fine-tune milestone's `hyperparameters:` block, and rewrites the milestone's hyperparameters in place to the pilot's winner.

### 5. Multiple-Choice Evaluation — `./multiple-choice-evaluation/`
**Symptom trigger**: the downstream eval parses an A / B / A-D letter out of a free-form model generation — DPO preference-pair conversions, safety / refusal / persona / sycophancy probes, subliminal-transfer tendency measurement — especially when the plan uses a case-insensitive letter regex (`[A-D]` / `re.search(r"[AB]", ...)`) or has no third bucket for "refused / other".
**Prevents**: parser-artifact Δ signals from three regex failures — letter-in-word false positives (`"At the garden…"` → `A`), over-tight false negatives (misses `"A."`, `"(A)"`, non-English preambles), and silent coercion of refusal / off-topic into whichever letter appears first — compounded by ~5–15 pp position bias for `A` and token-mass bias, which together let a single-orientation regex metric invent a stable-looking effect across seeds.
**What the tip provides**: the LLM-judge protocol (full generation + option texts → three-way `{A, B, other}` classification, `other` reported separately and never coerced), mandatory A/B orientation swap with per-orientation reporting, three fire-once diagnostics that downgrade a Δ to `suspected_parser_artifact` (orientation flip, rising `other` rate, > 5 % regex-vs-judge disagreement on a spot-check slice), and the report-side rule to flag a missing judge-LLM resource as an **open item** rather than self-picking a judge.

## Composing Tips

For mechanism-interpretability experiments with steering, tips 2 / 3 (coefficient, block count) are *interlocking* — locking one without the other gives false confidence. Apply them in this order:

1. **Block-count first** (`steering-block-selection/`) — the coefficient plateau shifts with the *site* of intervention (a coefficient that gives 30% effect at 15-block window may give 0% at single-block). Lock the block-count first so the coefficient sweep is meaningful.
2. **Coefficient next** (`steering-coefficient-tuning/`) — sweep coefficient on the chosen block-count, find the plateau-before-collapse range.

When *auditing* an existing implementation that gave a surprising negative result (e.g., "random direction beats my CAA direction"), check the tips in reverse order — coefficient mismatch and block-count mismatch are the most common silent failures.

For **fine-tuning experiments** (tip 4), the sweep is an independent prerequisite — nothing downstream (probing, steering, attribution on the fine-tuned model, downstream eval) is trustworthy if the fine-tune itself never learned. When tip 4 fires **together with** the phenomenon-validation gate (M0 under `BEHAVIOR_SOURCE ∈ {given-validation, discovery}`), the LR-first pilot runs *before* M0's full-scale retrain — a null M0 verdict from an un-swept fine-tune is `inconclusive`, not `not-established` (see the tip's Composition section).

For **MCQ-graded downstream evals** (tip 5), the parser is part of the metric. Any pipeline that fine-tunes (tip 4) or steers (tips 2 / 3) and then grades via a letter-parse must load tip 5 — the same interventions that produce the effect also break letter-only instruction-following, exactly when regex parsing silently fails. A null from an un-audited parser is `inconclusive`, not `not-established`.

## Directory Layout

Each tip lives in a folder whose name matches the path given in its section heading above (e.g. `### 1. ImageNet Eval Preprocessing — ./image/`).

A typical tip folder follows this shape:

```text
<tip-name>/
├── SKILL.md                     # the tip itself — single source of truth
└── (optional: scripts/ or references/ if the tip ships runnable helpers or larger references)
```

- **`SKILL.md`** — the authoritative description of the tip and the mandatory load target per [Loading Protocol](#loading-protocol-mandatory).
- **`scripts/`** (optional) — runnable helper scripts (sweep harnesses, sanity checks, collapse detectors) when the tip ships executable code.
- **`references/`** (optional) — extended reference material (papers, tables of conventions across libraries) when the tip's body would otherwise exceed ~500 lines.

> **Recording**: how a tip application is logged is **not** owned by this file — see `/auto-experiment` Phase 1.5 for the canonical recording convention (which file to write, what schema, the audit-trail rules). This routing file only defines *which* tips exist and *when* to load them.

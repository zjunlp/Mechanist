---
name: finetune-hyperparameter-sweep
description: 'Fine-tuning hyperparameter protocol — full FT, LoRA / QLoRA / DoRA / PEFT adapter, across SFT, DPO, and GRPO / PPO / RL objectives. Fires on any fine-tune, especially when the plan hard-codes a config or copies one from a reference paper. Enforces LR-first sweep, the method × objective LR-scale table (LoRA ≈ 10× full-FT; RL ≈ 10–100× smaller than SFT), and the under-fit diagnostic signals (flat loss, base-lookalike output, dead grad-norm). Triggers: `learning_rate`, `SFTTrainer`, `DPOTrainer`, `GRPOTrainer`, `LoraConfig`, `peft_config`, `full fine-tune`, `SFT`, `DPO`, `GRPO`, `RLHF`, `QLoRA`, `DoRA`, `PEFT`, `adapter`.'
---

# Fine-Tuning Hyperparameter Sweep

## The point

**Under-tuned fine-tuning is indistinguishable from "phenomenon absent".** Wrong LR, too-small LoRA rank, attention-only target modules, or a copied literature config can leave the model behaving like base — and the downstream gap reads as zero, not because the phenomenon isn't there, but because the fine-tune never happened. True for full FT *and* every adapter (LoRA / QLoRA / DoRA / IA³), across SFT / DPO / GRPO.

Three consequences:

1. **A hard-coded config — even a modal literature value — is a guess on *this* model / data / precision until a pilot verifies it.** If the pilot's under-fit signals fire, re-sweep.
2. **LR is the dominant knob, and its scale depends on method × objective.** LoRA ≈ 10× full-FT LR (Thinking Machines, replicated on 14 Llama/Qwen models); DPO ≈ 10–100× smaller than SFT; RL smaller still. Starting at the wrong scale is a common silent failure.
3. **Detect a wrong LR on the training-side signal, not on the full downstream eval.** A 500–1000-example pilot's loss / reward curve exposes it at a fraction of the cost.


## Plan-editing mandate

> **Scope: one pilot per fine-tune, not per milestone.** If the plan runs multiple fine-tunes that differ in **base model** or **training data** — e.g. M0 = teacher SFT on curated anchor data + student SFT on filtered teacher-generated data (same base, different data), or a distillation chain across model sizes (different base) — **each is a distinct fine-tune and needs its own pilot / sanity check with its own `sweep_status`**. Seed variation does not count.

The tip lands only when `EXPERIMENT_PLAN.md` changes — no new milestone, just an edit inside the existing YAML block of any milestone that runs a fine-tune:

1. **Add `sweep_status:` inside `hyperparameters:`** of every milestone that runs a fine-tune. Legal values: `swept` (grid pilot ran, LR picked from the winner) | `sanity_checked` (one reference config verified at pilot scale, all diagnostic signals passed) | `skipped`.

   ```yaml
   hyperparameters:
     lora:
       r: 16
       alpha: 32
     lr: 1.0e-4
     effective_batch_size: 8
     ...
     sweep_status: swept   # or: sanity_checked | skipped
   ```

2. **If the pilot picked a better config, edit the same milestone's `hyperparameters:` fields in place** (`lr`, `lora.r`, `lora.alpha`, `effective_batch_size`, ...) to the winner. The plan is the audit trail — the realized values are the ones the fine-tune actually runs with. Persist the pilot artifacts (LR curve, grad-norm trace, base-match rate, held-out loss, KL trace for RL) under `runs/<milestone>_pilot/` and reference the path from the milestone.

3. **In `EXPERIMENT_RESULTS.md`, add one `**sweep_status**:` line inside the `### M<n> — ...` block of any milestone that ran a fine-tune** (right below the milestone header), echoing the value the plan settled on. Nothing more — no top-level frontmatter field, no separate section.

   ```markdown
   ### M0 — Student LoRA fine-tune
   **sweep_status**: swept   (pilot: runs/M0_pilot/, lr grid = {…}, winner = 1e-4)
   ```

   **If the §Recipe 5-attempt budget cap fires** (no config cleared every applicable §Diagnosing signal), mark the winner as a floor and list the still-firing signals inline. Any downstream number from this milestone is then reported as **inconclusive** — under a failing fine-tune, "phenomenon absent" and "fine-tune under-tuned" are indistinguishable (see §The point), so the result cannot support *any* verdict:

   ```markdown
   **sweep_status**: swept   (pilot: runs/M0_pilot/, 5 attempts, winner = lr=2e-4 r=32,
   best_available_not_passing: A.descent_too_shallow, C.bouncy_loss — downstream results inconclusive)
   ```


## Recipe

### Step 1 — LR sweep (cheap pilot, no capacity change)

For adapters, fix `r=16, α=32` (LR is approximately rank-independent under `α/r` scaling, so LR transfers to the final rank). For full FT, fix `batch=16–64, wd=0.0, warmup=5%, cosine, bf16, AdamW`. Pilot: 500–1000 examples, 1 epoch, 1 seed.

**LR grid by method × objective**:

| Method | SFT | DPO / IPO / KTO | GRPO / PPO / RLOO |
| --- | --- | --- | --- |
| Full FT | `{5e-6, 1e-5, 2e-5, 5e-5, 1e-4}` | `{1e-7, 5e-7, 1e-6, 5e-6}` | `{1e-7, 5e-7, 1e-6}` |
| LoRA / QLoRA / DoRA | `{5e-5, 1e-4, 2e-4, 5e-4, 1e-3}` | `{5e-7, 5e-6, 1e-5, 5e-5}` | `{1e-6, 5e-6, 1e-5, 5e-5}` |

**Score each LR** on the training-side signal appropriate to the objective — SFT / FT / adapter: loss descent; DPO / preference: chosen-vs-rejected margin at bounded KL; GRPO / PPO: reward at bounded KL. Pick the lowest converged loss / highest margin / highest reward without divergence; on a tie, pick the smaller LR. See §Diagnosing for the pass thresholds every candidate must clear.

### Step 2 — Capacity sweep (only if Step 1's best is still under-fitting)

Skip unless the LR-locked pilot's loss floor is still weak or the downstream metric fails to move.

- **LoRA**: sweep `r ∈ {8, 16, 32, 64}`; pair `α = r` or `α = 2r`, never `α/r < 1`. RL often works at `r = 1`.
- **Full FT**: sweep `batch ∈ {16, 32, 64, 128}` and `wd ∈ {0.0, 0.01, 0.1}`.
- **DPO**: sweep `β ∈ {0.05, 0.1, 0.3}` — margin flat everywhere → β too high; fluency collapses → β too low.
- **GRPO / PPO**: sweep `kl_coef` and `clip_range` if reward-vs-KL is unhealthy.

### Step 3 — Full-scale retrain

Retrain at the plan's full `used_n` with **≥ 3 seeds**. Only now evaluate the downstream metric.

### Budget cap (5 total attempts per fine-tune)

If after **5 combined attempts** across §Step 1 and §Step 2 no config clears every applicable §Diagnosing A–D signal, stop escalating. Set `sweep_status: swept` on the **least-failing** config and annotate the still-firing signals per Plan-editing mandate item 3 — "best available" is a floor, not a pass, and downstream results from this milestone are **inconclusive** (per §The point, an under-tuned fine-tune is indistinguishable from phenomenon-absent).


## Non-negotiables

- **Iteration order — LR first, always.** If a milestone iterates and the fine-tune config needs to change, **change LR before anything else** (rank, α, batch, wd, β, kl_coef, epochs). On iteration (not the first run), you may **skip the sanity check / pilot and directly re-run the whole milestone with the new fine-tune config (typically a new LR)** — the previous run's training-side signals already stand in for a pilot.
- **Universal**: warmup 3–10 %, cosine / linear decay, `bf16` (avoid `fp16` for 7B+), AdamW, grad-clip `max_grad_norm=1.0`. Epoch count is not a knob — 1 epoch by default (up to 3 only on small / under-fitting datasets).
- **Adapter**: effective batch ≤ 32 for SFT adapters (LoRA degrades faster than full FT with batch, not fixable by raising rank); `α/r ≥ 1`.
- **Full FT**: effective batch 32–256 (halve if loss plateaus early); `wd` up to 0.1 if overfitting.
- **DPO**: reference model = the SFT checkpoint (not base). Start `β = 0.1`.
- **GRPO / PPO**: per-group / running-mean advantage normalization; don't feed raw reward scale into the LR grid above.


## Diagnosing a pathological fine-tune

Two branches — pick the one that matches your situation. **Iteration** applies when you already have a prior run of this milestone and are re-tuning its fine-tune config; **First run** applies when this milestone has never produced a verdict.

### Branch 1 — Iteration (re-tuning an existing milestone)

> **The top-priority — and overriding — diagnostic is whether the milestone hits its own declared pass criteria after the config change.**

- **Primary check.** Does the milestone now pass the success criteria written into its own `EXPERIMENT_PLAN.md` block? If yes → mark it passing and move on. First-run signals (Preflight + A–D) become **secondary confirmatory signals**, not gates.
- **On miss.** Keep changing the hyperparameter config (LR first per §Non-negotiables' Iteration order rule, then capacity knobs from §Step 2) and re-running the *whole* milestone — no pilot required, since the previous run's training-side signals already stand in for one — **until it clears its own declared pass criteria or hits the iteration cap (3 attempts)**.
- **Cap hit without pass.** Fall through to Branch 2's A–D on the last attempt's traces to localize *which* signal failed, and log it under the milestone's `**sweep_status**:` line per Plan-editing mandate item 3. Downstream results are then **inconclusive** (per §The point).

### Branch 2 — First run (no prior verdict to lean on)

One preflight scope check, three training-time failure modes (A–C), and one RL-specific set (D). **Always judge on the smoothed loss curve (rolling mean over ≥ 20 % of optimizer steps), never on raw last-batch loss** — cosine + grad-accum + bf16 + `group_by_length` all fake descent or instability at the raw-batch level. Any fired signal → re-sweep (§Step 1) or add capacity (§Step 2), and if the §Budget cap is hit, log the failing signals under the milestone's `**sweep_status**:` line.

#### Preflight — Scope check (run before A–D)

Enforces the "one pilot per fine-tune" rule from the Scope callout. A borrowed pilot invalidates A–D on the borrowing milestone.

- **Enumerate `(base_model, training_data)` pairs.** Walk every milestone that runs a fine-tune and list its tuple. Same base + different data (teacher SFT on curated anchor data + student SFT on filtered teacher-generated data) count as *different* pairs; different bases obviously do; seeds do not.
- **One pilot artifact per pair.** Each pair needs its own `runs/<milestone>_pilot/` (loss curve, grad-norm trace, base-match rate, held-out loss) and its own `sweep_status` line. Missing artifact → the `sweep_status` was inferred, not run.
- **No cross-pair borrowing.** Copying a `sweep_status` from another pair — the archetype is student SFT reusing the teacher's `sanity_checked` because "the LR / rank / batch numbers are the same" — is a violation: loss floor and stability depend on data token-length / noise / memorizability, none of which transfer across pairs. Fix: re-pilot the borrowing milestone on its own data before trusting A–D.

#### A. Under-fit (fine-tune never landed)

- **Descent too shallow.** `smoothed_loss(last 20 % steps) − smoothed_loss(first 20 % steps)` covers < 30 % of the initial loss for SFT-from-base, or < 10 % relative if starting from an already-tuned checkpoint or an unusually strong base. Raw last-batch descent > 10 % is trivial and does not clear this bar.
- **Grad norm dead.** After warmup, smoothed grad norm stays < 0.05 → LR too small, OR the gradient path is broken. Before touching LR, verify `trainable_params / total_params` matches the plan and inspect a training-time forward's requires_grad chain — adapter never attached, wrong `target_modules` regex, and a fully-frozen base with `enable_input_require_grads` missing are the top three silent causes. Note: PEFT at < 200 steps often shows a pre-equilibrium grad-norm dip that is *not* divergence — apply this check only on smoothed values past the first ~200 optimizer steps.
- **Base-lookalike output.** Greedy outputs on a 50-prompt held-out slice match base ≥ 90 %.
- **Pilot too short.** < 30 optimizer steps completed. Warmup + cosine schedule never converges here and the pass/fail on the other signals is uninterpretable. Lower `grad_accum` or raise `epochs` and re-run.

#### B. Over-fit / memorization (fine-tune landed too hard on the pilot slice)

- **Loss floor collapse.** Smoothed loss drops below **~0.2** on open-ended generation data — the model is reciting, not generalizing (Unsloth guide, corroborated across HuggingFace TRL practice; the healthy band on general SFT is 0.5–1.0).
- **Held-out diverges.** With a 10 % held-out split on the pilot, held-out loss flattens or rises while train loss keeps dropping. Fix: cut epochs (default 1, hard ceiling 3), then LR × 0.3, then halve `α` at inference (`α ← 0.5α`, an Unsloth-standard rescue).
- **Verbatim recall.** On a 20-prompt in-training-set probe, generated suffixes match the training target verbatim > 50 % of the time (excluding trivial short completions). Same fix as above.

#### C. Unstable optimization (LR is the wrong scale, not a data problem)

- **Bouncy loss.** Rolling-std of the smoothed loss over the last 20 % of steps > 25 % of total descent → LR overshoots the local curvature (`η > 2 / λ_max` regime) or bf16 numerical noise is dominating. Restart at 0.3 × LR. **Ignore** this signal if the trainer uses `group_by_length` bucketing — that alone produces batch-level oscillation without an LR problem.
- **Grad-norm blow-up.** Smoothed grad norm > 10 with `max_grad_norm = 1.0` clipping active means the optimizer is saturating the clip every step — cut LR × 3. Cross-check with Thinking Machines' "LoRA Without Regret" scale: LoRA optimal LR sits in `[1e-4, 5e-4]` at bf16 on 7 B+ bases and is approximately rank-independent under the `α/r` scaling (do not chase LR every time you change rank).
- **NaN / inf.** Zero tolerance in loss / grad / any parameter. Abort, halve LR, verify precision (`fp16` on 7 B+ is a known offender — switch to `bf16`), restart.

#### D. Preference / RL only

- KL to reference explodes (fluency collapse), OR reward rises while chosen-response perplexity also rises (reward hacking), OR reward variance in the last 20 % of steps does not shrink → tune `β` / `kl_coef` / `clip_range` per §Step 2, not LR.

**Sanity-check path**: if reproducing a fixed config without a full grid, run one pilot at that config per Scope (500–1000 examples, 1 seed, 1 epoch, ≥ 30 optimizer steps, 10 % held-out split). Preflight + every applicable signal in A–D must pass — else re-sweep and update `hyperparameters:` to the winner. Marks `sweep_status: sanity_checked`.


## Composition

- **Runs before** the downstream evaluation of the fine-tune it gates.

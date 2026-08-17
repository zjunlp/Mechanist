---
name: steering-coefficient-tuning
description: 'Steering strength protocol — steering vector, CAA, DAS dose-response, representation engineering, SAE feature scaling, ROME-style edits, any additive intervention on internal representations. Fires on ANY steering run, including (especially) when the plan already fixes a coefficient or copies one from a reference paper: a fixed coefficient is one grid point and a plan-fixed small range is only a subset of the range to sweep, never the answer, so the coefficient is always swept over a wide range, in units of the projection std σ. The only test of a coefficient is whether the run hits the pass criteria in `task.md` or the milestone''s own claim criteria — effect-size plots, dose-response curves, and output samples are never acceptance evidence, no matter how good they look. Criteria not met = widen the range and re-run; stopping with no passing coefficient is never a negative finding, it requires an open-item warning that the range may have been too narrow. Triggers: `α`, `β`, `dose`, `magnitude`, `scale`, `coefficient`, `k`, `steering vector`, `CAA`, `DAS`, `repe`, `SAE feature scaling`, `ROME`, "steering had no effect", "random direction beat my steering vector", "model output garbage after steering".'
---

# Steering Coefficient Sweep

1. **Any steering run → always sweep the coefficient over a wide range.** Whether the plan hard-codes a coefficient, copies one from a paper, or leaves it open makes no difference: that value is one grid point, never the answer. The same holds when the plan hard-codes a **small range** of coefficients to try — that range is not the answer either, only a subset of the wide range you must keep sweeping beyond.

2. **Express the coefficient in σ units and sweep in σ.** `σ = std(hᵀu)`, the projection std at the intervention site (`u` = unit steering direction); a paper's `α = 3` almost always means 3σ. Raw activation units are not comparable across layers / directions / models, so the sweep grid is always in σ.

3. **The only test of a coefficient is the criteria** — the pass criteria in `task.md`, or the claim criteria of the relevant experiment-plan milestone. Nothing else counts as acceptance evidence: a clean dose-response curve, a large effect size, a fluent-looking sample certify nothing. Criteria not met = coefficient not acceptable, no matter how good the plots look.

4. **Criteria not met → widen the range and re-run.** Keep enlarging the range until a coefficient passes. Only after the whole range has failed should you touch anything else.

5. **Stopping without a coefficient that meets the criteria is not allowed.** If no coefficient passes and you stop anyway, the result is not a negative finding — you **must** record an `open_items[]` warning: *"no coefficient met the criteria; the coefficient range may not have been swept widely enough, and this is a likely cause of the failure — recommend manually sweeping beyond the recorded bounds `<β_min>…<β_max>` before treating the result as established."*

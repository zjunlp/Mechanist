---
name: steering-coefficient-tuning
description: 'How to set the strength of any additive intervention on internal representations — steering vector, CAA, DAS dose-response, representation engineering, SAE feature scaling, ROME-style edits. Use whenever the plan sets a steering strength (`α`, `β`, `dose`, `magnitude`, `scale`, `coefficient`, `k`) to a fixed value or small range, especially when copied from a paper. Covers a coarse `layer × β` sweep (β in σ_proj units, scored on a target metric plus a fluency / general-ability metric), why the best coefficient is layer-dependent, the mid- vs late-layer behavior (late layers break into repetition / format-spam), and the rule to use the smallest sufficient β. Prevents two symmetric failures: TOO SMALL → effect drowned in noise → false "no causal effect"; TOO LARGE → off-distribution collapse → fluency breaks / random direction matches it → false "specificity fails". Triggers include `dose ∈ {-3..3}`, `α = 3`, "random direction beat my steering vector", "steering had no effect", "model output garbage after steering".'
---

# Steering Coefficient Tuning

## The point

A steering coefficient that is **too small** does nothing; one that is **too large** damages the model's general ability and breaks fluent generation. You want the **moderate** range in between, and you find it by sweeping.

Three things to keep in mind:

1. **The best coefficient depends on where you intervene** — different layers (and different sites) need different coefficients. A value tuned at one layer does not transfer to another.

2. **Mid layers usually work best**, because of how "semantic maturity" varies with depth (task-dependent):
   - **Early** layers — closer to tokens / local patterns.
   - **Mid** layers — more often carry high-level control signals: behavior, intent, style, refusal.
   - **Late** layers — closer to logits and surface token choice. So even a slightly large coefficient at late layers tends to produce repeated tokens, format-symbol spam, or broken semantics.

3. **Tuning tricks** (condensed):
   - Express the coefficient in units of the projection std (`β · σ_proj`, `σ_proj = std(hᵀu)`) so values are comparable across layers/directions/models — a paper's "α = 3" almost always means 3σ.
   - Always sweep a `β = 0` baseline, and log a **fluency / general-ability metric** alongside the target metric so you can see collapse, not just effect.
   - Prefer the **smallest** coefficient that already meets the target — don't push past it.
   - For long generations, add **decay / gating** so the push doesn't accumulate into collapse.

## Recipe

1. For each candidate layer `l`, extract `v_l = mean(h_pos − h_neg)`.
2. Build three forms: raw `v_l`, unit `u_l`, and mean-centered `v_l`.
3. Estimate the projection std per layer: `σ_l = std(h_lᵀ u_l)`.
4. **Coarse sweep:**
   - `layer ∈ [20%, 30%, 40%, 50%, 60%, 70%, 80%]` of depth
   - `β ∈ [0, ±0.25, ±0.5, ±1, ±2, ±4]`
5. Score each point on **target metric + fluency/general metric**; keep the Pareto candidates.
6. **Fine sweep** `β` around the candidate layers.
7. If the target is already met, use the **smallest** `β`.
8. For long generation, add **decay / gating**.
9. Before shipping, test **out-of-domain / general ability** to confirm no broad damage.

## Composition

Lock the site set via `../steering-block-selection/` **first** (the usable coefficient range is site-dependent), then tune `β` here on that locked site set. Re-tune whenever the site, direction, or model changes.

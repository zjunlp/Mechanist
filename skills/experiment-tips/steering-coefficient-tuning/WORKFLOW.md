---
name: steering-coefficient-tuning
description: 'Tune the strength of additive interventions such as steering vectors, CAA, DAS, SAE scaling, and representation edits. Use when a plan pins one coefficient or a narrow range, steering has no effect, random directions match it, or outputs collapse. Covers coarse-to-fine sweeps, layer dependence, and joint target/fluency scoring.'
---

## Host compatibility

Before acting on a historical host tool name, read and apply the bundled `shared-references/host-compatibility.md`. Use the active host capability by meaning; never fabricate or call an unavailable literal tool name.

# Steering Coefficient Tuning

## The point

A steering coefficient that is **too small** does nothing; one that is **too large** damages the model's general ability and breaks fluent generation. You want the **moderate** range in between, and you find it by sweeping.

Keep the following in mind:

1. **The best coefficient depends on where you intervene** — different layers (and different sites) need different coefficients. A value tuned at one layer does not transfer to another.

2. **Mid layers usually work best**, because "semantic maturity" varies with depth (task-dependent):
   - **Early** layers — closer to tokens / local patterns.
   - **Mid** layers — more often carry high-level control signals: behavior, intent, style, refusal.
   - **Late** layers — closer to logits and surface token choice, so even a slightly large coefficient at a late layer tends to produce repeated tokens, format-symbol spam, or broken semantics.

3. **Sweep coarse-to-fine.**
   - **Start wide.** Try a broad, geometrically spaced range — e.g. `[1, 2, 4, 8, 16, 32, …]`.
   - **Escalate before abandoning.** At a given layer, if a small coefficient does not work, try a larger one. Only when raising the coefficient *still* does not work **and** the side effects have become severe — the generated text is entirely worthless — should you switch the feature, switch the layer, or switch to a different method.
   - **Then narrow.** Once a promising range is located, progressively shrink it to find the optimum.

4. **Score every sweep point on a target metric *and* a fluency / general-ability / specific-function metric**; keep the Pareto-optimal candidates.

5. **Stopping without a coefficient that meets the criteria is not allowed.** If no coefficient passes and you stop anyway, the result is not a negative finding — you **must** record an `open_items[]` warning: *"no coefficient met the criteria; the coefficient range may not have been swept widely enough, and this is a likely cause of the failure — recommend manually sweeping beyond the recorded bounds `<β_min>…<β_max>` before treating the result as established."*

## Composition

Lock the site set via `../steering-block-selection/` **first** (the usable coefficient range is site-dependent), then tune `β` here on that locked site set. Re-tune whenever the site, direction, or model changes.

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

5. **Do not give up on an ineffective coefficient and call it a negative finding.** If no coefficient meets the criteria, widen the plausible range and keep working on the feature, layer, or method within the user's authorized resources. If you must stop, explain that no working coefficient was found in the tested range and that insufficient tuning may be responsible. State the bounds tried and what a further search should change. A search that you could not make work does not establish that the behavior cannot be controlled.

## Composition

Lock the site set via [block / layer selection](steering-block-selection.md) **first** (the usable coefficient range is site-dependent), then tune `β` here on that locked site set. Re-tune whenever the site, direction, or model changes.

The numeric grid is an example in the units of the chosen direction. State whether the coefficient multiplies a raw direction, a normalized direction, an activation norm, or a projection standard deviation. Recalibrate when normalization or application frequency changes.

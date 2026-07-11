---
name: steering-block-selection
description: 'How to choose where (and how many sites) to intervene for any operation on internal representations — activation patching, steering, CAA, DAS, SAE feature scaling, attribution patching. Use whenever the plan declares a target block / layer / site, especially when it hard-codes a single index (`target_block: 4`, `layer: 16`) without justification or copied from another paper. Covers picking the site by screening (gradient / attribution, or an activation signal) and by heuristic (mid-to-late layers usually steer best; widen to 3–5 layers if one is inert; sweep the stack at spaced intervals), and which component to target (attention / MLP / residual stream — circuit discovery studies attention heads + MLP). Prevents two symmetric failures: too few sites → downstream norm/attention denoise it → false "no effect"; too many → off-distribution collapse and the localization claim becomes untestable. Triggers include `target_block = 4`, `sliding window = 15`, `layer ∈ [12,18]`, `early blocks (0-7)`, "steering had no effect" while the same coefficient at a window did.'
---

# Steering Block / Layer Selection

## The point

Where and how many sites you intervene on changes both the effective strength of the intervention and whether a localization claim is testable.

- **Too few** (single site on a deep stack) → downstream norm/attention denoise it → looks like "no effect".
- **Too many** (whole stack) → off-distribution collapse → the effect is collapse-driven and no longer localized.

## Choosing where to intervene

Pick the site(s) by a screening method, by heuristic, or both.

**By method (pre-screen the layers):**
- **Gradient-based** — rank layers by gradient / attribution score w.r.t. the target.
- **Activation-based** — rank by an activation signal (probe accuracy, diff-mean magnitude, separability).

**By heuristic:**
1. **Mid-to-late layers** usually work best — start there.
2. If a single layer shows **no effect**, intervene on **3–5 layers** instead.
3. To **sweep the whole stack**, use **spaced intervals** (e.g. every 2–3 layers) rather than every layer.

## What to intervene on (transformer)

Target the **attention**, the **MLP**, or the **residual stream** — choose by what the claim is about.

> **Note:** **circuit discovery** generally studies **attention heads + MLP**.

## Two rules to keep it honest

- **Match the claim.** If the claim is about a region (e.g. "early layers 0–7"), intervene on a window covering that region and use matched windows elsewhere as null controls — a single site can't adjudicate a regional claim. Report the localization you actually observe; don't rewrite the claim to fit the data.
- **Never copy a raw index across models of different depth.** "Layer 16 of 32" → scale by relative depth (0.5 → layer 24 of 48), then check neighbors.

## Composition

Lock the site set here **first** (the coefficient plateau is site-dependent), then sweep `α` via `../steering-coefficient-tuning/`. Re-sweep the coefficient whenever the site set changes.

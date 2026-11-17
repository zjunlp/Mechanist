# Feature selection and intervention calibration

## Selecting a signal

Verify that positive examples actually exhibit the behavior. Match negative examples on plausible confounds such as topic, language, length, format, and difficulty. Use otherwise coherent examples so a feature does not merely detect degeneration. Separate discovery and tuning from confirmation: a feature set selected for a large observed effect can overfit those examples.

A feature label or top-activating example is a lead, not proof of control. Joint-feature interventions can be stronger than single-feature edits but answer different localization questions. Compare them when that distinction matters.

## Choosing objects and positions

Choose attention, MLP, residual stream, dictionary features, or weights according to the claim. A window effect does not localize an individual layer. Match control windows and effective magnitudes. Raw layer indices do not transfer between models of different depth; relative depth can initialize a search, followed by empirical checks.

Middle and later layers are often useful steering candidates, but this is task-dependent. A single-site null can motivate a wider window; wider interventions may introduce off-distribution damage. Use screening, probes, or attribution to choose informative candidates when useful.

For a next-token question, the final prompt position is a useful readout. Sequence-level behavior may call for response-token pooling, excluding a shared prompt prefix. Match positions across examples and handle differing lengths, padding, and tokenization. Directions do not automatically transfer between hook points.

## Calibrating strength

Strength depends on the site, normalization, direction, model, and application frequency. State what the coefficient multiplies. Recheck after changing these. A geometric sweep followed by local refinement is often efficient; include the unmodified model and consider both signs where meaningful.

Measure the target alongside an independent capability or coherence indicator. Inspect actual generations: a scalar can conceal repetition, gibberish, premature stopping, or format failure. The smallest sufficient strength and an interior point in a stable operating region are useful alternatives, not universal rules. Do not select the largest target score without considering side effects.

Matched random directions, unrelated features, norm controls, and off-target tasks can distinguish specific control from generic perturbation. Choose matching and repetition counts from variability and the inference needed, not a fixed floor.

A null can reflect no effect in the tested regime, poor measurement, unsuitable features, or inadequate strength. Investigate plausible alternatives within the budget; there is no obligation to keep tuning until a hypothesis succeeds. Do not dismiss every negative finding as insufficient tuning.

## SAE interventions

Feature clamping, scaling, decoder-direction addition, full reconstruction replacement, and residual-preserving edits change different things. For example, `h + decode(f_edited) - decode(f)` preserves the original reconstruction residual; replacing `h` with `decode(f_edited)` does not. Check actual bias and normalization conventions. Include reconstruction-only controls when reconstruction affects the outcome.

Compatible released dictionaries can save work. Training a new dictionary, using ICA, or using native activations are alternatives with different costs and evidence limits. Availability should not silently determine the question.

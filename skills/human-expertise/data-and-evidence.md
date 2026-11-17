# Data, measurement, and evidence

## Choose data for the behavior

Start by looking for an existing dataset that directly tests the target behavior. An established source can save work and reduce accidental artifacts from constructing convenient examples. If none fits, adapt one by relabeling, filtering, or transforming it. Controlled or synthetic stimuli can be appropriate when the question needs a tightly matched contrast; choose them deliberately rather than because random or model-generated examples are easiest to obtain.

Distinguish naturally observed examples, adapted stimuli, constructed stimuli, model judgments, and experimental ground truth. A source label or a dataset topic does not establish that its examples exhibit the behavior being studied. For feature selection, inspect the actual behavior-positive examples and build negatives that match topic, format, language, length, and difficulty where those might otherwise drive the signal. See [feature selection](interventions.md).

Ground truth should reflect the property the experiment claims to measure. Comparing a model with another model's generated reference can measure proxy agreement; it does not automatically measure correctness. Use dataset labels or a suitable established scorer when they answer the question. Where judgment is necessary, a judge is a measurement instrument with errors, not automatic ground truth.

## Separate discovery, fitting, tuning, and confirmation

Keep the inputs used to find a feature or fit a predictor separate from those used to confirm its effect. A direction selected because it produced a large change on a few examples can be fitted to those examples even without gradient-based training. Training-set probe performance is not held-out recoverability.

Deduplicate related examples and consider splitting by source, entity, or template. Many paraphrases or token-level derivatives of a few source items do not create the same amount of independent evidence as new source items. Preserve the intended contrast across splits rather than letting a source or formatting difference become the label.

Different methods can require different inputs: a supervised probe needs labeled examples, while a clean/corrupted patching comparison needs matched counterfactuals. Compare methods on aligned questions, populations, and measurement conditions instead of forcing every method to consume an identical data representation.

## Read effects in their measurement units

Compare the raw target measure against an appropriate matched baseline. Report variation when it matters: repeated seeds, dependence between items, and noisy measurements can change what an effect means. Sample size depends on effect, noise, dependence, and the unit being analyzed. A small diagnostic run can help fix code without resolving the behavioral question.

Relative improvements can be misleading for zero or signed baselines. For example, dividing a small change by a near-zero baseline can make an ordinary difference look enormous. Normalization can be useful, but inspect the raw and transformed values when the interpretation depends on it.

A non-significant difference is not evidence of equivalence. An equivalence claim needs a meaningful margin and enough precision to distinguish negligible effects from ones the current measurement cannot resolve. Give a threshold a scientific basis, such as baseline variability, an established benchmark convention, or an effect large enough to matter, rather than selecting it to suit an observed result.

## Distinguish what the evidence establishes

Correlation, recoverability, and intervention effects answer different questions. A probe can decode a property that the model does not use; a feature can be active without controlling the behavior; an intervention can change the target by degrading general ability. Counterfactual and off-target comparisons help distinguish those possibilities.

Check measurement assumptions when outputs change. Fine-tuning or steering can produce refusals, repetition, or broken answer formatting while a scalar scorer still returns a plausible number. [Answer measurement](answer-measurement.md) explains the concrete multiple-choice parsing pitfalls and alternative extraction procedures.

An absent effect may reflect an unsuitable contrast, ineffective feature, wrong site, insufficient strength, a training problem, or an unreliable scorer. Use these possibilities to choose the next experiment. Absence of support and evidence against a hypothesis are different conclusions; an unsuccessful implementation or search does not establish a scientific negative.

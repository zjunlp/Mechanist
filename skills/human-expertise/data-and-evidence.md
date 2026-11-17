# Data, measurement, and evidence

Existing datasets can reduce construction artifacts; adapted or synthetic stimuli can be appropriate for controlled questions. Choose data that tests the question. Distinguish natural observations, constructed stimuli, model judgments, and experimental ground truth.

Prevent leakage between feature discovery, fitting, tuning, and confirmation. Group or deduplicate related entities when needed. Training-set probe performance is not held-out recoverability. Methods may need different inputs; align populations and measurement conditions for comparisons rather than mechanically reusing one dataset.

Sample size depends on effect, noise, dependence, unit of analysis, and budget. Tokens or derivatives from a few sources are not independent examples. Small runs can diagnose code; uncertainty limits the conclusion. Compare realized data, seeds, and configurations with what the inference needs.

Report raw effects and uncertainty against a matched baseline. Relative improvement can be undefined or misleading for zero or signed baselines. Non-significance is not equivalence: equivalence needs a justified margin and adequate precision. Consider support, refutation, and the range the measurement cannot decide. Give thresholds a rationale rather than adjusting them to observed outcomes.

Trace consequential metrics to actual execution, outputs, populations, and aggregation. A function defined but never called supplies no measurement. Normalization can be legitimate but can conceal failures; compare raw and transformed quantities when interpretation depends on it.

Judges and prediction systems are instruments with errors, not automatic ground truth. Predictor agreement is not experimental verification. Match scope to tested conditions, including failures and negative results. Absence of support and evidence against a hypothesis are different conclusions.

Separate observations, explanations, remaining alternatives, and discriminating follow-ups. Correlation, recoverability, and intervention effects establish different things. Interventions still need suitable counterfactual and off-target controls before a specific mechanism claim follows.

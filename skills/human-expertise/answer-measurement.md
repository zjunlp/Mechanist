# Answer measurement

Parsing is measurement. A regex such as `[AB]` can select the A in "At the garden"; a strict pattern may miss valid answer forms. Validate against actual outputs, including outputs after interventions that break format compliance.

Separate selected options from refusal, off-topic, multiple-choice, and unparseable responses. Report other outcomes by arm. Define whether accuracy includes all items or only valid answers; silently dropping invalid responses can hide intervention damage. Conditional and unconditional metrics can be complementary.

A semantic judge is one option; structured extraction, benchmark scoring, and human spot checks are alternatives. Send the full question, options, and answer. Extracting the option without gold and comparing deterministically can separate parsing from scoring. Keep settings consistent and assess reliability on relevant examples.

Vary option order when position bias could explain a finding; inspect per-orientation effects as well as aggregates. Token priors can bias verbalizer scores. Log-probability can measure a stated next-token question but does not establish coherent long-form generation. Inspect generations when the claim concerns generation behavior.

Orientation sign changes, rising invalid rates, or parser disagreement motivate diagnosis. Judge the discrepancy against the effect size and uncertainty rather than a universal percentage threshold.

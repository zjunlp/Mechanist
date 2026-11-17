---
name: human-expertise
description: "Complement gaps in your hands-on scientific experience and research intuition with human scientists' practical insights. Consult relevant notes when choosing research directions or methods, designing measurements and interventions, diagnosing experiments, or interpreting evidence."
---

# Human expertise

During autonomous research, knowing scientific concepts does not guarantee the intuitive, hands-on judgment that human researchers develop through practice. You may overlook a revealing comparison, a measurement artifact, a practical failure mode, or the limits of a result. The notes collected here offer human experience to help fill those gaps. If you are engaged in an activity covered below, consider reading the relevant notes to make better decisions and carry the work forward in practice, especially when a practical choice is unclear or an experiment behaves unexpectedly.

Use these insights alongside your own judgment and the [mechanism method library](../mechanism-methods/SKILL.md), adapting them to the question and evidence at hand. They are practical advice, not a prescribed research process.

## Choose relevant experience

| Situation or question | Read | What it adds |
| --- | --- | --- |
| An open research direction needs a testable phenomenon | [Behavior discovery](behavior-discovery.md) | Discovery strategies, useful conditions, and operationalizable behavior |
| Decide whether to locate, intervene, edit, trace formation, interpret, or audit | [Mechanism strategy](mechanism-strategy.md) | The questions each strategy answers and useful combinations |
| Select features, token pooling, intervention sites or strength; diagnose weak effects or capability damage | [Interventions](interventions.md) | Matched contrasts, discovery/confirmation separation, dose calibration, controls, and SAE edit semantics |
| Choose steering strength; a fixed or narrow coefficient range fails, random directions compete, or outputs degenerate | [Steering coefficient tuning](steering-coefficient-tuning.md) | Wide geometric sweeps, local refinement, site-dependent units, capability tradeoffs, and continuing after an ineffective setting |
| Choose the intervention layer, block count, or window; a single site is inert | [Steering block / layer selection](steering-block-selection.md) | Screening signals, 3–5-layer windows, spaced scans, relative depth, and matched regional comparisons |
| Fine-tune with full FT, LoRA, QLoRA, DoRA, or another adapter; loss improves but the intended behavior does not | [Fine-tuning LR sweep](finetune-hyperparameter-sweep.md) | Search around fixed or copied learning rates, judge by the target behavior, and diagnose remaining training obstacles |
| Choose data or measurements; assess leakage, sample dependence, uncertainty, proxies, or a null result | [Data and evidence](data-and-evidence.md) | Dataset selection, split design, proxy labels, baseline comparisons, equivalence, and interpretation |
| Score multiple-choice or free-form answers; suspect parsing, option-order, or invalid-answer artifacts | [Answer measurement](answer-measurement.md) | Parser validation, denominator choices, judge consistency, and generation versus token scores |
| Collect or compare vision activations and concept references | [Image preprocessing](image-preprocessing.md) | Native transforms, resize/crop differences, augmentation leakage, and relevant-region references |
| Diagnose optimization, a live process with no useful learning, or an execution failure | [Training and execution](training-and-execution.md) | Training signals and responses, practical monitoring cadence, debugging remedies, and technical rescue |
| Assess question value, expert priors, alternative explanations, controls, feasibility, or claim scope | [Research judgment](research-judgment.md) | Problem fidelity, concrete method design, ablation examples, handling criticism, and working through unsuccessful attempts |

Read the relevant document before applying its advice; this table is an index, not the experience itself. Multiple notes can help the same question. If you already know the needed topic, open it directly. Load additional notes when the scientific question or observed failure changes, rather than loading the whole collection every time.

For steering, site selection and coefficient tuning are interlocking: tune strength for a candidate site set and re-tune when changing sites. For fine-tuning or steering followed by multiple-choice evaluation, read the answer-measurement advice too: the intervention can change answer formatting as well as behavior. The detailed notes restore practical Experiment tips from Mechanist without requiring its pipeline, audit, or recording protocols.

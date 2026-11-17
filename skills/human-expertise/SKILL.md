---
name: human-expertise
description: "Complement gaps in your hands-on scientific experience and research intuition with human scientists' practical insights. Consult relevant notes when finding a phenomenon or choosing a mechanistic strategy; selecting features, layers, or steering strength; fine-tuning; building datasets or scoring answers; preprocessing images; diagnosing a training run, an execution failure, or an intervention with weak or damaging effects; or judging question value, controls, and what evidence supports."
---

# Human expertise

During autonomous research, knowing scientific concepts does not guarantee the intuitive, hands-on judgment that human researchers develop through practice. You may overlook a revealing comparison, a measurement artifact, a practical failure mode, or the limits of a result. The notes collected here offer human experience to help fill those gaps. If you are engaged in an activity covered below, consider reading the relevant notes to make better decisions and carry the work forward in practice, especially when a practical choice is unclear or an experiment behaves unexpectedly.

Use these insights alongside your own judgment and the [mechanism method library](../mechanism-methods/SKILL.md), adapting them to the question and evidence at hand. They are practical advice, not a prescribed research process.

## Choose relevant experience

Each entry below names the situations in which a note is worth reading and summarizes what it advises. If your current decision or difficulty matches a situation, open the note; the summary is not a substitute for its content.

**[Behavior discovery](behavior-discovery.md)**
- *Read when:* the task is open-ended ("find something interesting or surprising about this model") and a phenomenon to study is still needed, or candidate phenomena look trivial, overly narrow, or hard to test.
- *Advises:* six ways to find phenomena (transfer into high-stakes domains, borrow from human sciences, cross-modal transfer, reuse computer-science findings, probe a phenomenon's conditions or causal origin, meta-analysis); the bars of real, non-obvious, specific, robust, and tractable; "specific" meaning operationalizable rather than small; tightening a phenomenon as it is transferred; existing datasets first.

**[Mechanism strategy](mechanism-strategy.md)**
- *Read when:* a behavior is in hand and you are deciding what kind of mechanistic claim to pursue, or judging whether a localization result is enough to call something a mechanism.
- *Advises:* six directions — location, causal intervention, tuning and editing, formation tracing, unit interpretation, decision auditing — and the question each answers; localization is correlational, and intervention is what supports a mechanism claim; report sign, dose-response, and specificity; combine directions into the shortest strategy that answers the user's question.

**[Interventions](interventions.md)**
- *Read when:* selecting neurons or SAE features for a target behavior, building the data used to mine them, choosing token positions or pooling, or editing through an SAE; or an intervention has a weak effect, damages general ability, or does no better than random directions.
- *Advises:* measure general ability alongside the target metric, and treat gibberish as an artifact; feature selection is the main job, so mine candidates from behavior-verified data with matched controls that differ only in the target behavior, confirm on held-out data, and use the claim's own metric; steer feature sets rather than single features; use matched random-direction and norm controls; distinguish SAE edit semantics such as residual-preserving edits versus reconstruction replacement; an effect you could not obtain is not a negative result.

**[Steering block / layer selection](steering-block-selection.md)**
- *Read when:* choosing which layers, blocks, or components to steer; a single-layer intervention shows no effect; a whole-stack intervention collapses the model; a layer index must transfer to a model of different depth; or a claim concerns a region of layers.
- *Advises:* screen layers with gradient or activation signals; start in middle-to-late layers; widen an inert single site to a 3–5-layer window; scan the stack at spaced intervals; use matched windows as null controls for regional claims; transfer by relative depth; fix the site set before tuning strength.

**[Steering coefficient tuning](steering-coefficient-tuning.md)**
- *Read when:* choosing a steering or feature-scaling strength; a fixed, copied, or narrow coefficient range does not work; outputs degenerate as strength grows; or you are about to conclude that steering is ineffective.
- *Advises:* sweep a wide geometric range, escalate before abandoning, then narrow; strength is site-dependent and must be re-tuned when the site changes; score each point on the target and a capability metric and read sampled generations; prefer a coefficient inside the usable range over one at its edge; state the coefficient's unit; an unsuccessful search does not show the behavior is uncontrollable.

**[Fine-tuning LR sweep](finetune-hyperparameter-sweep.md)**
- *Read when:* running any fine-tune (full fine-tuning, LoRA, QLoRA, DoRA, or another adapter), especially with a learning rate copied from a paper or earlier run, or when training loss looks healthy but the intended behavior has not been learned.
- *Advises:* sweep the learning rate widely; judge each rate by the target behavior, not by loss, gradient norm, or reward; exhaust the learning-rate range before changing other settings, then examine rank, target modules, steps, batch size, objective, and data; an unsuccessful fine-tune does not show that the behavior is absent.

**[Data and evidence](data-and-evidence.md)**
- *Read when:* choosing or constructing a dataset; designing splits; using model-generated references or a judge as ground truth; reporting relative improvements or normalized scores; interpreting a null or non-significant result or making an equivalence claim; or deciding what a probe, feature, or intervention result actually shows.
- *Advises:* prefer existing datasets and verify the behavior on actual examples; ground truth must measure the claimed property, and a judge is an instrument with errors; keep discovery, fitting, tuning, and confirmation data separate and split by source or template; read effects in raw units, especially against near-zero baselines; non-significance is not equivalence; correlation, recoverability, and intervention answer different questions; an absent effect has many possible causes.

**[Answer measurement](answer-measurement.md)**
- *Read when:* scoring multiple-choice or free-form answers from generated text, especially after fine-tuning or steering; refusals, format breakage, or invalid answers appear; or an effect might come from option order or the parser.
- *Advises:* parsing is part of the measurement; common regex failures and silent coercion of invalid answers; a three-way CORRECT / INCORRECT / OTHER judgment with a frozen judge configuration; report invalid-answer rates per arm; rotate option order to expose position bias; log-probability scoring cannot detect corrupted outputs; diagnose the parser before attributing a null result to the model.

**[Image preprocessing](image-preprocessing.md)**
- *Read when:* evaluating or probing vision models, writing or inspecting ImageNet-style evaluation transforms, collecting vision activations, or comparing internal units with concept reference images.
- *Advises:* use the model's native processor when reporting its accuracy and a shared convention for probing frozen backbones; `Resize(256)` and `Resize((256, 256))` crop different patches from non-square images; training augmentation should not leak into evaluation; build concept references from relevant regions; surface a preprocessing ambiguity rather than resolving it silently.

**[Training and execution](training-and-execution.md)**
- *Read when:* monitoring a training run; loss becomes NaN, diverges, stays flat, or is noisy; a process is alive but it is unclear whether it is learning; logs are unreachable; or a run fails with OOM, import, missing-path, shape, or hook errors.
- *Advises:* process health is not training quality; which training signals to watch and how to respond to each; avoid stopping on the first noisy checkpoint; a practical monitoring cadence for long runs; concrete remedies for common failures; do not silently substitute a different model or dataset; a fixable implementation problem is not a scientific negative; visible hardware is not authorization to use all of it.

**[Research judgment](research-judgment.md)**
- *Read when:* assessing whether a question is worth pursuing or new relative to the closest findings; choosing between method routes or considering added components; designing controls or ablations; deciding whether to repair or abandon an unsuccessful attempt; weighing criticism from another model; or writing up findings.
- *Advises:* keep the original problem in view; compare with the nearest findings rather than the nearest topics; prefer the smallest adequate method and make it concrete; pair each plausible mundane explanation with a comparison that distinguishes it; design ablations that answer concrete questions; separate implementation failure from evidence against a hypothesis; accept valid criticism and resist drift away from the original question; explain findings with concrete quantities and separate observations from interpretation.

Read the relevant document before applying its advice; these summaries are an index, not the experience itself. Multiple notes can help the same question. If you already know the needed topic, open it directly. Load additional notes when the scientific question or observed failure changes, rather than loading the whole collection every time.

For steering, site selection and coefficient tuning are interlocking: tune strength for a candidate site set and re-tune when changing sites. For fine-tuning or steering followed by multiple-choice evaluation, read the answer-measurement advice too: the intervention can change answer formatting as well as behavior.

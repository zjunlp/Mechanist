---
name: mechanism-explore
description: 'Macro-level strategic directions for investigating the *mechanism* behind a model behavior — the downstream half of the project''s mission (mine LLM behaviors, then explain the mechanism behind them). Use once a phenomenon is observed in a model — whether already established/known or freshly mined by `/mechanism-behavior-discovery` — and the task is to choose *how* to investigate the internal cause. It is the strategy layer above the concrete method families in `/mechanism-skills`, organized around six parallel research directions — **Location**, **Causal Intervention**, **Tuning & Editing**, **Formation Tracing**, **Unit Interpretation**, **Decision Auditing** — plus how to combine them into strategies and how to make the method itself a contribution rather than an off-the-shelf chain. Domain-general: it prescribes strategy, not any single model, modality, or method.'
---

# Mechanism — Explore

The explanation half of the loop. Given a validated phenomenon, this skill is the **macro-level plan** for finding the mechanism behind it. It decides **which strategic directions to pursue, and in what order** — the families in **`/mechanism-skills`** execute the chosen directions.

> A mechanism claim is **causal**: "component X is responsible for behavior B" means intervening on X changes B in the predicted, specific way. *Locating* X is necessary but not sufficient — only intervention earns the word "mechanism."

## When to Use

A phenomenon is in hand — whether already established/known or handed off from `/mechanism-behavior-discovery` — and the question is now *where* it is computed, *whether* that component causes it, *whether* it can be tuned for use, *how* it formed, *what it means*, or *whether the model's decision is trustworthy*. Do **not** use this skill to find a phenomenon (that is `/mechanism-behavior-discovery`), nor as a substitute for the chosen family's method file in `/mechanism-skills`.

## The Six Research Directions

Six parallel directions for explaining a model. They are coordinate — each answers a different question and stands on its own — and they also chain into strategies (see below). **Location** is typically the natural entry point for the others, since most directions act on a component you have first located.

### 1. Location — *where* the behavior is computed

At inference time, find which internal function component for the behavior: a **layer**, a **neuron** (or head), a **circuit**, or a **featur/activation direction**. Use cheap correlational/attribution methods (probing, vocabulary projection, magnitude, attribution, circuit discovery, dictionary learning). Output: a ranked shortlist of candidates. This is **correlational** — a located component is a hypothesis, not yet the cause.

### 2. Causal Intervention — *whether* the component causes the behavior

Intervene on the located component and check the target behavior moves as predicted (amplify → behavior strengthens, ablate → behavior gone). Tools: **ablation**, **activation patching** (sufficiency / localization), **steering** (dose-response on a represented quantity). Always report **sign**, **magnitude / dose-response**, and **specificity** (a matched control component does nothing; off-target behavior intact). This is what promotes *located* to *mechanism*.

### 3. Tuning & Editing — *use* the component to improve capability

Directly tune or edit the located component to raise downstream task ability (steering vectors, parameter-space task vectors / weight editing, targeted fine-tuning). Distinct from direction 2: intervention is **diagnostic** (does X cause B?), tuning is **applied** (use X to make B better). Judged by downstream gains, not a causal verdict.

### 4. Formation Tracing — *how* the component formed (training-time)

Move from inference-time to training-time: (a) how the component **forms over training** (when it emerges, how it sharpens across checkpoints); (b) which **training data** is critical to it (influence functions / data attribution, data-ablation re-training). Explains the component's origin. The most expensive direction — use only when *genesis* is part of the claim.
> Reference: *Mechanistic Data Attribution: Tracing the Training Origins of Interpretable LLM Units.*

### 5. Unit Interpretation — *what* an internal unit means

Decode the human-understandable concept carried by an internal unit (neuron / feature / direction) — turning an opaque activation into a named meaning.

- **Dictionary decomposition.** Use a **sparse autoencoder (SAE)** to factor activations into monosemantic features and read off each feature's concept. When no SAE is available (or training one is too costly), use **ICA** to recover interpretable directions directly from activations as a lightweight substitute.
- **Model-explains-model (auto-interpretation).** Have a stronger model write and score natural-language explanations of a weaker model's units (e.g. a frontier LLM labeling another LM's neurons), giving scalable, automatically-validated descriptions.
- **Cross-modal interpretation.** For non-text models, map internal units to concepts in a shared multimodal space and surface them as readable visual/textual descriptions — e.g. **SemanticLens** for vision models.
> References: *Mechanistic understanding and validation of large AI models with SemanticLens* (vision); language-model-explains-language-model auto-interpretation work; InterPLM: discovering interpretable features in protein language models.

### 6. Decision Auditing — *whether* the model's decision is trustworthy

Trace the evidence a model relies on for a specific decision, then judge that evidence against domain knowledge. Two complementary uses:

- **Validate decision-making.** Audit whether a decision rests on valid, task-relevant features rather than spurious correlations (background artifacts, dataset bias, shortcut cues). By mapping each contributing unit to a concept (direction 5) and checking it against what *should* matter, you catch "right answer, wrong reason" before deployment — e.g. SemanticLens-style audits that expose the concepts driving a prediction and flag illegitimate ones.
- **Discover novel decision bases.** The same trace can surface features the model uses that humans had not recognized as relevant — turning interpretability into a source of new domain knowledge rather than only a check on old knowledge.
> Reference: *Using Interpretability to Identify a Novel Class of Alzheimer's Biomarkers.*

## Combining into Strategies

Any of the six directions can stand alone, and they also chain. Pick the shortest combination that answers your question. **When the user states an explicit requirement, that requirement takes precedence over novelty and resource computations** — read what they asked for and pick the chain that delivers it. For example, if the user explicitly wants to *drive the model to produce a target output*, go straight to **Location (of the target feature) → Causal Intervention**, rather than defaulting to a broader survey.

| Strategy | Mechanism Directions | Specific Case |
|---|---|---|
| Mechanistic evidence | Location → Causal Intervention | "X causally drives B." |
| Capability / editing | Location → Tuning & Editing | "Tuning X improves downstream task T." |
| Complete account | Location → Causal Intervention → Formation Tracing | "X drives B, and forms at stage S from data D." |
| Explaining a model | Unit Interpretation | "Unit X encodes concept C." |
| Decision reliability | Unit Interpretation → Decision Auditing | "Decision D relies on C — valid (or spurious / novel)." 

## Method Innovation — Earning Novelty on the *How*

The six directions and the five strategies are the field's standard vocabulary; on their own they establish competence, not contribution. **If the method section of your plan could be copy-pasted onto a different phenomenon with only the nouns changed, the method is not part of the contribution** — and a claim whose novelty rests entirely on its phenomenon is one replication away from being obsolete.

So each mechanism plan names, in one line, **what about this investigation has not been done this way before**. One of the moves below is enough; the point is that the line exists and that the experiments turn on it.

1. **Adapt the instrument to the phenomenon.** The standard probe usually measures a quantity adjacent to the one the claim is about — a linear probe reads *decodability*, not *use*; an ablation reads *necessity in this forward pass*, not *responsibility*. Name the mismatch, then close it: change what the probe predicts, the population it is fit on, the intervention's granularity, or when in the pipeline it is applied. That modification, stated as a delta against the standard recipe, is the methodological contribution.

2. **Import a paradigm from another discipline, not a metaphor.** Analogies to biology or physics are decorative; their *experimental apparatus* is not. Each of these transfers a design that yields measurements this field does not currently make:
   - **Genetics** — knockout **and rescue** (necessity plus sufficiency in one design), epistasis (does ablating A change B's effect?), complementation, heritability decomposition across "generations" of distillation.
   - **Pharmacology / epidemiology** — dose–response curves with an EC50, time-to-event and survival analysis for a trait that decays, washout and re-challenge designs, exposure–outcome with matched cohorts.
   - **Psychophysics** — staircases and detection thresholds, just-noticeable differences, signal-detection d′ separating sensitivity from bias.
   - **Econometrics** — instrumental variables where a clean intervention is impossible, difference-in-differences across checkpoints, formal mediation analysis to split direct from indirect effect, regression discontinuity at a training-stage boundary.
   - **Information theory** — channel capacity and rate–distortion for how much of a quantity a representation can carry, minimum description length for whether a probe is reading structure or memorizing.
   - **Physics** — order parameters, phase diagrams and critical points, finite-size scaling across model scale, perturbation–response (susceptibility) measurement.
   - **Ecology / evolution** — competition for a shared resource, carrying capacity, selection–drift decomposition across training.
   
   State the import concretely: *which design, mapped onto which internal object, measuring which quantity*. "Inspired by neuroscience" is not an import.

3. **Rescue, not just ablation.** Necessity is cheap and ambiguous — most ablations degrade something. The design that earns the word *mechanism* removes the component and then **restores the behavior by re-supplying it alone**, in a model or condition where it was absent. Sufficiency evidence is rarer than necessity evidence here, and building the rescue arm is often the whole methodological contribution.

4. **Invent the unit the phenomenon lives in.** The standard units — layer, head, neuron, SAE feature, direction — are inherited, not derived. When a phenomenon fits none of them (it is a relation between two models, a property of an update, a statistic of the training corpus, a trajectory across checkpoints), define the unit it *is* described by, then say how it is measured and intervened on. A new well-defined unit outlives the claim it was built for.

5. **Move the measurement to a stage nobody measures.** Almost all method effort is spent at inference time on a finished model. The gradient at the moment of the update, the difference between two checkpoints, the geometry of the weight delta, the data point's influence — all measurable and comparatively unexplored, and a claim about how something *forms* is not testable at inference time at all.

6. **Build the two-system design.** Standard methods assume one model in one forward pass. Relational phenomena — teacher and student, base and finetune, model and its own earlier context, monitor and monitored — need designs that cross the systems: shared-subspace estimation, cross-model patching, aligning two representation spaces before intervening, matched-pair controls where the pairing is the manipulation. This is where the field's toolkit is thinnest and a modest step is most visible.

7. **Make the mundane rival a measurement, not a caveat.** Every mechanism claim has boring nulls (memorization, surface form, tokenization, position, capability confounds), usually handled by a sentence in the limitations. Turning one into its own *measured quantity*, with a control that estimates how much of the effect it accounts for, converts a weakness into a result — and often into the paper's most cited number.

**The check.** Before committing a strategy, write two sentences: *the standard way to investigate this phenomenon*, and *what this plan does instead, and what that buys*. If the second is empty, or is only "we also run an SAE", the plan is a competent execution of someone else's method — go back to the moves above. Method innovation is judged like behavioral novelty: not by how sophisticated it sounds, but by whether it produces a number that could not have been produced before.

There is **no default** — choose the strategy (or a few candidates) from the user's intent, and let that choice define the claim you are trying to land. The table fixes the *shape* of the argument; it does not supply a method, and a chain of off-the-shelf steps (train a probe, ablate the top head, report a drop) is the mechanism-side equivalent of a domain transfer — correct, runnable, and not a contribution. Each row is self-contained: Location + Causal Intervention locates the head / feature carrying the behavior, then ablates or steers it to confirm it causally drives the behavior — a complete finding on its own, so do not bolt on a direction the user's question does not need. If a strategy is already specified by the task or plan, follow that requirement.

## Goal

Based on the user's intent, design a few suitable mechanism-research strategies and directions for them — **each one a strategy from the table plus the one line of § Method Innovation that says what it does differently**. A direction handed off without that line is incomplete, however well the chain is chosen. The common strategies are the five in the table above: **Mechanistic evidence** (Location + Causal Intervention), **Capability / editing** (Location + Tuning), **Complete account** (Location + Causal Intervention + Formation Tracing), **Explaining a model** (Unit Interpretation), and **Decision reliability** (Decision Auditing).

**Keep the mechanism claim at the right altitude — hypothesize the *kind* of component, not its exact identity.** The claim should assert that *some* internal component (a layer / neuron / head / circuit / feature direction) carries or causes the target behavior — not pin down *which specific* layer or *which exact* feature. Those concrete identities are precisely what the experiment stage is meant to discover (the Location + Causal Intervention work); fixing them at claim time pre-empts the experiments and risks committing to a specific the runs may not bear out.

**If a record of mechanism directions already investigated for this same phenomenon (with their outcomes) is provided**, propose a direction from the **candidate set = untried directions ∪ directions left `inconclusive`**. Do **not** re-propose a direction already shown to **hold (confirmed)** or already **refuted** — those are settled. A direction left **`inconclusive`** is *not* settled (the test failed to decide); it is a legitimate retry candidate, ideally with a stronger test. Build on what the prior outcomes established.

**An explicit user/plan-specified direction overrides this avoidance.** Per the "If a strategy is already specified by the task or plan, follow that requirement" rule above: when the task pins a direction, use it directly rather than picking a complementary untried one. Deciding whether to honor a pin that collides with an already-`confirmed`/`refuted` direction is the **caller's** responsibility, not this skill's — act on whatever honor-or-replace decision the caller hands you, and do **not** raise that confirmation yourself.
# Mechanism — Explore

The explanation half of the loop. Given a validated phenomenon, this skill is the **macro-level plan** for finding the mechanism behind it. It decides **which strategic directions to pursue, and in what order** — the families in **the mechanism method library** execute the chosen directions.

> A mechanism claim is **causal**: "component X is responsible for behavior B" means intervening on X changes B in the predicted, specific way. *Locating* X is necessary but not sufficient — only intervention earns the word "mechanism."

## When to Use

A phenomenon is in hand — whether already established/known or handed off from `behavior discovery` — and the question is now *where* it is computed, *whether* that component causes it, *whether* it can be tuned for use, *how* it formed, *what it means*, or *whether the model's decision is trustworthy*. Do **not** use this skill to find a phenomenon (that is `behavior discovery`), nor as a substitute for the chosen family's method file in the mechanism method library.

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

Any of the six directions can stand alone, and they also chain. Pick the shortest combination that answers your question.

| Strategy | Mechanism Directions | Specific Case |
|---|---|---|
| Mechanistic evidence | Location → Causal Intervention | "X causally drives B." |
| Capability / editing | Location → Tuning & Editing | "Tuning X improves downstream task T." |
| Complete account | Location → Causal Intervention → Formation Tracing | "X drives B, and forms at stage S from data D." |
| Explaining a model | Unit Interpretation | "Unit X encodes concept C." |
| Decision reliability | Unit Interpretation → Decision Auditing | "Decision D relies on C — valid (or spurious / novel)." 

There is **no default** — choose the strategy (or a few candidate strategies) from the user's intent, and let that choice define the claim you are trying to land. Each row is self-contained: e.g. Location + Causal Intervention locates the head / feature carrying the behavior, then ablates or steers it to confirm it causally drives the behavior — a complete finding on its own, so do not bolt on a direction the user's question does not need. If a strategy is already specified by the task or plan, follow that requirement.

# Belief Localization in Pretrained Language Models

## Behaviour Description

This project studies **belief ability** in pretrained language models.

Belief ability refers to a model's capacity to represent and reason about a proposition under context. The same proposition may need to be interpreted either as an objective fact about the world or as an agent's mental state.

We focus on two core belief abilities:

* **Personal belief**: tracking the objectively true state of the world.
* **Attributed belief**: tracking an agent's mental state, even when it conflicts with reality.

World knowledge is used only as a **control**, to verify that belief-circuit interventions do not simply destroy factual knowledge or general language modeling ability.

### Core Frames

#### World Knowledge Control (`world_knowledge`)

```text
The sky is _____.
→ blue
```

#### Personal Belief (`personal_belief`)

```text
James believes that the sky is green. In reality, the sky is _____.
→ blue
```

#### Attributed Belief (`attributed_belief`)

```text
James believes that the sky is green. James thinks that the sky is _____.
→ green
```

False-belief contexts are used so that personal belief and attributed belief remain behaviorally separable.

---

## Claims

### Claim 1: Scale-Dependent Emergence

Personal belief and attributed belief exhibit distinct emergence patterns across model scales.

### Claim 2: belief heads Localization

Personal belief and attributed belief are implemented by distinct, causally separable attention-head circuits.

### Claim 3: Formation Window

Belief-related circuits exhibit distinct developmental trajectories during pretraining.

### Claim 4: Dynamic Controllability

The attention heads identified in Claim 2 are not only causally necessary but also causally controllable. A lightweight per-frame router can dynamically amplify these heads to selectively enhance personal belief and attributed belief while leaving world knowledge unchanged, providing an application-level demonstration that localized belief circuits can be turned into a controllable inference-time switch.

---

## Resources

### Data

1. Belief datasets are located at:

```text
/data/xuhaoming/belief_loc/data/derived/belief_core/
```

| Frame               | File                      | Size | Role                        |
| ------------------- | ------------------------- | ---: | --------------------------- |
| `world_knowledge`    | `reality.jsonl`           |  227 | factual control             |
| `personal_belief`      | `believe_truth.jsonl`     |  681 | core belief frame           |
| `attributed_belief`     | `follow_belief.jsonl`     |  681 | core belief frame           |


Use the provided datasets without modifying prompts or labels.

Use the full dataset for Claim 1 behavioral evaluation and Claim 3 trajectory evaluation.

For Claim 2 head localization, Fisher computation, head ablation, and related causal localization analyses, use only the third-person subset:

```text
person in {James, Mary}
```

This gives 454 items per belief frame:

```text
227 James + 227 Mary
```

Do not use first-person examples for Fisher localization or head ablation.


2. Pretraining Corpus (Perplexity Corpus) are located at: 

```text
/mnt/quarkfs/share_model/Ptyhia_data/pile-standard-pythia-preshuffled/
```

Use the pretraining corpus to evaluate general language modeling ability using perplexity (PPL) as the metric.

### Models

Model directory:

```text
/mnt/quarkfs/share_model/Ptyhia
```

Use the following final-checkpoint models:

* `pythia-410m`
* `pythia-1b`
* `pythia-2.8b`

Intermediate checkpoints are located at:

```text
/mnt/quarkfs/share_model/Ptyhia/pythia-{size}-checkpoints/
```

---

## Research Questions and Required Outcomes

Run the experiment in the order below. Later steps should only use artifacts produced by earlier steps.

Keep the study within the Pythia family. Do not turn the model comparison into a cross-architecture generalization test.

---

### 1. Behavioural Evaluation

Evaluate all models on all belief-related tasks.

Use the full dataset for each belief-related task in this behavioral evaluation.

#### Metrics:

For each sample, compare the gold and distractor continuations:

```text
correct iff sum_t log P(gold_t) > sum_t log P(distractor_t)
```

* Sum log-probabilities over completion tokens only.
* Do not include prompt tokens.
* Do not apply length normalization.
* Use the tokenizer matching the checkpoint.
* Evaluate gold and distractor under identical prompt conditions.

#### Require: 

The experiment should investigate how attributed belief and personal belief behave across model scales, including whether one belief ability exhibits stronger scale dependence and whether the scaling behavior is monotonic or non-monotonic.

---

### 2. Belief Heads Localization

#### Methods

Use Fisher information matrix, refering to this paper "Sensitivity Meets Sparsity: The Impact of Extremely Sparse Parameter Patterns on Theory-of-Mind of Large Language Models" 

Use three independent signals:

| Signal | Data |
|---|---|
| `F_attributed` | `attributed_belief`, James + Mary only |
| `F_personal` | `personal_belief`, James + Mary only |
| `F_knowledge` | `world_knowledge` |

Construct two independent target-specific Fisher masks or views:

```text
Mask_attributed = top 0.1% of F_attributed AND NOT top 1% of F_knowledge
Mask_personal  = top 0.1% of F_personal  AND NOT top 1% of F_knowledge
```

Use the Fisher signals to obtain target-specific candidate heads or rankings, then use attention-head zero-ablation to search for the smallest head set that satisfies the causal, specificity, baseline, and PPL criteria below.

#### Require:

The experiment should determine whether attributed belief and personal belief are supported by causally identifiable attention-head circuits. For models passing the above-chance criterion, identify candidate heads using the third-person localization subset, evaluate their causal effects through zero-ablation on the same localization subset, and report both baseline controls for each evaluated head set:

* `20` random-head baseline mean ± `2σ`, matched by head count.
* `20` random-mask baseline mean ± `2σ`, matched by parameter count.

Select the final belief head set using these fixed thresholds:

* Target behavior drop must be at least `0.30` absolute accuracy.
* The effect must be outside the `20`-random-head baseline `2σ` band.
* Each off-target behavior drop, including the other belief behavior and `world_knowledge`, must be at most `0.10` absolute accuracy.
* PPL on the pretraining-corpus control must be no more than `clean × 1.05`.

A valid belief circuit should selectively impair its corresponding target behavior while preserving the off-target behaviors and general language modeling ability under the thresholds above. If no head set satisfies all thresholds, report the claim as not localized or only partially localized rather than changing the thresholds.

---

### 3. Belief Formation Window Analysis

#### Methods

Analyze intermediate checkpoints of `pythia-1b` to study the emergence of belief abilities during pretraining.

Conduct two evaluations across checkpoints:

1. **Behavioral evaluation**: measure `world_knowledge`, `personal_belief`, and `attributed_belief` performance on the full datasets at different `pythia-1b` training steps to characterize when each ability emerges.

2. **Circuit intervention evaluation**: using the `pythia-1b` `personal_belief` and `attributed_belief` head sets identified in Claim 2, separately zero-ablate each head set at every `pythia-1b` checkpoint. For each ablation condition, measure `world_knowledge`, `personal_belief`, and `attributed_belief` performance, so the causal trajectory records both the target effect and the cross-behavior controls for each belief head set.

#### Require:

The experiment should determine whether personal belief and attributed belief emerge at different stages of pretraining. The analysis should report the behavioural trajectory and causal intervention trajectory of each belief ability, and identify the corresponding formation windows based on predefined emergence criteria.

### 4. Dynamic Head Amplification

#### Methods

Use the belief heads identified in Section 2 to construct an inference-time controller that dynamically modulates belief-related circuits during the model forward pass.

The controller should:
- infer the current task frame (`world_knowledge`, `personal_belief`, or `attributed_belief`) from the model's internal representations at layers before the identified belief heads;
- amplify the corresponding belief circuit within the same forward pass based on the inferred frame;
- preserve the base model behavior for unrelated frames, especially leaving `world_knowledge` samples unchanged.

The frame classifier should be trained only on `belief_core`:

```text
/data/xuhaoming/belief_loc/data/derived/belief_core/
````

and evaluated on the out-of-distribution belief holdout:

```text
/data/xuhaoming/belief_loc/data/derived/belief_holdout/
```

The holdout should contain unseen propositions and categories to test whether the internal frame signal generalizes beyond training examples.

Compare the controller against an oracle prompt-hint baseline, where the ground-truth frame is explicitly provided through a natural-language instruction. The prompt hints should state the task frame clearly:

* For `world_knowledge`, ask the model to extract and answer with the factual state of the proposition.
* For `personal_belief`, ask the model to ignore others' beliefs and answer according to its own belief about reality.
* For `attributed_belief`, ask the model to track the named person's belief and answer according to that person's belief.

This baseline measures the benefit of internal circuit control beyond prompt-level task specification.

#### Require:

The experiment should determine whether localized belief circuits support controllable amplification and whether the internal frame signal reflects generalizable belief states rather than memorized content.

A valid controller should demonstrate:

1.  **Frame generalization**: the frame classifier should achieve reliable classification on unseen categories using internal model representations, showing that it captures task-level belief information rather than text-level shortcuts.

2.  **Intervention effectiveness**: circuit amplification should improve belief behavior with positive item-level net improvement while maintaining low degradation on previously correct predictions and preserving `world_knowledge` and general model capability.

Report intervention outcomes using item-level metrics, including recovery of incorrect cases, degradation of correct cases, and net improvement, with comparison against the oracle prompt-hint baseline.

---

## Goal

Determine whether:

1. Personal belief and attributed belief show distinct scale-dependent emergence patterns.
2. Personal belief and attributed belief are implemented by causally separable attention-head circuits.
3. These circuits are compact or distributed at each model scale.
4. These belief heads form at different stages during pretraining.
5. The same belief heads can be turned into a controllable inference-time switch that selectively amplifies personal belief and attributed belief without harming world knowledge.

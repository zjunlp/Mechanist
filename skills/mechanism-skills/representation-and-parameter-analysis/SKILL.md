---
name: Representation and Parameter Analysis
description: 'Representation and Parameter Analysis interprets and controls a model by directly manipulating its two kinds of internal objects — features (the hidden-state activations produced during a forward pass) and weights (the parameters of the target model). The analysis side relies on standard linear-algebra tools applied straight to these objects: techniques such as PCA, mean-difference, or simple linear classifiers are run over collected features (e.g., from contrastive prompt pairs) or over weight differences between a fine-tuned and a pre-trained checkpoint, in order to extract a small set of meaningful directions. The control side then operates directly through arithmetic on those objects: adding such a direction back into the features steers behavior at inference time, while adding, subtracting, or combining task-level weight differences edits the model in one shot — so that interpretability findings translate into behavioral control without any retraining.'
---

## Advantage

Features and weights provide a single low-dimensional handle for both analysis and control, with no retraining needed. Once a concept direction is identified, reading becomes a projection and editing becomes an addition — the same primitive supports monitoring, classification, steering, model editing, and capability composition. This is far cheaper than the intervention sweeps in Causal Attribution or full fine-tuning. Linearity also makes operations compose: directions can be subtracted to contrast concepts, and task-level weight edits can be added or negated to mix in or remove capabilities, each step with a clear semantic meaning.

## Limitation

The approach assumes target concepts are linearly encoded. When the encoding is non-linear, distributed, or entangled with other concepts, a single direction misses much of the signal and additive edits spill into neighboring features. Results are also basis- and checkpoint-specific — directions rarely transfer across models — and large edit strengths push the model off-distribution, breaking the linear regime the method relies on.

## Submethods

The category typically takes 3 forms:

- **Steering Vectors**:
A focused instance of directly editing features at inference time: steering directions are built from contrastive activation pairs (Contrastive Activation Addition / CAA) and added to a chosen layer's residual stream during generation. It is especially useful for behavioral control of chat models, where concepts of interest are easy to frame via paired examples of desired vs. undesired behavior.
You can find a demo for this method in ./steering-vectors. This demo shows steering_vectors: Work with Llama 2 model steering using Contrastive Activation Addition (CAA) for behavioral control, including generating steering vectors, evaluating model behavior, and analyzing activation patterns.

- **Representation Engineering**:
Reads, monitors, and edits LLM behavior by extracting concept directions from hidden-state features using contrastive prompt pairs. RepReading projects features onto the concept direction to detect attributes such as truthfulness, emotion, fairness, harmlessness, or memorization, while RepControl writes the same direction back into the residual stream during generation to steer the model toward or away from the concept.
You can find a demo for this method in ./representation-engineering. This demo shows representation-engineering: Use this skill when working with Representation Engineering (RepE) for AI transparency, monitoring, or controlling internal representations of large language models including truthfulness detection, emotion control, harmlessness steering, and memorization analysis.

- **Parameter-Space Task Vectors**:
Lifts the same idea to weight space and edits weights directly: a *task vector* is the displacement between a fine-tuned checkpoint and its pre-trained checkpoint, and arithmetic on these vectors — addition for multi-task composition, negation for unlearning, and analogy-style combinations across related tasks — modifies model behavior without any further training.
You can find a demo for this method in ./parameter-space-task-vectors. This demo shows task-vectors: Use this skill when working with task arithmetic for editing neural network models, including creating task vectors from pre-trained and fine-tuned checkpoints, combining them via arithmetic operations (negation, addition, analogies), and applying them to CLIP vision models for multi-task learning.

---
name: gradient-detection
description: 'Gradient Detection methods localize influential internal objects by scoring them with the sensitivity of a scalar target $F(x)$ (e.g., a logit, margin, or loss) with respect to an object $o_j$: $s_j(x) = \phi(\nabla_{o_j} F(x), o_j)$, where common instantiations include the gradient norm $s_j = \|\nabla_{o_j} F(x)\|$ and the gradient-input score $s_j = \nabla_{o_j} F(x)^\top o_j$. These scores serve as fast, first-order proxies for intervention effects. '
---

## Advantage

Gradient Detection can be applied to many types of objects (inputs, activations, parameters) without additional training. It only requires a backward pass, making it efficient for quickly ranking important components. Compared with exhaustive interventions, it can produce rankings with a relatively small number of backward passes, making it practical as an initial localization step when the candidate set is large.

## Limitation

Gradients provide a local proxy, not causal necessity: salience can be offset by downstream computation, and finite interventions may depart from first-order effects in non-linear regimes. For these reasons, gradient-ranked objects are typically paired with Causal Attribution to validate whether the identified objects are genuinely responsible for the target behavior.

## Submethods

Given object categories, the method typically takes three forms:

- **Inputs and Layer-wise States**:
For input embeddings $x_i^0$ and the residual stream state $x^l$, gradients directly quantify how sensitive $F(x)$ is to changes in specific prompt components and their propagated representations. In practice, one computes $\nabla_{x_i^0} F(x)$ or $\nabla_{x^l} F(x)$ and derives token-level influence, such as the gradient norm $\|\nabla_{x_i^0} F(x)\|$, the gradient–input score $\nabla_{x_i^0} F(x)^\top x_i^0$, or integrated gradients. Aggregating these scores across positions $i$ (optionally across layers $l$) yields a ranked view of which tokens or contextual spans are most responsible for a target output, as used to analyze CoT prompting and which depth regions contribute most strongly to the formation of that output, with closely related layer-/token-saliency signals also supporting dynamic token pruning and inference-time steering.
You can find a demo for this method in ./inputs-and-layer-wise-states.This demo shows layer-gradient: Analyze and visualize layer-wise gradient behaviors in LLMs during fine-tuning for fast vs slow thinking tasks, calculate gradient statistics, and understand training patterns across different model layers

- **Intermediate Outputs**:
Beyond inputs, Gradient Detection can score internal computational units whose activations vary with the input.
You can find a demo for this method in ./intermediate-outputs. This demo shows relp: Use this skill when working with circuit discovery in language models, mechanistic interpretability, activation patching, attribution patching, or Layer-wise Relevance Propagation (LRP) for neural network analysis

- **Parameters**:
Because $F$ is differentiable with respect to model weights, Gradient Detection can score parameters at multiple granularities. At the block level, common targets include attention projection matrices $\mathbf{W}_{Q/K/V/O}^{l,h}$ and FFN matrices $\mathbf{W}_{\text{in/out}}^l$. Gradients such as $\nabla_{\mathbf{W}_Q^{l,h}} F(x)$ can be turned into scalar salience measures (e.g., $\|\nabla_{\mathbf{W}} F(x)\|$) to rank influential attention/FFN modules. At finer granularity, the same principle is used to select influential individual weights or structured blocks.
You can find a demo for this method in ./parameters. This demo shows linguistic-regions-llm: Use this skill when working with linguistic region analysis in Large Language Models, including data preprocessing for multilingual training, region-based model training with DeepSpeed, and extracting/visualizing linguistic regions in transformer models



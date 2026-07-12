---
name: Vocabulary Projection
description: Vocabulary Projection methods interpret internal model states by projecting them through the unembedding matrix to obtain a distribution over the vocabulary. The core idea is that the unembedding matrix, which maps the final hidden state to output logits, can serve as a universal decoder for intermediate states throughout the model. By inspecting the top-ranked tokens of the resulting distribution, researchers can directly read off the semantic content encoded in any internal object — such as a residual stream state or an attention head output — in terms of the model's output vocabulary.
---

## Advantage

It provides a zero-shot interpretation method that is computationally efficient and intuitive. Unlike Probing, it does not require collecting a labeled dataset or training a separate classifier, allowing for immediate inspection of any model state.

## Limitation

The primary limitation is the assumption that intermediate states exist in the same vector space as the output vocabulary (basis alignment). While this often holds for the residual stream due to the residual connection structure, it may be less accurate for components inside sub-layers (like FFN and MHA) or in models where the representation space rotates significantly across layers. Consequently, results should be interpreted as an approximation of the information that is linearly decodable by the final layer.

## Submethods

Given object categories, the method typically takes 3 forms: 

- **Residual Stream State**:
Projecting the residual stream state allows researchers to trace the layer-wise evolution of predictions and identify the crucial layers where specific concepts emerge.
You can find a demo for this method in ./residual-stream-state. This demo shows tuned-lens: Use this skill when working with transformer model interpretability, analyzing layer-by-layer predictions, training tuned lenses to understand intermediate representations, or peeking into iterative computations of transformers

- **Attention Head Output**:
Applying projection to the output of individual heads reveals the specific information (e.g., copied names or next-token candidates) that a head transmits to the residual stream. This has been instrumental in identifying functional heads in mechanistic studies.
You can find a demo for this method in ./attention-head-output. This demo shows logitlens4llms: Use this skill when you need to analyze and interpret the internal workings of large language models layer by layer, visualize hidden states and predictions across transformer layers, or understand how models like Llama-3.1-8B and Qwen-2.5-7B make predictions at each layer using the Logit Lens technique

- **Neuron Value Weight**:
From a point of view, FFNs operate as key-value  memories. By projecting the value weight vector into the vocabulary, one can see which tokens are promoted by a specific neuron. Individual neurons often boost semantically related clusters (e.g., “press”, “news”, “media”), suggesting that FFNs refine predictions by composing these pre-learned semantic distributions.
You can find a demo for this method in ./neuron-value-weight. This demo shows ff-layers: Analyze transformer feed-forward layers as key-value memories, extract activations, identify trigger examples, and compute key-value agreement in transformer language models

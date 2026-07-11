---
name: Multi-Modal Interpretability
description: 'Multi-Modal Interpretability methods explain *vision* and *vision-language* models by linking each internal unit (a convolutional neuron, attention head, residual-stream channel, or SAE feature) to a *natural-language concept* drawn from an external concept set $\mathcal{C}$. The unifying construction is a similarity score $s(u, c) = \langle \mathbf{a}_u, \mathbf{t}_c \rangle$ between a per-unit activation summary $\mathbf{a}_u$ — collected over a probing image set — and a text-side embedding $\mathbf{t}_c$ produced by an aligned multi-modal model such as CLIP. Ranking the concepts by $s(u, \cdot)$ yields a human-readable label for $u$, turning vision representations from anonymous tensors into named, attributable concepts. The two submethods below are NOT mutually exclusive — for building a per-component concept vector from a component''s highly-activating reference images, select BOTH together (CRP for cropping, CLIP-Dissect for embedding); see "Compose the two".'
---

## Advantage

By delegating the language side to a pre-trained vision-language model, multi-modal interpretability avoids the labor-intensive step of crowdsourcing per-neuron labels and scales to *open-vocabulary* concept sets — any text the alignment model recognises is a candidate label. The resulting concept-level explanations compose naturally with attribution: one can mask, swap, or steer a labelled neuron / SAE feature and observe the downstream effect on predictions, producing concept-conditional heatmaps and feature-visualisation videos that describe both *what* a unit represents and *how* it is used.

## Limitation

Explanations inherit the biases and blind spots of the underlying alignment model: anything CLIP cannot embed cleanly (fine-grained categories, novel domains, low-resource languages, abstract qualifiers) yields noisy or empty concept rankings. Probing-image and concept-set selection also matter — different reference distributions can label the same neuron differently, so reported descriptions should always be read together with the concept set used. Finally, a high similarity score localises a concept *correlationally*; whether the unit is *causally* responsible for the model using that concept still requires interventional follow-up.

## Submethods

The category typically takes two forms:

- Concept-Set Neuron Description (CLIP-Dissect):
A scalable, training-free pipeline that automatically labels neurons in any vision DNN. For each neuron $u$, one collects its activations over a probing image set, summarises them into $\mathbf{a}_u$, and selects the concept $c \in \mathcal{C}$ whose CLIP text-embedding is most similar to the visual signature of those high-activating images. The resulting per-neuron descriptions cover the entire network — convolutional and transformer-based image classifiers alike — and let researchers compare neuron meanings across architectures, layers, and probing distributions.
You can find a demo for this method in ./clip-dissect. This demo shows clip_dissect: Use this skill when you need to automatically describe or interpret the functionality of individual neurons in deep neural networks (DNNs) using CLIP-based semantic analysis, perform mechanistic interpretability research on vision models, dissect convolutional or transformer-based image classifiers, identify what visual concepts activate specific neurons, or compare neuron descriptions across different probing datasets and concept sets.

- Concept Relevance Propagation (Zennit-CRP):
Combines layer-wise relevance propagation (LRP) with *concept-conditional* masks, so that, instead of a single class-attribution heatmap, one obtains a heatmap conditioned on a chosen latent concept (a neuron, channel, or SAE feature). CRP also supports relevance-maximization-driven feature visualisation and attribution graphs that connect input regions → low-level concepts → mid-level concepts → output, exposing the concept hierarchy a PyTorch model uses to make a prediction.
You can find a demo for this method in ./zennit-crp. This demo shows zennit_crp: Use this skill when working with Concept Relevance Propagation (CRP) and Relevance Maximization for explainable AI in PyTorch models, including generating concept-conditional heatmaps, feature visualizations, attribution graphs, and identifying which latent concepts neural networks use for predictions.

## Compose the two when the task is "component → concept vector"

The two submethods above solve different sub-problems and **compose into a single pipeline whenever the goal is to assign each model component a vector in foundation-model semantic space**. Treating them as alternatives in this regime is a common routing mistake — it picks CLIP-Dissect's embedding pipeline but silently drops the cropping refinement that makes the resulting concept vector clean.

The canonical concept-vector pipeline:

1. Forward probing images through the vision model; record per-component activations.
2. For each component, pick its top-K activating images.
3. **(Zennit-CRP)** For each (component, image) pair, compute a concept-conditional CRP heatmap and crop the image to the high-relevance region. This strips the background noise that the foundation encoder would otherwise embed.
4. **(CLIP-Dissect)** Embed each cropped reference image with the multi-modal model (CLIP / SigLIP / DINOv2); average into a per-component vector $\mathbf{v}_c$; cosine-rank concepts (text queries or a concept vocabulary).

Step 4 alone is the CLIP-Dissect pipeline. Step 3 is the Zennit-CRP refinement that materially improves $\mathbf{v}_c$ quality, especially for components whose top-K images carry large irrelevant backgrounds (the default case on natural-image datasets such as ImageNet). Skipping CRP yields a faster baseline but produces measurably noisier concept vectors and degraded channel-against-text-query ranking — the cropping step is a small additional code change with a non-trivial quality gain.

**Select BOTH submethods together whenever the task description matches any of the following**, even if the user does not name both methods explicitly:

- "build / compute per-neuron / per-channel concept vectors $\mathbf{v}_c$"
- "embed activating reference images into CLIP / SigLIP / DINOv2 for concept labeling"
- "represent each model component as a vector in foundation-model semantic space"
- "reproduce SemanticLens-style pipelines" or any reference-image embedding workflow
- "rank neurons / channels against text queries via cosine in foundation-model space"
- "label components by averaging top-K activating image embeddings"

**Select CLIP-Dissect alone** when the task is pure neuron labeling without per-image cropping (e.g., very large concept-vocabulary scans where the cost of per-(component, image) CRP backward passes is prohibitive, or quick first-pass interpretability scans).

**Select Zennit-CRP alone** when the task is explaining a single model prediction (concept-conditional heatmaps, attribution graphs, relevance flows), with no plan to embed reference images into a foundation model.

---
name: Circuit
description: Circuit discovery methods localize the minimal subgraph of a transformer's computational graph (a set of nodes such as attention heads and MLPs, together with the edges that connect them) that is causally responsible for a specific model behavior. Rather than scoring individual objects in isolation, these techniques recover an end-to-end mechanism by jointly identifying which components, and which information pathways between them, must be preserved to reproduce the behavior on a task distribution.
---

## Advantage

Circuit discovery moves beyond per-object localization to deliver a structured, mechanism-level explanation: it returns not only *which* components matter, but *how* they communicate. The resulting circuits are evaluated for faithfulness on a held-out task distribution, so the recovered subgraph can be verified to actually implement the behavior rather than merely correlating with it. This makes circuits the natural unit for downstream analyses such as cross-model comparison, behavior editing, and mechanism-level claims about generalization.

## Limitation

Recovering a circuit is substantially more expensive than scoring isolated objects, because the search space is the set of edges in the computational graph and faithfulness must be checked under interventions. Pure ablation-based approaches scale poorly with model and graph size, while gradient-based approximations trade exactness for speed and can miss edges whose effect is non-linear. Results also depend on the choice of task distribution, counterfactual / corrupted inputs, and the metric used to score faithfulness, so different configurations can yield different "circuits" for ostensibly the same behavior.

## Submethods

Circuit discovery typically takes two forms: exact iterative search via ablation, or fast gradient-based attribution. A third, more recent paradigm — *feature-based replacement models* — replaces dense components such as MLPs with sparse-feature decoders (e.g. transcoders) so that the discovered circuit lives in interpretable feature space rather than over raw neurons; Anthropic's [circuit-tracer](https://github.com/safety-research/circuit-tracer) is a representative open-source implementation. This skill does not ship a dedicated demo for that paradigm — see the `feature-dictionary-learning/transcoder` skill, which links to circuit-tracer.

- E**xact Iterative Search via Ablation**
A typical approach is Automatic Circuit Discovery (ACDC). This approach treats circuit discovery as an iterative graph-pruning problem. Starting from the full computational graph, ACDC walks edges in reverse topological order and tests each one by patching its endpoint with an activation from a corrupted input; if removing the edge does not degrade the chosen task metric beyond a threshold, the edge is pruned. Repeating this until convergence yields a minimal subgraph that preserves the behavior, providing a causal, intervention-grounded circuit at the cost of many forward passes per edge.
You can find a demo for this method in ./intervention-based-edge-search. This demo illustrates how to perform automated circuit discovery in transformer models by editing the computational graph, running activation patching across edges, and extracting minimal task-specific circuits for mechanistic interpretability studies.

- **Fast Gradient-based Attribution**
A typical approach is Edge Attribution Patching with Integrated Gradients (EAP-IG). Alternatively, EAP-IG approximates the effect of patching every edge in the computational graph using a gradient-based first-order estimate, augmented with integrated gradients to better capture non-linear contributions along the path between clean and corrupted activations. This produces an importance score for every edge in a small number of forward/backward passes, so the circuit can be obtained by thresholding scores instead of running per-edge ablations, dramatically reducing cost while remaining faithful enough to rival exact search.
You can find a demo for this method in ./attribution-based-edge-scoring. This demo shows how to discover and analyze computational circuits in autoregressive transformer language models using Edge Attribution Patching with Integrated Gradients (EAP-IG), evaluate the faithfulness of recovered circuits, and use them for mechanistic interpretability studies.

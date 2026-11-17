---
name: mechanism-methods
description: "Supplement gaps in your detailed, systematic knowledge of mechanistic-interpretability methods. Consult eleven method families, selection guidance, submethods, papers, API references, and code templates when choosing, comparing, implementing, or interpreting a method."
---

# Mechanism Methods

Your knowledge of mechanistic-interpretability methods may be less detailed, concrete, or systematic than that of a specialist who works with them. Familiarity with a method's name can leave gaps in its purpose, assumptions, implementation, alternatives, or evidence limits. This library organizes eleven method families, detailed submethods, papers, API references, and code templates to help fill those gaps.

Consult it when selecting or comparing methods, adapting an implementation, or judging what a result supports. Use the routing overview when the suitable method is unclear, or open a relevant family or submethod directly when you already know what you need. Choose and adapt methods using the research question and available evidence.

## When to Use

Consult these skills whenever the research question is about **how the model computes internally**, not just how it performs externally. Typical triggers:

- A reviewer asks for mechanistic evidence behind a claim
- A claim attributes a behavior to a specific component (layer, head, neuron, feature, weight)
- An experiment needs to isolate *which* internal object drives a behavior
- A method swap is under consideration and the candidate pool should include mechanism-level tools (e.g., swapping a magnitude-based screen for a causal-intervention method)
- A vision or vision-language model needs concept-level explanations rather than raw saliency

For a purely behavioral question (accuracy, robustness, calibration), decide whether internal analysis would add useful evidence before consulting this library.

## Using the library

Compare methods by question, internal object, signal, cost, and evidence limits. Read relevant family and submethod details when useful; a selected method can be opened directly. Consult scripts and API references before adapting an implementation.

Scripts are reference templates, not a tested universal execution interface. Inspect dependencies and demonstration assumptions. Unimplemented measurements report their limitation rather than return fabricated effects. No research-wide file layout or history schema is required.

## Method Families

The eleven families are organized by *what signal they use* to localize internal objects. Each family has its own parent `SKILL.md` with full submethod detail, runnable demo scripts, and paper references — see [Directory Layout](#directory-layout) for the exact file shape. The summaries support selection; linked files supply details.

### 1. Vocabulary Projection — `./vocabulary-projection/`
**Premise**: the pre-trained unembedding matrix $\mathbf{W}_U$ can serve as a universal decoder for intermediate states, via $\mathbf{p} = \text{softmax}(\mathbf{z}\mathbf{W}_U)$.
**Signal**: tokens promoted by projecting an internal object into vocabulary space.
**Cost**: cheap. No training, no labels — direct inspection of any state.
**What it answers**: what semantic content is already *linearly decodable from this state by the final layer*? Intuitive for residual-stream states; degrades inside sub-layers where basis alignment weakens.
**Advantage**: training-free — any internal state can be read directly in token space without labels or auxiliary classifiers.
**Limitation**: assumes intermediate states share a basis with the output vocabulary, so reliability degrades inside sub-layers (FFN, MHA) and in models whose representation space rotates strongly across layers.

Submethods: Residual Stream State · Attention Head Output · Neuron Value Weight.

### 2. Magnitude Analysis — `./magnitude-analysis/`
**Premise**: internal elements with larger numerical values often exert greater influence on the computation.
**Signal**: static or dynamic magnitudes (weight norms, activation statistics, layer-wise distances).
**Cost**: cheapest. No backward passes, no auxiliary training.
**What it answers**: which components are *present and prominent*? Useful first-pass screening before committing to expensive methods. Does not establish causality — a high-magnitude feature can still be cancelled downstream.
**Advantage**: the cheapest method — no backward passes, no training — so it scales to large models and can serve as a first-pass filter before more expensive methods like Causal Attribution.
**Limitation**: a heuristic only — high magnitude does not guarantee causal necessity (it may be cancelled downstream), and components dormant on the chosen inputs are missed.

Submethods: Static Parameters · Dynamic Components · Layer-wise Representation.

### 3. Representation and Parameter Analysis — `./representation-and-parameter-analysis/`
**Premise**: many concepts are encoded as *linear directions* — either in activation space ($\mathbf{v}_c \in \mathbb{R}^{d_{\text{model}}}$) or in parameter space ($\boldsymbol{\tau} = \boldsymbol{\theta}_{\text{ft}} - \boldsymbol{\theta}_{\text{pre}}$). Once a target direction/feature is found, it can be used as a read-out (project) or write-in (add) operator — the write-in form doubling as a **causal intervention** that steers the behavior on demand.
**Signal**: dot products of states with concept directions; arithmetic on task vectors in weight space.
**Cost**: moderate. Vector construction is one or a few forward passes; evaluation and intervention are linear-algebraic.
**What it answers**: is a candidate direction *causally sufficient* (not just correlated) to drive the behavior? Promotes a probe direction into a controllable handle, and quantifies how much of the behavior the direction accounts for. In parameter space, the same view enables training-free model editing via task arithmetic.
**Advantage**: one direction serves both as a read-out (projection) and a write-in (addition), so monitoring, steering, and training-free model editing share the same handle, with no fine-tuning required and clean composition (add, subtract, negate).
**Limitation**: assumes concepts are linearly encoded — non-linear or entangled concepts are missed and additive edits spill into neighbouring features; directions are basis- and checkpoint-specific, and large edit strengths push the model off-distribution.

Submethods: Representation Engineering · Steering Vectors · Steering features · Parameter-Space Task Vectors.
**Choosing among them — what gets manipulated**: *Parameter-Space Task Vectors* edit the **weights** (a one-shot displacement in parameter space, applied before inference). The other three act on **activations** at inference time. Of those, *Steering features* and *Steering Vectors* both intervene on the input's own representation — *Steering features* directly amplifies/shrinks the model's **existing internal feature** for the target behavior, whereas *Steering Vectors* leaves the internal features untouched and instead **adds an externally built direction** (a CAA vector from contrastive pairs) into the residual stream. *Representation Engineering* is the read-and-write superset on the activation side: it extracts concept directions to both monitor (project) and steer (add) behavior.

### 4. Probing — `./probing/`
**Premise**: train an auxiliary predictor (often linear) to decode a labeled property $y$ from an internal vector $\mathbf{z}$; treat the LLM as a frozen feature extractor.
**Signal**: probe accuracy or information-theoretic surrogate across candidate objects.
**Cost**: moderate. Requires a labeled dataset and probe training, but the LLM stays frozen.
**What it answers**: is property $y$ *recoverable* from this internal object by a restricted hypothesis class? Supports comparison across layers/heads/FFNs under a shared protocol. Decodability is not causality; follow-up causal tests are typically needed.
**Advantage**: with a fixed probe family, supports standardized layer-/head-wise comparisons under a single protocol; the LLM stays frozen, so broad sweeps are cheap and the probes themselves are interpretable.
**Limitation**: decodability is not causality — high probe accuracy does not mean the model actually uses the object, and results are sensitive to labels, token positions, and probe family, so causal follow-up tests are typically needed.

Submethods: Residual Stream States · SAE Feature Activation State.

### 5. Feature Dictionary Learning — `./feature-dictionary-learning/`
**Premise**: re-base dense activations onto an over-complete, sparsely-active dictionary so that each atom is an interpretable, monosemantic feature: $\mathbf{a} \approx \mathbf{D}\,\mathbf{f}(\mathbf{a})$ with $\|\mathbf{f}\|_0 \ll m$.
**Signal**: per-token, per-feature firings of a trained sparse encoder.
**Cost**: high *up-front* (dictionary training is expensive, $m \gg d$); cheap to evaluate once trained.
**What it answers**: what are the *monosemantic units* of the model at this site, and how do they interact across sites? Underpins downstream tools — feature dashboards, circuit discovery via attribution graphs, SAE-based steering.
**Advantage**: replaces polysemantic neurons with a much more monosemantic basis; once trained, encoding and steering reduce to a single linear pass plus simple feature-weight edits, making feature dashboards, attribution-graph circuits, and SAE-style interventions tractable at LLM scale.
**Limitation**: dictionaries are expensive to train and suffer from dead, split, or absorbed features; reconstruction error leaves an "error term" that confounds full-circuit claims, and a dictionary trained on one site or checkpoint rarely transfers verbatim to another.
**Practical consideration**: released dictionaries can save work. Compare reuse, training, ICA, and native activations against the question and budget.

Submethods: SAE · Transcoder · Crosscoder · ICA Lens

### 6. Gradient Detection — `./gradient-detection/`
**Premise**: score internal objects with the sensitivity of a scalar target $F(x)$ with respect to the object, $s_j(x) = \phi(\nabla_{o_j} F(x), o_j)$.
**Signal**: gradient norm, gradient–input score, integrated gradients.
**Cost**: moderate. A small number of backward passes; much cheaper than exhaustive interventions.
**What it answers**: which objects are *first-order influential* on the target behavior? Produces fast rankings useful for narrowing the candidate set before a causal test. Local proxy only — not sufficient for functional necessity claims.
**Advantage**: applies to any object (inputs, activations, parameters) without extra training, needing only a backward pass; produces fast rankings that are far cheaper than exhaustive interventions, and can serve as a first-pass filter before more expensive methods like Causal Attribution.
**Limitation**: gradients are a local, first-order proxy — salience can be cancelled by downstream computation and finite interventions may diverge from first-order effects in non-linear regimes; results can be further validated with causal attribution.

Submethods: Inputs and Layer-wise States · Intermediate Outputs · Parameters.

### 7. Causal Attribution — `./causal-attribution/`
**Premise**: intervene on an object and measure the resulting change in behavior.
**Signal**: effect of patching (replace with a counterfactual-derived activation), ablation (zero out / remove), or attribution patching (first-order approximation of patching).
**Cost**: expensive for exact patching/ablation; cheap for attribution patching.
**What it answers**: is this object *causally necessary or sufficient* for the behavior? The gold standard — but expensive enough that exact variants should usually be preceded by a cheaper screen.
**Advantage**: provides definitive evidence of *functional* responsibility — distinguishes components that actually drive a behavior from those that are merely active or correlated, which correlation-based methods cannot do.
**Limitation**: traditional patching/ablation cost scales linearly with the number of analyzed objects (one forward pass per intervention); Attribution Patching approximates the same effect with a single backward pass per task example, but is only first-order accurate. In practice, a cheaper method (e.g. Gradient Detection or Magnitude Analysis) is typically applied first to narrow the candidate set.
**Practical consideration**: long-response intervention evaluation can be costly. A differentiable fixed-position or teacher-forced scalar may support gradient screening, but it tests a narrower quantity than free generation; confirm important findings with the metric needed for the actual claim.

Submethods: Patching · Ablation · Attribution Patching.

### 8. Circuit Discovery — `./circuit-discovery/`
**Premise**: a transformer's computation forms a graph of attention-head and MLP edges; the minimal subgraph that reproduces a target behavior is its *circuit*.
**Signal**: edge-level effect under iterative pruning (ACDC), gradient-attribution (EAP-IG), or sparse-feature replacement (transcoder-based).
**Cost**: moderate to expensive. EAP-IG runs in a few backward passes; ACDC scales linearly in edges; feature-based replacement adds the cost of training transcoders.
**What it answers**: which subgraph of edges is *jointly* necessary and sufficient for the behavior? Goes beyond per-component scoring to recover an end-to-end mechanism (e.g., factual recall, indirect-object identification).
**Advantage**: recovers a structured, end-to-end mechanism — not just *which* components matter but *how* they communicate — and the resulting subgraph can be checked for faithfulness on held-out tasks, supporting cross-model comparison and mechanism-level claims.
**Limitation**: the search space is over edges, so it is much more expensive than per-object localization; gradient-based shortcuts trade exactness for speed, and outcomes depend on the choice of task distribution, counterfactual inputs, and faithfulness metric.

Submethods: Intervention-based Edge Search (ACDC) · Attribution-based Edge Scoring (EAP-IG) · Feature-based Replacement Models (e.g. circuit-tracer; demo lives under `./feature-dictionary-learning/transcoder/`).

### 9. SHAP — `./SHAP/`
**Premise**: feature attribution as a coalition game — assign each input feature its Shapley value, the unique attribution that satisfies local accuracy, missingness, and consistency.
**Signal**: per-feature contributions $\phi_i$ to a single prediction $f(x)$, with $f(x) = \phi_0 + \sum_i \phi_i$.
**Cost**: model-dependent. Exact polynomial-time for tree ensembles (TreeSHAP); sample-based for arbitrary models (KernelSHAP); amortized neural surrogate for real-time use (FastSHAP).
**What it answers**: how does the model use each *input* feature for this prediction, on a scale that is comparable across model families? The standard tool for input-level feature importance and the reference framework that other attribution methods are compared against.
**Advantage**: unifies many ad-hoc attribution methods (LIME, DeepLIFT, LRP, classical Shapley) under one axiomatic framework, so explanations are comparable across model families; per-instance values aggregate into global importance, and tree models admit an exact polynomial-time estimator.
**Limitation**: exact computation is exponential in the number of features for arbitrary models, so estimators rely on sampling and assumptions about how "missing" features are modelled; values are correlational rather than causal, and the additive form obscures strong feature interactions.

Submethods: Foundational and Estimator-based SHAP · Extended SHAP (FastSHAP).

### 10. Neural Feature Learning — `./neural-feature-learning/`
**Premise**: feature learning can be analysed without backpropagation through the Neural Feature Matrix $\mathbf{W}^\top\mathbf{W}$ and its empirical fingerprint, the expected gradient outer product $\mathbb{E}[\nabla f \nabla f^\top]$ (EGOP). Their alignment — the Deep Neural Feature Ansatz — predicts the directions a network has learned.
**Signal**: top eigenvectors of $\mathbf{W}^\top\mathbf{W}$ / EGOP; iterative kernel-EGOP fixed points (RFM); width-limit dynamics (NTK / NNGP / muP).
**Cost**: moderate to high. EGOP estimation requires per-sample Jacobians; infinite-width experiments are constrained by the choice of parameterization.
**What it answers**: *how* did the network learn its features, and can the same features be recovered without gradient descent? Connects classical kernel methods, infinite-width theory, and observed feature-learning behaviour in finite networks.
**Advantage**: gives a kernel-shaped view of feature learning that transfers across layers and widths; relies only on cheap input gradients, enabling backprop-free algorithms (RFM) and clean predictions in the infinite-width limits (NTK / NNGP / muP).
**Limitation**: the NFM-EGOP alignment is an empirical *ansatz*, not universal, and infinite-width predictions only approximate finite-width training when initialization scales and learning rates are tuned to the chosen parameterization; EGOP estimation is also expensive on high-dimensional inputs.

Submethods: Eigenvector Feature Direction (DNFA) · Gradient Outer Product (RFM) · Kernel/NTK Feature Regime (TP4) · Network as Filter (ConvRFM).

### 11. Multimodal-Specific Interpretability — `./multi-modal/`
**Premise**: link an internal vision unit (neuron, channel, feature) to a *natural-language concept* via similarity to a text embedding from an aligned multi-modal model such as CLIP.
**Signal**: similarity scores between per-unit activation summaries and text-side embeddings of an open-vocabulary concept set.
**Cost**: moderate. Requires a probing image set and a forward pass through the alignment model; no fine-tuning of the analyzed network.
**What it answers**: what *named concepts* drive a vision (or vision-language) model's predictions, and how do those concepts compose into attribution graphs? Turns anonymous tensors into human-readable explanations that compose with attribution and steering.
**Advantage**: outsources the language side to a pre-trained vision-language model (e.g. CLIP), so labels come from an open-vocabulary concept set without crowdsourced annotation; the resulting concept-level handles compose cleanly with attribution and steering for concept-conditional heatmaps and feature visualisations.
**Limitation**: inherits the alignment model's biases — anything CLIP cannot embed cleanly (fine-grained categories, novel domains, low-resource languages, abstract qualifiers) yields noisy or empty rankings; results are correlational and depend on the choice of probing images and concept set, so causal follow-ups are typically needed.
**Practical rule**: most of the families in §1–§10 above already apply directly to both text-only LLMs *and* multimodal models — pick them whenever the analysis is about layers / heads / neurons / features regardless of modality. Reach for this section only when the goal is **vision-specific** and requires concept-level natural-language labels of internal units (neurons / channels / SAE features) via CLIP-style cross-modal alignment.

Submethods: CLIP-Dissect · Zennit-CRP.

## Selecting a Method

Match the question to the family:

| Research question | Start with | Why |
|-------------------|-----------|-----|
| "Which components are prominent for this behavior?" | Magnitude Analysis | Cheapest screen; surfaces candidates without interventions |
| "What semantic content does this state carry, without labels?" | Vocabulary Projection | Zero-shot, no training, intuitive |
| "Is property $y$ linearly decodable from this layer/head?" | Probing | Standardized cross-layer comparison under a fixed probe family |
| "Is this object a first-order influencer of the target?" | Gradient Detection | Fast ranking with a few backward passes |
| "Is this object causally necessary for the behavior?" | Causal Attribution | Gold standard; use after a cheaper method has narrowed the set |
| "Which subgraph of edges is necessary and sufficient for this behavior?" | Circuit Discovery | Recovers an end-to-end circuit at the edge level |
| "What are the monosemantic feature units of the model at this site?" | Feature Dictionary Learning | Trains a sparse, over-complete basis whose atoms are interpretable |
| "Is a *direction* (in activations or parameters) sufficient to control the behavior?" | Representation and Parameter Analysis | Tests directional sufficiency via additive intervention or task arithmetic |
| "How does this network learn its features, and can a kernel reproduce them?" | Neural Feature Learning | Backprop-free analysis through the NFM / EGOP and width-limit dynamics |
| "How does the model use each *input* feature for this prediction?" | SHAP | Game-theoretic input attribution, model-agnostic on a comparable scale |
| "What named concepts drive this vision model's predictions?" | Multimodal-Specific Interpretability | Open-vocabulary concept labelling via CLIP-style alignment |

If the question spans multiple granularities (prompt tokens, residual stream, attention heads, neurons, SAE features, parameters, weights), consult the submethod tables inside each family's `SKILL.md` — granularity is the primary axis along which submethods are organized.

### Previous findings

Use available previous findings to choose informative follow-ups. A tried family can still help replication, another question, or better measurement. No required history file or automatic family ban applies.

## Practical Tips

### 1. Finding an SAE for the Target Model
Check whether a Sparse Autoencoder has already been released for the target model — and for which layers. If one exists, use it to locate the target feature: SAE features are far more monosemantic and interpretable than directions read off the raw backbone activations, and intervening on them usually gives a cleaner, stronger effect.

**Search local disk first** (existing model/SAE caches, e.g. the Hugging Face cache or the project's own weights directory), and only download if nothing is found locally.

Commonly used public SAEs:

- Evo2-7B-262k (genomic DNA) → https://huggingface.co/Goodfire/Evo-2-Layer-26-Mixed
- ESM2-650M (protein) → https://huggingface.co/liambai/InterProt-ESM2-SAEs
- ESM2-650M (protein) → https://huggingface.co/Elana/InterPLM-esm2-650m
- CLIP / ViT (vision) → https://huggingface.co/Prisma-Multimodal
- Gemma 2 / 3 → https://huggingface.co/google/gemma-scope
- Llama 3.1 / 3.2 → https://huggingface.co/collections/EleutherAI/sparse-autoencoders
- Qwen3 → https://huggingface.co/Qwen/SAE-Res-Qwen3-1.7B-Base-W32K-L0_100
- GPT-2 Small → https://huggingface.co/jbloom/GPT2-Small-OAI-v5-32k-resid-post-SAEs
- Mistral 7B → https://huggingface.co/lmxxf/mistral-7b-sae-layer16
- Pythia → https://huggingface.co/nileshsarkar-ai/pythia-410m-saes-x32-l1-3e-4-fixed


If no SAE covers the target model, fall back to a feature identified directly in the model's own activations — the same direct-intervention procedure applies, without the encode/decode step.

### 2. Token Position for Steering Vectors
Match the pooling site to where the behavior is encoded.
- **Last token**: default for prompt-based extraction — autoregressive models concentrate next-token signal at the final input position.
- **Mean over response tokens**: pair a positive and negative response to the same input, then average hidden states across response positions only (exclude the shared prefix). Use when the behavior spans the full sequence rather than a single token.
- **Head / MLP output**: if extracting from a head or MLP output instead of the residual stream, match pooling to the claim's granularity (last-token for next-token effects, mean-pool for sequence-level properties).

### 3. Choosing the Intervention Layer
Start where representations are richest for the target behavior, then refine.
- **Default range**: middle (~40–60% depth) to middle-to-late (~60–80%) layers. By this depth the residual stream carries compositional representations but has not yet committed to the output distribution, so additive interventions redirect behavior without breaking syntax/fluency.
- **Task-specific refinement**: if the default sweep fails, treat layer index as a hyperparameter. Use probing accuracy or gradient-based localization (§6 Gradient Detection) to narrow candidates before running full intervention sweeps.

### 4. Calibrating Intervention Strength
Find the magnitude that reliably elicits the target effect, judged jointly by a target metric and a general capability metric. Re-tune from scratch whenever layer, position, or method changes — the optimum may not transfer.
- **Non-monotonic response**: too small → no effect (signal drowned out); moderate → target behavior peaks; too large → fluency/coherence degrade, then the target effect itself collapses as activations go off-distribution.
- **Sweep procedure**:
  1. Start small (e.g., α = 1 for a steering vector on a normalized residual stream) and increase geometrically (1 → 2 → 4 → 8 → 16 → 32 …), not in fixed steps.
  2. At each step, log the target metric (e.g., target-behavior rate on held-out probes) and a capability metric (e.g., perplexity or benchmark score).
  3. Pick the smallest α that meets the target while capability drop stays within tolerance (e.g., < 5–10%) — not the α where the target metric peaks.
  4. Same recipe for SAE feature scaling or activation patching — sweep the coefficient or patch fraction.
- **Layer–magnitude coupling**: earlier layers need larger multipliers; later layers saturate sooner. Always re-sweep when the site changes.
- **Suppression**: subtracting a direction follows the same sweep; large negative multipliers produce symmetric off-distribution failures.

## Composing Families

Mechanism work is rarely done in a single family. A common screen-to-verify pipeline:

1. **Screen** with a cheap method — Magnitude Analysis or Vocabulary Projection or Gradient Detection — to narrow the candidate set of layers / heads / neurons / features.
2. **Decode** with Probing or Vocabulary Projection or Multimodal-Specific Interpretability to confirm the candidates carry the property of interest.
3. **Verify** with Causal Attribution or Representation and Parameter Analysis to establish necessity / sufficiency via interventions.
4. **Recover** an end-to-end mechanism with Circuit Discovery if the claim is about how multiple components interact.
5. **Re-base** with Feature Dictionary Learning when polysemantic neurons obscure the analysis, then re-run steps 2-4 in feature space.

Neural Feature Learning sits adjacent to this pipeline as a *theoretical lens* on how the features being analyzed came to exist; SHAP sits adjacent for *input-side* attribution that complements internal-side mechanism work.

## Directory Layout

Each family lives in a folder whose name matches the path given in its section heading above (e.g. `### 1. Vocabulary Projection — ./vocabulary-projection/`); submethod folders are named exactly as listed in that section's `Submethods:` line.

A typical family folder follows this two-level shape:

```text
<family>/
├── SKILL.md                     # family-level routing skill
├── article_references.md        # canonical papers for the whole family
└── <submethod>/
    ├── article_references.md    # narrower paper list for this submethod (when present)
    ├── scripts/                 # runnable demo scripts (.py)
    └── references/              # library/API documentation for the demo
        └── api_reference.md
```

- **`SKILL.md`** describes a family or submethod, its use cases and assumptions. Read relevant detail as needed.
- **`article_references.md`** — a curated list of the originating papers (with links). A family-level file gives the umbrella reading list; submethod-level files (where present) narrow it to that specific technique. Use these to ground methodological choices and to cite source work.
- **`scripts/`** — reference implementations illustrating API usage and experimental patterns of the demo library bundled with this submethod. They are starting points, not turnkey pipelines: adapt them to the project's specific model, dataset, and metrics rather than copying verbatim.
- **`references/`** — local documentation of the demo's underlying library (typically `api_reference.md`), kept alongside the scripts so the demo can be understood and reproduced without external lookup. Distinct from `article_references.md`: papers vs. library docs.
## Intervention experience

[Intervention practice](../human-expertise/interventions.md) covers feature selection, positions, sites, strength, controls, and reconstruction effects.

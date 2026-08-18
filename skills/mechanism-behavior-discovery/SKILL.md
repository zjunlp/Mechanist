---
name: mechanism-behavior-discovery
description: 'Mine behavioral regularities in neural-network (LLM / multimodal) models — the upstream half of the project''s mission (find a behavior worth explaining, then investigate the mechanism behind it). Use this skill when the task is open-ended: surface a *new* behavioral phenomenon — a candidate claim / research direction — rather than investigate an already-named mechanism. It gives strategies for choosing which behavior to probe and how to choose the data that validates it. The output is a candidate phenomenon that hands off to `/mechanism-explore` for mechanistic investigation. Domain-general: no assumption about model family, modality, or task.'
---

# Mechanism — Behavior Discovery

The discovery half of the loop: before you can explain *why* a model does something, you need a behavior worth explaining. This skill helps surface a **new behavioral phenomenon** — a candidate claim — and choose the data that tests it. The sharpened phenomenon (a one-sentence falsifiable behavior, its data/metric, and a plausible internal locus) hands off to `/mechanism-explore`.

A phenomenon is an observable, reproducible regularity in a model's input→output behavior that is not obvious a priori. A candidate is worth pursuing when it is **real, non-obvious, specific, robust, and tractable** (a plausible internal locus exists to explain it).

## When to Use

The task is open-ended — "find something interesting about how this model behaves," "what's surprising here." Do **not** use it to explain an already-named behavior (that is `/mechanism-explore`) or to score a model on a fixed benchmark.

This skill runs only when the phenomenon is **not** already pinned by the user. When the user explicitly names the phenomenon to investigate, the caller skips discovery entirely and goes straight to explaining that named phenomenon — so a behavior-level override is handled by the caller, not here.

## Strategies for Choosing a Behavior to Investigate

1. **Transfer a behavioral phenomenon into a high-stakes domain.** Take a behavior already known elsewhere, move it into an important domain, and test whether it reappears — either under the same conditions or under stricter, more counterintuitive ones. Domains include but are not limited to:
   - Science domains: chemistry, biology, medicine, …
   - Language: how language systems evolve and develop, etymological / cognate relationships, ancient-text decipherment, and the language–intelligence relationship.
   - Multi-agent social science.
   - Creativity.
2. **Borrow from the human sciences.**
   - Take a finding from brain science, psychology, or developmental history and check whether LLMs exhibit the same behavior.
   - Compare how the human brain and LLMs process the same task, identifying similarities and differences. This usually requires EEG (or other neural) recordings of humans performing that task.
3. **Cross-modal transfer.** Take a phenomenon seen in text and check whether it appears in image / video / multimodal models.
4. **Reuse existing results in computer science.** Check whether earlier findings, methods, or conclusions in computer science apply to the current model or research question.
5. **Probe a phenomenon's conditions or causal origin.** Take a known (or just-surfaced) phenomenon and ask *when* it holds or *why* it arises.
   - **When it holds** — characterize the regime of validity. *Macro*: under what general condition or law does the phenomenon hold or break? *Micro*: vary a concrete knob — model scale, checkpoint, prompt format, language, in-context examples, difficulty, or domain — and find the specific point at which the behavior flips. Either a general boundary or a single flipping condition is itself a candidate claim.
   - **Why it arises** — trace it to a *training* cause (data frequency, order of acquisition across checkpoints, objective, RLHF stage) or an *inference* cause (decoding, attention/representation locus, prompt position, context length), yielding a claim of the form *"P is caused by C at stage S"*.
6. **Meta-analysis.** Distill a theory or law from prior research — e.g. the scaling law and the Densing Law of LLMs — and use a macro-level or mathematical-theory lens to characterize the regularity, including the conditions under which a given phenomenon holds.

## Some Rules

1. **Existing datasets first.** Check whether an existing dataset can test the behavior directly; if not, adapt one (relabel / filter / transform). Prefer datasets that are well-established — e.g. authoritative and widely cited, or those published in venues such as *Nature* / *Science*.

2. **Pitch at any altitude — a high-level behavior phenomenon and a fine-grained one are both good.** A candidate can be a broad, abstract regularity in how the model reasons, represents, or decides, or a narrow, concrete effect tightly scoped to a single input→output pattern. Both are worth pursuing — so do **not** default to ever-smaller, hyper-specific points. An important high-level phenomenon is often the more valuable and more illuminating target, *as long as* it is still sharpened into a falsifiable, testable one-sentence behavior — the **specific** bar (§ the five bars) means *operationalizable*, not *small*. Aim for a spread of altitudes across your candidates rather than a monoculture of tiny effects.
   - **High-level behavior phenomenon** — e.g. *"the model's expressed confidence is largely decoupled from whether its answer is actually correct"*; or *"the model's sycophancy is a capability distinct from its factual-knowledge competence"*.
   - **Fine-grained behavior phenomenon** — e.g. *"the model's multiple-choice answer flips with the option ordering, independent of content"*; or *"the model is more sycophantic when the prompt is phrased in the first person"*.

3. The move is strongest when you *tighten as you transfer*: not only just re-confirm a phenomenon in a new domain, but make its precondition harder or more counterintuitive while moving it somewhere the behavior actually carries consequences. The candidates that matter most are those where a small or innocuous-looking cause yields a disproportionate, high-stakes effect — prefer framings that widen that gap over ones that merely reproduce the original.

4. **Safety and risk in science domains are especially worth probing.** Chemistry, biology, medicine, healthcare, clinical diagnosis, and the like are high-priority directions: when an unsafe or risky phenomenon surfaces in some other domain, prioritize transferring it into one of these safety-critical domains — that is where the same behavior carries the highest stakes and is most worth investigating.

Identify the user's intent, then pick the strategy direction that best matches it to probe the behavior. Using the Strategies for Choosing a Behavior to Investigate above, brainstorm several promising and interesting LLM behavioral phenomena internally, then **commit to exactly one** as the candidate to hand off — the single phenomenon to explain. (The *mechanism* directions for explaining that one phenomenon may stay plural; producing a few candidate directions is `/mechanism-explore`'s job, not this stage's.)

**If a record of already-explored phenomena and their outcomes is provided**, pick a phenomenon that is **distinct from all of them**. In particular, do **not** re-propose a phenomenon already **established**, **conditional** (it holds, under stated conditions), or **not-established** (refuted) — those questions are answered; choose a genuinely new direction (you may build on what those outcomes taught you). A phenomenon left **`inconclusive`** is *not* settled (the test failed to decide) — it remains a valid retry target, not something to avoid. The phenomena you considered but did not commit to are worth noting as a backlog for a later round.
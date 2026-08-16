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

## Innovation Moves — Where the Novelty Actually Comes From

The six strategies say **where to look**; they do not by themselves produce a new claim. A transfer that lands exactly where its source predicts contributes a data point, not a finding — the domain changed and nothing else did. A reviewer reads that as «X, but in Y», and it is the most common way a competently-executed candidate still scores as incremental.

So every candidate must carry a **novelty delta**, written down before it is committed to:

> *If the borrowed phenomenon reappears here exactly as its source predicts — no surprises — what is still new?*

If the honest answer is "the domain is new", "the modality is new", or "it is tested on a bigger model", the candidate is not ready: domain transfer buys **relevance**, never novelty. Apply the moves below until the delta survives being said out loud to someone who has read the source paper.

The same test applies to the *method*: a design that is the source paper's with the nouns swapped inherits its blind spots and can only confirm it or fail to. **Novelty lives in at least one of three places — the claim, the condition, or the instrument.** Name which one, for every candidate.

1. **Adapt the mechanism to the domain, don't just relocate the test.** Ask what this domain has that the source did not — a structure, a constraint, a modality, an actor — and make *that* what the claim turns on. A domain interchangeable with any other high-stakes one is decoration: the claim should break, or change shape, when you swap it.
   > Weak: *does effect E also happen in medicine?* Strong: *E is carried by a channel that exists only where an intermediate model rewrites the data, so E should survive triage summarization and die under structured extraction.*

2. **Predict against the source.** State the condition under which the source result should **fail** or reverse sign, and make that the claim. A prediction that agrees with the incumbent account in every regime is testing it, not competing with it. Every statement should read as *«the standing account predicts A here; we predict B»*.

3. **Aim at the boundary, not the reappearance.** The question is rarely "does it happen too" but "where does it stop" — the flipping point, the threshold, the decay curve behind an apparently binary rule, the regime where a qualitative account turns out to be quantitative. A measured boundary is a contribution even when the phenomenon is known.

4. **Change the measured quantity.** Keep the setting and measure what the source could not: a rate rather than a presence, a capacity rather than an effect, a half-life rather than a snapshot, an interaction rather than a main effect, a per-item attribution rather than a corpus average. New quantities are where laws come from; re-running someone's metric cannot produce one.

5. **Import the method, not the finding.** Borrowing a *result* from another discipline gives an analogy; borrowing its **paradigm or instrument** gives a design nobody here has run — knockout–rescue and epistasis from genetics, staircases and detection thresholds from psychophysics, instrumental variables and mediation from econometrics, dose–response and survival curves from epidemiology, capacity and rate–distortion from information theory, competition and carrying capacity from ecology. Transfer the apparatus and the phenomenon gets measured in a way it never has been.

6. **Compose two independent results into a prediction neither makes.** Take two established findings that have never been put in the same experiment and derive the joint prediction. The composition is the contribution, and it is falsifiable in a way each ingredient alone is not.

7. **Turn the phenomenon into an instrument.** A behavior that is merely alarming becomes a contribution when it is used to *measure* or *do* something else — detect provenance, audit a pipeline, estimate a previously unmeasurable quantity, serve as a defense. It converts "here is a worrying effect" into "here is a tool", which is what gets built on.

8. **Attack the assumption the field is resting on.** Find the load-bearing assumption everyone shares because nobody has tested it (filtering works, retraction erases, the benchmark measures what it says, the control is neutral), and make the phenomenon the demonstration that it does not hold. The stakes come free; the work is in constructing the case where the assumption is genuinely tested rather than merely doubted.

**One statement, three failure modes.** A statement fails if (a) it can be produced by paraphrasing a sentence from the source paper's abstract; (b) it can be produced from a sibling candidate by swapping one noun — that is one phenomenon with several instantiations, not several phenomena; or (c) the setup clause is longer than the claim clause. Write the statement so the novelty delta is *visible inside it*, not parked in a justification field.

## Some Rules

1. **Existing datasets first.** Check whether an existing dataset can test the behavior directly; if not, adapt one (relabel / filter / transform). Prefer datasets that are well-established — e.g. authoritative and widely cited, or those published in venues such as *Nature* / *Science*.

2. **Pitch at any altitude — a high-level behavior phenomenon and a fine-grained one are both good.** A candidate can be a broad, abstract regularity in how the model reasons, represents, or decides, or a narrow, concrete effect tightly scoped to a single input→output pattern. Both are worth pursuing — so do **not** default to ever-smaller, hyper-specific points. An important high-level phenomenon is often the more valuable and more illuminating target, *as long as* it is still sharpened into a falsifiable, testable one-sentence behavior — the **specific** bar (§ the five bars) means *operationalizable*, not *small*. Aim for a spread of altitudes across your candidates rather than a monoculture of tiny effects.
   - **High-level behavior phenomenon** — e.g. *"the model's expressed confidence is largely decoupled from whether its answer is actually correct"*; or *"the model's sycophancy is a capability distinct from its factual-knowledge competence"*.
   - **Fine-grained behavior phenomenon** — e.g. *"the model's multiple-choice answer flips with the option ordering, independent of content"*; or *"the model is more sycophantic when the prompt is phrased in the first person"*.

3. The move is strongest when you *tighten as you transfer*: not only just re-confirm a phenomenon in a new domain, but make its precondition harder or more counterintuitive while moving it somewhere the behavior actually carries consequences. The candidates that matter most are those where a small or innocuous-looking cause yields a disproportionate, high-stakes effect — prefer framings that widen that gap over ones that merely reproduce the original. This is the minimum form of § Innovation Moves; a transfer that tightens nothing has a novelty delta of zero and should be reworked or dropped, however important its destination domain.

4. **Safety and risk in science domains are especially worth probing.** Chemistry, biology, medicine, healthcare, clinical diagnosis, and the like are high-priority directions: when an unsafe or risky phenomenon surfaces in some other domain, prioritize transferring it into one of these safety-critical domains — that is where the same behavior carries the highest stakes and is most worth investigating. The stakes raise the value of an answer; they do not supply the novelty delta, so a safety-critical transfer still owes one of the § Innovation Moves.

5. **Say which of the three is new — claim, condition, or instrument — and make the experiment turn on it.** A candidate may reuse the field's standard design *only* when the claim or the condition is what is new. If the claim is a known effect in a new place, the instrument has to be new for the candidate to be worth running, and the design must be sketched far enough to show that it is. "Standard setup, standard metric, new topic" is the profile of an incremental paper, and it is visible at candidate time, long before the experiments are written.

Identify the user's intent, then pick the strategy direction that best matches it to probe the behavior. Using the Strategies for Choosing a Behavior to Investigate above, brainstorm several promising and interesting LLM behavioral phenomena internally, sharpen each with at least one of the § Innovation Moves until its novelty delta is non-empty, then **commit to exactly one** as the candidate to hand off — the single phenomenon to explain. (The *mechanism* directions for explaining that one phenomenon may stay plural; producing a few candidate directions is `/mechanism-explore`'s job, not this stage's.)

**If a record of already-explored phenomena and their outcomes is provided**, pick a phenomenon that is **distinct from all of them**. In particular, do **not** re-propose a phenomenon already **established**, **conditional** (it holds, under stated conditions), or **not-established** (refuted) — those questions are answered; choose a genuinely new direction (you may build on what those outcomes taught you). A phenomenon left **`inconclusive`** is *not* settled (the test failed to decide) — it remains a valid retry target, not something to avoid. The phenomena you considered but did not commit to are worth noting as a backlog for a later round.
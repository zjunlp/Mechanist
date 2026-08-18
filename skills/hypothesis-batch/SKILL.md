---
name: hypothesis-batch
description: "Batch pipeline for research hypotheses. The positional argument is the user's whole INPUT INTENTION. Load the literature landscape plus behavior- and mechanism-discovery strategies once per run; generate a deduplicated, mechanism-aware behavior library over accumulating rounds; select with novelty verification and external review; then instantiate a mechanism and iteratively improve one reviewer-facing `claim.json` per selected behavior using independent novelty, impact, and testability judges. `WRITER` authors candidates and claims (`session` by default or `llm-chat`); evaluation uses the external reviewer."
argument-hint: "<intention — what you want out of this topic> [— n-behaviors: N] [— rounds: R] [— top-n: K] [— cold-n: N] [— writer: session|llm-chat]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__llm-chat__chat
---

# Workflow: Hypothesis Library → Selection → Claim Skeletons

Orchestrate the claim stage for: **$ARGUMENTS**.

## Overview

Seven numbered phases (P1–P7), run non-interactively end to end. P1 and P1.5 are run-level initialization: each executes once before round 1 and is reused by every generation round.

```
Step 1  BUILD    /research-lit ─→ full-load behavior + mechanism strategies ─→ ROUNDS × round loop
                 (P1, once/run)    (P1.5, once/run; no artifact)                 (P2) → hypothesis_library.json

Step 2  SELECT   /novelty-check ─→ /research-review ─→ veto, rank, cut to TOP_N
                 (P3, hard gate)    (P4)                (P5)   → verdicts written back into the library

Step 3  CLAIM    instantiate mechanism ─→ draft ─→ evaluate ─→ revise ─→ evaluate ─→ verify
                 (P6)                    (P7; serial)                          → claims/<NN>_<name>/claim.json
```

```
hypothesis_library.json      # the pool, scores, eliminations, ranks — updated in place
topic.md                     # the topic + goal handed to the evaluators — written once, at run start
RESEARCH_LIT.md              # raw retrieval dump (audit-only)
LANDSCAPE.md                 # synthesized landscape — regenerable scratch
claims/
  01_<name>/claim.json       # one directory per selected behavior, rank-ordered
  …
  <TOP_N>_<name>/claim.json
```

## Context budget and phase routing

This file is the normative spec, but the active prompt should be phase-local. Do not paste the whole workflow back into every model call.

- **Run initialization:** read both `/mechanism-behavior-discovery/SKILL.md` and `/mechanism-explore/SKILL.md` **in full once**. Retain them as run context; do not re-read either skill per round and do not copy their prose into the library.
- **Phase 2 generation:** keep the current `INTENTION`, compact `LANDSCAPE.md` gaps/open-problem summary, relevant round slice, compact banlist, field spec, and the strategy material appropriate to the pass. Do not repeat later-phase workflow prose. The cold prompt withholds named taxonomies; the guided prompt uses relevant strategy content from the already-loaded skills.
- **Phases 3–5 evaluation:** pass only the candidate statement/trigger, `innovation`, `mechanism_opportunity`, `five_bars` when relevant, impact rationale, and nearest-work evidence. Do not pass the claim-writing specification.
- **Phases 6–7 claim work:** load the selected behavior node **in full** (`statement`, `discovery_strategy_detail`, `five_bars`, `innovation`, `mechanism_opportunity`, `gaps`, `impact`, plus Phase 3 nearest works and Phase 4 feedback), instantiate its mechanism, then draft. A revision prompt receives only the current claim, the frozen problem anchor, the three score files with justifications, and the claim specification/checklist; never the full pool.
- `pipeline.md` is an orientation/reference file. Use it for routing or audit, not as an additional copy of the active prompt when `SKILL.md` is already loaded.

Three things bind the whole run:

- **One deliverable per claim.** The experiment design *is* the `Experiments` field. No `EXPERIMENT_PLAN.md`, no `FINAL_PROPOSAL.md` — a design written twice is a design maintained in two places, and this workflow ships the reviewer's version only.
- **Retrieval runs once.** `/research-lit` executes exactly once per invocation, before round 1. Every normal and top-up round reuses that `LANDSCAPE.md`; Phase 3 later retrieves per candidate. There is no literature-refresh option or per-round retrieval branch.
- **Strategies load once.** Both strategy skills are read in full during P1.5 and reused for all rounds and selected claims. Full-load is a run-level action, not repeated prompt payload.
- **`ROUNDS × N_BEHAVIORS` in, `TOP_N` out.** The pool exists to be cut: it must survive a novelty gate and a design veto and still leave `TOP_N`. A post-dedup pool below `2 × TOP_N` means the rounds collapsed onto each other — run one extra round aimed at whatever the dedup revealed as over-covered.

## Two target standards

These are the batch's optimization targets, not labels applied after generation.

- **Novelty — a researcher who knows this area would not have predicted this specific prediction.** Passing a literature search is only a publication floor, and a candidate can clear it while leaving every expert expectation intact. The target is the expectation itself: a challenged boundary, an overturned assumption, a prediction that competes with the standing account, a quantity nobody measures, or a phenomenon put to a use it was never built for. Say, for every candidate, what the expert would have predicted first — and what this one predicts instead. § *Innovation moves* is how that gets produced; § *Instrument diversity* is its mechanism-side counterpart.
- **Impact — address an important problem and change a consequential decision.** Start from the problem or behavior, not from the method. Prefer recognized bottlenecks, safety or reliability concerns, or decisions that a field or real user must make. State who would act differently if the result were true or false and how far that consequence travels. “Interesting”, technically elegant, or merely difficult is not impact by itself.

## Constants

- **INTENTION** — **the positional argument itself**, everything before the first ` — `, verbatim. Free text stating the direction plus whatever angle, constraint, or wanted result the user attached. Injected into every brainstorm round, the impact rationale, the Phase 5 tiebreak, and every `claim.json` prompt. Required: if empty, ask for it in one line and never invent one. Stored at the library's top level as `intention`.
- **TOPIC** / **topic_slug** — distilled from `INTENTION` (a short noun phrase naming the direction, dropping the angle and the constraint; plus a kebab-case slug). Used only for library identity. Generation and ranking read `INTENTION`, never `TOPIC`.
- **N_BEHAVIORS = 10** — target count of *new* behaviors per round. `— n-behaviors: N`.
- **COLD_N = `max(1, round(N_BEHAVIORS / 5))`** — how many of each round's behaviors come from the **cold pass**, generated before the discovery-strategy taxonomy is shown. `— cold-n: N`; `0` disables it (not recommended). A taxonomy read immediately before generating **anchors** the generation: every candidate arrives pre-shaped to fit a named lens, and the lenses' blind spot becomes the round's. Cold candidates are the round's only chance to name something no lens would have asked for. They are held to the same bars and the same dedup — unprimed, not unfiltered.
- **ROUNDS = 3** — consecutive generation rounds. Each runs the full generate → dedup → impact → persist cycle and writes the library **before the next round starts**, so the pool accumulates and every round's banlist is rebuilt from it. `— rounds: R`.
- **TOP_N = 10** — how many behaviors survive Phase 5 and get a `claim.json`. Fixes the directory numbering. `— top-n: K`.
- **IMPACT_WEB = false** — keep Phase-2 impact scoring lightweight and unsearched; it cuts nothing. The official Phase-7 impact judge performs the required web search on selected claims.
- **CLAIM_EVAL_PASSES = 2** — fixed v2-style claim loop: score the initial draft, revise once, then score the revision. Stop early when the first score set yields no material revision; never run an open-ended critique loop.
- **REVIEWER_BACKEND = `llm-chat`** — **the external model, always, for every evaluation step**: dedup and impact scoring in Phase 2, the novelty gate in Phase 3, the critical review in Phase 4, and the three final claim judges in Phase 7. Resolved from `LLM_MODEL` via `mcp__llm-chat__chat`. Sub-skills declare the same default independently; this constant is not forwarded. Deliberately **not** tied to `WRITER` — never route review, dedup, or scoring through the session model, because a writer grading its own pool is not a gate.
- **WRITER = `session`** — **the single model authoring both deliverables**: the behaviors in `hypothesis_library.json` (Phase 2) and every `claim.json` (Phase 6). `— writer:` takes two values:
  - **`session`** (default) — the current session model. Full file access, no context-assembly cost.
  - **`llm-chat`** — the external model, stateless and with no file access, so every prompt must be assembled by hand. Brings different priors, which makes the brainstorm diverge harder.

  **Never split the setting across phases.** If Phase 2 and Phase 6 ran on different models, the run is inconsistent and the `claim.json` files must be redrafted. At the default, `WRITER` and the orchestrator are the same model, so the separation between authoring and verifying holds by discipline rather than by plumbing: **verification is still a distinct act**, run against the checklist as written.
- **LIBRARY_FILE = `hypothesis_library.json`** — the canonical pool, at project root. One topic per file.
- **OUTPUT_DIR = `.`** — where `/research-lit`'s two files land: the working directory, alongside `hypothesis_library.json`. `/research-lit` defaults to `idea-stage/` *regardless of caller*, so Phase 1 must pass the override explicitly; it is not inherited.

### Argument parsing

`$ARGUMENTS` is `"<intention>" — <key>: <value>, <key>: <value>`. Everything before the first ` — ` (or `--`) is `INTENTION`, verbatim; the rest is a comma-separated option list. Keys: `n-behaviors`, `rounds`, `top-n`, `cold-n` (positive integers; `cold-n` may be 0 and must not exceed `n-behaviors`), `writer` (`session` / `llm-chat`). A bad integer is a parse error — log it and stop. A bad `writer` value falls back to the default with a log line. Unknown keys are ignored with a log line. **There is no `refresh-lit` argument**: P1 always runs once per invocation and is never repeated inside the round loop.

Only a ` — ` immediately followed by `key: value` opens the option list; an em dash followed by prose belongs to the intention. When ambiguous, prefer the longer intention.

## Example run

```
/hypothesis-batch "Extend research on subliminal learning, per the paper: Subliminal
Learning: Language models transmit behavioral traits via hidden signals in data" — rounds: 10
```

`INTENTION` is the whole quoted string (the internal colons are prose, not keys). `ROUNDS = 10`; `N_BEHAVIORS`, `TOP_N`, `COLD_N` stay at their defaults, so the shape is ~100 candidates in, 10 claims out. `topic_slug` distils to `subliminal-learning`.

**Pool size and batch size price differently.** `rounds × n-behaviors` sets how wide Step 1 searches and how many candidates Step 2 must score — and Step 2 spends one `/novelty-check` **and** one `/research-review` per survivor, which dominates the bill. `top-n` alone sets Step 3's cost. Widen the pool to search harder; raise `top-n` only when you intend to read that many skeletons. The library accumulates across invocations, so several small runs and one large run reach the same place.

## Step 1 — Build the hypothesis library

### Phase 1: Literature survey

```
/research-lit "<INTENTION>" — output-dir: <OUTPUT_DIR>
```

Pass `INTENTION` verbatim — not `$ARGUMENTS` (which still carries the option list) and not the distilled `TOPIC`. The angle and constraint in the intention are what should aim the retrieval. **The `— output-dir:` override is required**, not optional: `/research-lit` writes to `idea-stage/` regardless of caller unless told otherwise.

Searches Zotero, Obsidian, local PDFs, the web, and the cloud mechanic-db (via `/mechanic-db-search`); builds a landscape map of sub-directions, approaches, and open problems; identifies structural gaps and recurring limitations. Outputs `RESEARCH_LIT.md` (raw dump, audit-only) and `LANDSCAPE.md` (synthesized landscape — Phase 2 reads this from disk), both in `OUTPUT_DIR`.

**Run this command exactly once per invocation, before round 1.** All `ROUNDS` generation rounds and the one permitted top-up round reuse these two files. Do not invoke `/research-lit` from inside the round loop, do not refresh the landscape between rounds, and do not define a refresh flag.

### Phase 2: The round loop — generate, dedup, score, persist

**Before round 1, full-load both strategy skills exactly once.** Read `/mechanism-behavior-discovery/SKILL.md` and `/mechanism-explore/SKILL.md` in full. The first supplies the five bars and the six discovery strategies; the second supplies the six mechanism directions, their combination strategies, and the claim-altitude rule. Read them; do not execute their phases, expect no output file, and do not copy their prose into any artifact. Log:

```text
[behavior-strategy] full-loaded /mechanism-behavior-discovery
[mechanism-strategy] full-loaded /mechanism-explore
```

This is run initialization, not part of a generation round. Retain both full texts as run context and reuse them through Phase 7; never re-read either file per round or again before claim writing. With a stateless `WRITER = llm-chat`, the orchestrator retains the loaded source and assembles only the phase-relevant material into each call.

**Both strategy skills are deliberately generic — they are shared with the rest of the project and say only *where to look*.** They do not say what makes a candidate worth persisting, and neither of them will stop a pool from collapsing onto one framing. The two axes this workflow is actually graded on live in **this** file: *Innovation moves* (the behavior side) and *Instrument diversity* (the mechanism side), both below. Load the skills for their search space; take the standard from here.

What all of this supplies is used at three different moments:

- **The bars, the innovation moves, and the instrument check are always on** — they filter every behavior in every pass, and a filter cannot anchor generation because it runs after it.
- **The discovery-strategy taxonomy and the instrument catalogue are withheld from the cold pass** — the named lenses, the eight moves, the apparatus list and their vocabulary are generation *scaffolding*, and scaffolding placed before the first idea decides which ideas are reachable. They enter at Round step 2b and never at 2a. What survives into 2a is the *question* the moves exist to answer — what would the expert have predicted, and what does this predict instead — asked in plain words, with no list attached.
- **Mechanism strategy shapes opportunity, not a finished mechanism.** Every candidate carries a one- or two-sentence `mechanism_opportunity`; only a Phase-5 survivor receives a full mechanistic hypothesis in Phase 6.

The strategy is advisory and never relaxes downstream filtering. A library entry **assumes** its phenomenon exists; its existence is settled only by running the claim's Experiment 1, downstream of this workflow.

### Generation contract: question → baseline → observable prediction

Do not begin by finding an effect and writing the justification afterward. Before drafting each behavior, the `WRITER` should internally form a **Problem–Prior–Prediction** triad as a drafting aid:

1. **Problem.** State the question and the context in which it is worth examining.
2. **Prior.** State the nearest known behavior or working expectation that gives the question a baseline.
3. **Prediction.** State the observable quantity, comparison, or condition that would distinguish the candidate.

This triad is a way to make candidates concrete, not an additional hard-scoring checklist. Use `statement`, `five_bars`, and `innovation` to express the behavioral claim; use `mechanism_opportunity` to preserve its mechanism-side potential; and draft `impact.rationale` during generation so importance is not invented after the candidate exists.

**Library setup (once).** Distil `TOPIC` and `topic_slug`. If `hypothesis_library.json` exists and its `topic` differs semantically from this run's, **halt and ask** — never silently overwrite another topic's library. A *different intention on the same topic* is not a conflict: keep accumulating, overwrite the top-level `intention`, and note the shift in the Phase 5 report. Otherwise start `{topic, topic_slug, intention, created, updated, behaviors: []}`.

**Write `topic.md` at `OUTPUT_DIR` root in the same step**, and never below it: every judge resolves the topic by walking up from the claim directory to the nearest `topic.md`, so one file at the root serves all `TOP_N` claims. Without it the judges score each claim with an empty topic and cannot check that it addresses the direction it was commissioned for. Three short parts, and nothing else — no landscape, no candidate list, no scores:

```markdown
# <TOPIC>

<the behavior area in two or three sentences: the phenomenon or domain being explored, and the reference result INTENTION names, stated as a finding rather than a citation.>

**Goal.** <what this run is asked to get out of the area — the wanted-result half of INTENTION, e.g. novel and counterintuitive phenomena with a mechanistic account, at a standard a top-conference reviewer would accept.>
```

If `topic.md` exists from an earlier invocation and the topic is unchanged, leave it; refresh only the `Goal` paragraph when the intention shifted.

Then run this cycle once per round, `round = 1..ROUNDS`.

**Round step 1 — Rebuild the banlist.** Re-read the library (it grew in the previous round's persist step). Keep the full library on disk for dedup and audit, but make the generation banlist compact: pass active behavior statements in full; represent eliminated or merged entries as one line each (`id` + phenomenon + trigger + delta fingerprint). Expand an old entry only when a new candidate is close to it. Under `WRITER = llm-chat`, the assembled prompt should contain this compact banlist rather than the full claim/review records.

**Round step 2 — Brainstorm, in two passes, never merged into one call.**

**2a — The cold pass (`COLD_N` behaviors).** One `WRITER` pass whose prompt carries **only** `INTENTION` verbatim, the `LANDSCAPE.md` gaps and open problems, the banlist, this round's slice, and the field spec. It carries **no** discovery-strategy list, no strategy names, no lens numbering — and says so explicitly, so the model does not reconstruct one from memory: *do not organize the output by any taxonomy of research strategies; propose whatever you would propose if none existed.* For every candidate, use the Problem–Prior–Prediction triad internally to make the question, baseline, and observable comparison concrete.

Ask for what a lens cannot ask for: what is actually strange, unexplained, or quietly assumed here — the observation that does not fit, the assumption everyone is standing on, the result that would most annoy whoever believes the standard account. One useful framing: *if you had to bet on one thing here being wrong, what would it be?*

`discovery_strategy` for a cold behavior is `"cold-pass"` and stays that way — **never back-fill it with the lens it happens to resemble**. Its `discovery_strategy_detail` still names a concrete provenance: a cold behavior is unprimed, not unmotivated.

**2b — The guided pass (`N_BEHAVIORS − COLD_N`).** One `WRITER` pass using the relevant discovery and mechanism strategy material from the two full-loaded skills. The cold pass's outputs are appended to this prompt's banlist, so the guided pass cannot re-derive what the cold pass found. Apply the same Problem–Prior–Prediction triad. The strategy text supplies directions for search and a mechanism lens; downstream reviewers still judge whether the resulting candidate is valuable.

**Both passes, every behavior, these fields:**

- `statement` — the phenomenon, its trigger, and its novelty delta, per *Writing a statement* below. The field the whole library is judged on.
- `discovery_strategy` — which lens produced it, as a **bare human-readable name** (`cross-modal transfer`, `cold-pass`). Never a numbered label copied out of the skill file.
- `discovery_strategy_detail` — one to two sentences of concrete provenance: which cross-discipline finding or past result was borrowed and mapped onto what. Provenance, **not** an experiment sketch — a detail that reads like a Methods paragraph means the behavior was written backwards from a protocol.
- `innovation` — `beyond_transfer` and `method`, per *The novelty delta* below.
- `mechanism_opportunity` — one to two sentences naming a plausible mechanism strategy, the **instrument class** it would use (§ *Instrument diversity*), a directional causal prediction, and why resolving it would add explanatory or actionable value. Keep the internal object at the class level (layer / head / feature / direction / circuit), never guess an exact identity before the experiment. The instrument is named so the pool can be tallied by it; a candidate whose instrument is the default chain is allowed, but the round-3 read will see how many of those the pool already holds.
- `five_bars` — one line each for Real / Non-obvious / Specific / Robust / Tractable.
- `impact.rationale` — one sentence authored with the candidate: why the problem matters, who would use the answer, and what decision changes if the result is true or false. The scorer may challenge it but may not invent importance after the fact.
- `gaps` — the `LANDSCAPE.md` structural gaps it is grounded on, each **restated in one self-contained line**; `[]` when it is grounded on none. `LANDSCAPE.md` is regenerable scratch, so a node must never carry a bare pointer into it.

**Each round gets a different slice of the search space**, given to both passes — it bounds *where* to look, not *how*, so it does not compromise the cold pass:

| Round | Assignment |
|---|---|
| 1 | the landscape's **structural gaps** — one behavior aimed at each gap `LANDSCAPE.md` names |
| 2 | the **behavior-discovery strategies and mechanism directions not yet used** in round 1 |
| ≥ 3 | the **under-covered cells** of the accumulated library, read along three axes: phenomenon class, the **instrument** each `mechanism_opportunity` would use (§ *Instrument diversity*), and the **innovation moves** (§ *Innovation moves*) the pool's deltas actually rest on |

The instrument axis prevents a pool in which every candidate defaults to location-plus-ablation, or to fitting one linear direction and steering it; the innovation axis prevents a pool where every delta is only "new domain" or "new trait." Rounds from 3 on are written **after** reading the library, so their assignment is derived, not guessed. Read both axes by tallying the pool, not by impression: count how many live nodes sit in each cell and aim the round at the empty ones.

**Every round's prompt carries `INTENTION` verbatim, and every behavior must answer to it.** The slice bounds the search space; the intention constrains what counts as a hit inside it. A behavior excellent for the topic but not serving the stated intention is a miss. The Problem–Prior–Prediction triad is only a compact way to write the candidate clearly.

**Spread the altitude.** A candidate may be a broad regularity in how the model reasons or a narrow effect scoped to one input→output pattern — both are good. Aim for a spread rather than a monoculture of tiny effects.

#### Writing a `statement`

`statement` is the node's load-bearing sentence and the only one most readers process. Phase 3 searches against it, Phase 4 reviews it, Phase 5 ranks on it, Phase 6 repackages it. **A statement that reads like a sentence from the anchor paper's abstract will be scored as that paper** — the novelty check finds the source and the node dies at the gate.

That failure is the path of least resistance, not carelessness: `INTENTION` names a reference result, the result has a canonical phrasing, and the fastest way to write a falsifiable sentence is to change one slot in it — the objective, the trait, the modality, the domain. The pool then reads as one paper inflected `ROUNDS × N_BEHAVIORS` ways.

**One test, run on every statement before it is persisted.** If the statement can be produced by substituting nouns — into the anchor paper's own claim, or into a sibling from the same round — it is not yet a behavior of its own. Rewrite it once; if the second version still fails, replace the behavior. A related tell: if the clause carrying the *setting inherited from the source* is longer than the clause carrying *what this node predicts*, the node is mostly restatement — cut the setup to what falsifiability needs and spend the sentence on the prediction.

**What a statement must contain**, in whatever order reads best:

- **The triggering condition** — what has to be true for the phenomenon to appear, and where it sharpens the claim, the condition under which it should *not* appear.
- **The phenomenon** — a falsifiable regularity in observable behavior, with a direction, and with the quantity it is measured in named.
- **The delta clause** — what the standing account predicts *instead*, and what this node predicts against it. This is where `discovery_strategy_detail`'s content lands: **the borrowed idea's content is written into the statement as the reason the prediction has the shape it does**, while the fact that it was borrowed stays out.

**Register.** No taxonomy vocabulary («cross-domain transfer», «this behavior is tractable»), no account of the search («we borrowed from»), no reference to the library, the round, or another node. Two to three sentences: one is too few to carry a delta clause, past three it has become a plan. Numbers beat quantifiers.

> **Carrying its delta:** *Preference optimization should destroy a hidden trait channel rather than carry it: its gradient is a contrast between two responses, so any signal shared by the chosen and the rejected one cancels before it reaches the weights. We predict the opposite, and predict it to behave differently in kind — trait transfer under preference training survives, but its strength tracks the within-pair asymmetry of the carrier rather than the size of the corpus, so the standard hygiene of raising pair quality should increase transfer where it is expected to reduce it.*

#### The novelty delta

Every behavior carries an `innovation` object whose two entries are answerable questions with checkable answers:

```json
"innovation": {
  "beyond_transfer": "<what is still new if the borrowed phenomenon reappears here exactly as its source predicts>",
  "method": "<the one move in the design that is not standard practice for this phenomenon>"
}
```

`beyond_transfer` says what the candidate establishes beyond the source result: a new quantity (a rate, capacity, half-life, boundary, or interaction), a prediction that competes with the standing account, a condition under which the source result should fail, a setting-specific failure mode or constraint that the new context creates rather than inherits, or a use the phenomenon is put to. A new domain, modality, or scale is a **starting point, never the answer** — it says where the work happens, not what it establishes, and left at that it is the profile of an incremental candidate. Produce the answer with one of § *Innovation moves*, and name which move it was.

`method` is the adapted instrument, the imported paradigm, the measurement taken where nobody takes it, the rescue arm, the unit of analysis that had to be defined — the catalogue is § *Instrument diversity*. Restating the anchor paper's own design is not an answer; that is the control condition the new design has to beat. A behavior may legitimately reuse a standard design **when `beyond_transfer` carries the whole delta** — say so in the field, in those words.

#### Innovation moves

Where `innovation.beyond_transfer` actually comes from. The six discovery strategies say **where to look**; they do not by themselves produce a claim. A transfer that lands exactly where its source predicts contributes a data point — the domain changed and nothing else did — and that is the most common way a competently written candidate still reads as incremental.

So state, for every behavior: *if the borrowed phenomenon reappears here exactly as its source predicts, no surprises, what is still new?* If the honest answer is "the domain is new", "the modality is new", or "it runs on a bigger model", the candidate is not ready. **Novelty lives in the claim, the condition, or the instrument — name which one.** The moves below are the ways it gets there; one is enough, and `discovery_strategy` records which was used so the round-3 coverage read can tally them.

1. **Adapt the mechanism to the setting, don't relocate the test.** Ask what this setting has that the source did not — a structure, a constraint, a modality, an actor — and make *that* what the claim turns on. A setting interchangeable with any other high-stakes one is decoration: the claim should break, or change shape, when it is swapped. Weak: *does effect E also happen in medicine?* Strong: *E is carried by a channel that exists only where an intermediate model rewrites the data, so E survives triage summarization and dies under structured extraction.*
2. **Predict against the source.** State the condition under which the standing account should **fail** or reverse sign, and make that the claim. A prediction that agrees with the incumbent in every regime is testing it, not competing with it.
3. **Aim at the boundary, not the reappearance.** Not "does it happen too" but "where does it stop" — the flipping point, the threshold, the decay curve behind an apparently binary rule, the regime where a qualitative account turns out to be quantitative. A measured boundary is a contribution even when the phenomenon is known.
4. **Change the measured quantity.** Keep the setting, measure what the source could not: a rate rather than a presence, a capacity rather than an effect, a half-life rather than a snapshot, an interaction rather than a main effect, a per-item attribution rather than a corpus average. New quantities are where laws come from.
5. **Import the paradigm, not the finding.** Borrowing a *result* from another discipline gives an analogy; borrowing its **apparatus** gives a design nobody here has run. See § *Instrument diversity* for the catalogue.
6. **Compose two independent results into a prediction neither makes.** Two established findings never put in the same experiment, and the joint prediction derived from them. The composition is the contribution and is falsifiable in a way each ingredient alone is not.
7. **Turn the phenomenon into an instrument.** A behavior that is merely alarming becomes a contribution when it is used to *measure* or *do* something else — detect provenance, audit a pipeline, estimate a previously unmeasurable quantity, serve as a defense. "Here is a worrying effect" becomes "here is a tool", which is what gets built on.
8. **Attack the assumption the field rests on.** The load-bearing assumption everyone shares because nobody has tested it — filtering works, retraction erases, the benchmark measures what it says, the control is neutral — with the phenomenon as the demonstration that it does not hold. The stakes come free; the work is constructing the case where the assumption is genuinely tested rather than merely doubted.

**High-stakes settings are worth aiming at, and they are not a substitute.** Chemistry, biology, medicine, clinical decision-making, law, and finance raise the value of an answer; a transfer into one of them still owes one of the eight moves above.

#### Instrument diversity

Where `innovation.method` and, later, Phase 6's method-innovation line come from. `/mechanism-explore`'s six directions and five combinations are the field's standard vocabulary — competence, not contribution. **A mechanism plan that could be copy-pasted onto a different phenomenon by changing the nouns is not part of the contribution**, and a pool in which every `mechanism_opportunity` reduces to *fit a linear direction, steer it, report a dose-response* or *locate a component, ablate it, report a drop* has one instrument, however many phenomena it has.

Each candidate's `mechanism_opportunity` therefore names its **instrument class**, and the round-3 coverage read tallies the pool by that class. One of these moves is enough:

1. **Adapt the instrument to the phenomenon.** The standard probe measures a quantity adjacent to the one the claim is about — a linear probe reads *decodability*, not *use*; an ablation reads *necessity in this forward pass*, not *responsibility*. Name the mismatch, then close it: change what the probe predicts, the population it is fit on, the intervention's granularity, or when in the pipeline it applies.
2. **Import an apparatus from another discipline.** Concretely — *which design, mapped onto which internal object, measuring which quantity*; "inspired by neuroscience" is not an import.
   - **Genetics** — knockout **and rescue**, epistasis (does ablating A change B's effect?), complementation, heritability across distillation "generations".
   - **Pharmacology / epidemiology** — dose–response with an EC50, survival and time-to-event for a decaying trait, washout and re-challenge, matched-cohort exposure–outcome.
   - **Psychophysics** — staircases and detection thresholds, just-noticeable differences, d′ separating sensitivity from bias.
   - **Econometrics** — instrumental variables where a clean intervention is impossible, difference-in-differences across checkpoints, formal mediation splitting direct from indirect effect, regression discontinuity at a training-stage boundary.
   - **Information theory** — channel capacity and rate–distortion for how much a representation can carry, MDL for whether a probe reads structure or memorizes.
   - **Physics** — order parameters, phase diagrams and critical points, finite-size scaling across model scale, susceptibility.
   - **Ecology / evolution** — competition for a shared resource, carrying capacity, selection–drift decomposition across training.
3. **Rescue, not just ablation.** Necessity is cheap and ambiguous. Remove the component and then **restore the behavior by re-supplying it alone**, in a model or condition where it was absent. Sufficiency evidence is rare here, and building the rescue arm is often the whole methodological contribution.
4. **Invent the unit the phenomenon lives in.** Layer, head, neuron, SAE feature, direction are inherited units. When the phenomenon fits none of them — it is a relation between two models, a property of an update, a statistic of the corpus, a trajectory across checkpoints — define the unit it *is* described by, and say how it is measured and intervened on.
5. **Move the measurement to a stage nobody measures.** Almost all method effort is inference-time on a finished model. The gradient at the update, the difference between two checkpoints, the geometry of the weight delta, per-example influence — all measurable, comparatively unexplored, and a claim about how something *forms* is not testable at inference time at all.
6. **Build the two-system design.** Teacher and student, base and finetune, model and its own earlier context, monitor and monitored: cross-model patching, shared-subspace estimation, aligning two representation spaces before intervening, matched pairs where the pairing is the manipulation. The toolkit is thinnest here and a modest step is most visible.
7. **Make the mundane rival a measurement, not a caveat.** Every mechanism claim has boring nulls — memorization, surface form, tokenization, position, capability confound — usually handled by a sentence in the limitations. Turn one into its own measured quantity, with a control that estimates how much of the effect it accounts for.

**The check, before persisting the candidate:** write the standard way to investigate a phenomenon of this kind, and what this one does instead and what that buys. If the second is empty, or is only "we also run an SAE", the candidate carries a standard chain — either apply a move or say in `innovation.method`, in those words, that the design is standard and the delta is entirely in `beyond_transfer`.

**Round step 3 — Dedup, including the delta check.** One `REVIEWER_BACKEND` judgment over both passes' output and the whole library at once. Flag each new behavior `new` or `duplicate-of:<Bk>`; drop duplicates and merge any extra nuance into the existing node's `notes`. Three things count as duplication:

1. **Same phenomenon under the same trigger**, whatever the wording says.
2. **Template collapse** — two behaviors differing only in the slot filled into a shared setup sentence (same trigger, same measurement, same predicted direction, different trait or domain or objective). The library keeps the general statement and lists the instantiations in `notes`. Ten trait names in ten nodes is one node with a list, and it is what makes a pool look full while covering one idea.
3. **Empty delta** — an `innovation.beyond_transfer` that simply restates the anchor finding without adding a distinct question, quantity, condition, or context-specific angle, or a `method` that restates the anchor design. A domain or modality transfer is not automatically empty; if its contribution is still unclear, send it back to `WRITER` **once** with the failing point quoted, and if the second pass still has no usable delta, drop it before persisting and count it as `dropped: transfer-only`.

When a cold behavior and a guided behavior collide, **keep the cold one** and merge the guided one's nuance into it — the cold statement was reached without the scaffolding and is usually the less templated of the two.

Report `duplicates dropped` and `transfer-only dropped` separately in the round ledger. Dropping the empty-delta cases here is cheap; Phase 3 would spend a full literature search discovering the same thing, and Phase 5 would cut them after the pool had already been shaped around them.

**Round step 4 — Impact score.** Score each survivor's importance on `REVIEWER_BACKEND` following `/impact-check`'s dimensions — does it address an important problem, would named consumers use or cite it, could it shift a field's direction or a consequential decision, does it help applications or cross-disciplinary work, does it reveal an important phenomenon even with a simple method. This is an unsearched estimate that cuts nothing; the final impact judge performs the required web search on selected claims. Judge the `WRITER`-authored `impact.rationale`; do not manufacture a stronger value proposition. Return `score` (1–10), `recommendation` (`PROCEED` / `PROCEED WITH CAUTION` / `DEPRIORITIZE`), and `date`. If the rationale is unsupported or post-hoc, return it to `WRITER` once with the objection rather than rewriting it as reviewer prose.

Judge importance **on its own merits, not against `INTENTION`** — a behavior serving the intention perfectly but mattering to nobody scores low. The intention belongs in the `rationale`'s "who would build on it" half and does its ranking work later, as Phase 5's tiebreak. **No cut happens here.**

**Round step 5 — Merge and persist.** Assign ids by max-suffix+1, never reused: `B1`, `B2`, …. Set `status: "candidate"`, stamp `added` and `updated`. Write `hypothesis_library.json` **now, before the next round** — this persisted state is the next round's banlist.

Every authored field — `statement`, `five_bars`, `discovery_strategy_detail`, `innovation`, `mechanism_opportunity`, `notes`, `impact.rationale` — is `WRITER`'s own wording, carried through verbatim. The orchestrator performs only the mechanics: assigning ids, stamping `status` / `added` / `updated`, stripping a numeric prefix off a strategy label, merging, and writing the file. It never rewrites, paraphrases, tightens, or translates an authored field; a field that needs changing goes back through `WRITER`. Under `WRITER = llm-chat` the plumbing enforces this; under the default it holds by discipline — **author the field, then stop**, and treat the merge as bookkeeping rather than a second editing pass.

**Early stop.** If a round adds **0** survivors after dedup, stop the loop and note it in the Phase 5 report. Never pad a round with near-duplicates to fill it.

#### Library schema

Step 1 writes exactly these fields; Step 2 adds its own. Nothing else is written here.

```json
{
  "topic": "<topic>",
  "topic_slug": "<slug>",
  "intention": "<INTENTION, verbatim>",
  "created": "<YYYY-MM-DD>",
  "updated": "<YYYY-MM-DD>",
  "behaviors": [
    {
      "id": "B1",
      "pass": "<cold | guided>",
      "discovery_strategy": "<bare lens name, or \"cold-pass\">",
      "discovery_strategy_detail": "<the concrete provenance of the conjecture — provenance, not a protocol>",
      "statement": "<phenomenon + trigger + delta clause, two to three sentences>",
      "innovation": {
        "beyond_transfer": "<what is still new if the borrowed phenomenon reappears exactly as predicted>",
        "method": "<the one non-standard move in the design, or an explicit 'standard design; the delta is entirely in beyond_transfer'>"
      },
      "mechanism_opportunity": "<one or two sentences: plausible strategy + directional causal prediction + explanatory/actionable value>",
      "five_bars": {"real": "", "nonobvious": "", "specific": "", "robust": "", "tractable": ""},
      "impact": {
        "score": 8,
        "rationale": "<why it matters + who would build on it>",
        "recommendation": "<PROCEED | PROCEED WITH CAUTION | DEPRIORITIZE>",
        "date": "<YYYY-MM-DD>"
      },
      "gaps": ["<each landscape gap restated in one self-contained line>"],
      "notes": "<optional merged nuance>",
      "status": "candidate",
      "added": "<YYYY-MM-DD>"
    }
  ]
}
```

`pass` records which half of Round step 2 produced the behavior; it is stamped by the agent, not authored. `status` lifecycle: `candidate` → `selected` / `eliminated` (Phase 5) → `explored` (flipped by hand when the user promotes a claim into an `/auto` round).

**No full mechanism axis.** The library remains behavior-first and stores only the lightweight `mechanism_opportunity` needed for early novelty/impact evaluation and later handoff. The falsifiable mechanism context is instantiated in Phase 6 for `TOP_N` survivors only and lives in the claim-writing context, not as a second library taxonomy.

## Step 2 — Evaluate and select the top N

### Phase 3: Deep novelty verification (hard gate)

One `/novelty-check` per behavior with `status: "candidate"`, dispatched in parallel:

```
/novelty-check "[behavior Bk: statement + trigger + innovation + mechanism_opportunity + why it would be surprising]"
```

Multi-source literature search (arXiv, Scholar, Semantic Scholar), cross-verification with the external reviewer, a check for concurrent work in the last 3–6 months, and identification of the closest existing work.

**Check the delta, not just the phenomenon.** Pass `innovation` into the prompt and require the verdict to address it. A behavior whose phenomenon is reported in the literature is **not** automatically eliminated if its `beyond_transfer` is a quantity, boundary, or prediction that no found work establishes — eliminating it collapses the workflow into hunting for phenomena nobody has ever mentioned. Conversely, a behavior whose delta the search finds, in a paper the statement never anticipated, is eliminated even when its surface framing looks fresh. The hard publication bar is *the claim as stated is already established*, not *this area has been studied*; the stronger novelty target is whether the claim challenges an expert prior or a standing boundary. Record which of these the verdict turned on.

Judge both novelty axes exposed by the final evaluator: **phenomenon/scene** and **mechanism/measurement**. A candidate need not be new on both, but its `mechanism_opportunity` must be searched rather than treated as automatically novel. A standard location→ablation chain adds no novelty by itself; the contribution must come from the behavior delta or from the specific measurement/causal design.

**This is the only hard gate.** Eliminate anything already reported: `status: "eliminated"`, `selection.reason = "already published — <the work>"`. Behaviors are never deleted; an eliminated node stays as a citable record of what was tried.

For each survivor, record its **three nearest works** with the specific finding each established — Phase 6's `Related Work` and checklist item 1 both need exactly this, and re-deriving it later wastes a second literature pass.

### Phase 4: External critical review

One `/research-review` per novelty survivor — the full pool, not a shortlist — dispatched in parallel:

```
/research-review "[behavior Bk: statement + five bars + innovation + mechanism_opportunity + important problem + impact rationale + nearest works]"
```

The external reviewer acts as a senior reviewer (NeurIPS/ICML level): scores the behavior as a study target, identifies weaknesses, suggests minimum viable improvements, and gives concrete feedback on experimental design.

Reviewing the full pool is deliberate: novelty and impact both judge *whether the question is worth asking*, and neither can tell whether the phenomenon can actually be measured. That is the reviewer's lens, and it is worth having **before** the batch is fixed.

Classify each review as one of two kinds, because Phase 5 depends on the distinction:

- **Fatal design flaws** — the phenomenon is not falsifiable as stated, the measurement cannot reach the quantity it claims to measure, a confound is structural rather than controllable, no accessible model could exhibit the trigger. Refinement cannot rescue these; they are grounds for elimination.
- **Ordinary weaknesses** — incremental framing, execution risk, thin baselines, unclear presentation. These are what Phase 6's refinement is for and must **not** eliminate anything.

#### Step-2 fields

Phases 3–5 write these back into each behavior node:

```json
{
  "novelty": {
    "score": 7,
    "verdict": "<NOVEL | ALREADY PUBLISHED>",
    "nearest_works": [
      {"work": "<author, year — title>", "established": "<the specific finding it established>", "separation": "<what this contradicts / extends past its scope / looks at where it never looked>"}
    ],
    "date": "<YYYY-MM-DD>"
  },
  "review": {
    "score": 6,
    "fatal_flaw": "<the flaw, or null>",
    "weaknesses": ["<ordinary weakness>"],
    "date": "<YYYY-MM-DD>"
  },
  "selection": {
    "rank": 3,
    "verdict": "<selected | eliminated>",
    "reason": "<why — required when eliminated>",
    "claim_dir": "claims/03_<name>"
  }
}
```

### Phase 5: Select the batch of TOP_N

The only cut that produces the batch.

**Step 1 — Apply the veto.** Eliminate every behavior whose Phase 4 review found a **fatal design flaw**, regardless of impact. A phenomenon whose measurement cannot answer its own question does not become shippable by being important. `selection.reason = "vetoed at external review — <the flaw>"`.

**Step 2 — Rank the rest** by the **balanced bottleneck** `min(impact.score, novelty.score)`. Novelty and impact are co-primary: a candidate is limited by whichever of the two is weaker, so a high-impact but merely incremental idea cannot outrank a comparably important idea with stronger novelty just because impact came first. Use `review.score` as the next tie-breaker, then alignment with `INTENTION`; never let either tie-break override the veto or the Phase 3 novelty gate. Do not form a weighted total — the bottleneck is the whole ranking signal.

**Step 3 — Take the top `TOP_N`.** Everything below gets `status: "eliminated"`, `reason = "below rank <TOP_N>"`. This ranking fixes the folder numbering; nothing downstream re-orders it.

**Step 4 — Check the spread.** If the top `TOP_N` collapse onto two or three phenomena classes, swap the lowest-ranked duplicates for the highest-ranked candidates covering a distinct class, and record each swap in `notes`. `TOP_N` skeletons on one class is a worse batch than `TOP_N` on eight, even at slightly lower average score.

**If fewer than `TOP_N` survive**, run **one** top-up round: return to Phase 2, generate behaviors aimed at the gaps the eliminations exposed, and put them through Phases 3 → 5. If still short, ship what survived and state the shortfall plainly. Never pad with an already-eliminated behavior, never overturn a novelty verdict or a design veto to reach `TOP_N`.

**Report.** `INTENTION` verbatim, the distilled `TOPIC`, `ROUNDS` requested vs actually run (note any early stop), a per-round ledger (round → cold added / guided added → duplicates dropped → transfer-only dropped → running total), total pool size, eliminations by reason, the impact distribution (min/median/max), and the selected `TOP_N` with ranks and claim directories. After Phase 7, append each claim's final `(novelty, impact, clarity, feasibility)` tuple and the evaluation pass retained; do not collapse it into an overall score.

## Step 3 — Mechanism and claim

### Phase 6: Instantiate the mechanism for each selected behavior

Do **not** load `/mechanism-explore` here; its full text was loaded once in P1.5. Phase 6 applies that run-level strategy context to one selected behavior. It converts the node's short `mechanism_opportunity` into the falsifiable mechanism context that `claim.json` needs; it does not reopen discovery or choose an unrelated phenomenon.

**Run the claims one at a time, in Phase 5 rank order** — claim `01` is finished and closed before `02` starts. This is what keeps each claim's numbers, conditions, and slug from bleeding into its neighbours. Phases 3 and 4 stay parallel; only Step 3 serializes.

**Step 0 — Instantiate the mechanism.** Starting from the persisted `mechanism_opportunity`, frame a **falsifiable mechanistic hypothesis** for the claim being worked:

- the **internal object** held responsible — layer / head / neuron / SAE feature / direction / circuit;
- the **predicted causal relation** — ablate → effect, steer → dose-response, patch → localization;
- at least one **boring null** — memorization / surface feature / shortcut / tokenizer / position;
- the `/mechanism-explore` combination strategy it commits to (e.g. Location → Causal Intervention), chosen for *this* behavior and justified in one line;
- **the method-innovation line** — what this investigation does that is not the standard recipe for a phenomenon of this kind, and what that buys, drawn from § *Instrument diversity* and written as the two-sentence check at the end of that section. It inherits the behavior's `innovation.method`, committed to back in Phase 2: **the mechanism makes good on that commitment or explicitly supersedes it with a stronger one.** Silently reverting to the default chain ships a design the behavior's own node already called insufficient.

Prefer a hypothesis on a **climbable ladder of evidence**. Hold the expanded mechanism in claim context — it surfaces as `claim.json`'s H-list. Do not replace the node's lightweight `mechanism_opportunity` with this longer form or add a full mechanism axis to `hypothesis_library.json`.

**Step 1 — Create the directory.** Derive `<name>`: a **snake_case slug, ≤ 6 words, naming the phenomenon** — the same slug that becomes `claim.json`'s `Name`. Derive it once and reuse it verbatim; directory and `Name` must not diverge. Create `claims/<NN>_<name>/` at the zero-padded rank, write the path back as `selection.claim_dir`, and log `[claim] <NN>_<name> — "<behavior statement>"`.

**Step 2 — Draft.** `WRITER` writes the seven keys in one pass, in the write order below. Assemble the input first:

- the behavior node in full — `statement`, `five_bars`, `discovery_strategy_detail`, `innovation`, `gaps`, `impact.rationale`;
- its persisted `mechanism_opportunity`;
- its three `novelty.nearest_works`, each with the finding it established and the separation;
- the Step-0 mechanism — internal object, causal relation, boring nulls, combination strategy, method-innovation line;
- the Phase 4 reviewer feedback, ordinary weaknesses included — those are what this draft is meant to fix;
- `INTENTION`, verbatim. The claim **serves** it and never quotes it: its constraint half (affordable scale, setting, what kind of model has to settle it) binds concrete choices in `Experiments`, and its wanted-result half is what the sentence naming who acts on the answer should be useful to. It supplies no framing vocabulary — a claim echoing the user's phrasing reads as a restatement of the request rather than a paper;
- this phase's specification, from `Feasibility and clarity` to `Write order`.

At the default `WRITER = session` the agent drafts directly and can read what it needs from disk — but *re-read the behavior node and the mechanism explicitly* before writing. Drafting from what happens to still be in context is how a claim ends up carrying a neighbour's numbers. Under `WRITER = llm-chat` the same material must be pasted into the prompt.

### Phase 7: Draft, evaluate, revise once, and ship

**Step 3 — Evaluate the initial draft.** Run the following three prompts as independent, parallel judges against the complete current `claim.json` and `TOPIC`:

```text
/data/wmr/hypothesis-eval/eval_prompt/hypothesis_judge_novelty_zh.md
/data/wmr/hypothesis-eval/eval_prompt/hypothesis_judge_impact_zh.md
/data/wmr/hypothesis-eval/eval_prompt/hypothesis_judge_testability_zh.md
```

Follow each prompt's dimension isolation, required web search, percentile calibration, and exact output schema. Novelty and impact each return one 0–10 integer; testability returns separate `clarity` and `feasibility` integers and **no combined total**. Never invent a weighted overall score.

Keep evaluation artifacts out of the reviewer-facing claim directory. For pass `p`, create `.mechanist/traces/hypothesis-batch/<run>/claims/<NN>_<name>/eval-p<p>/`, place the current draft there as `claim.json`, and treat that trace folder as `<claim_dir>`. The judges write only their own exact files there:

```text
score_novelty.json
score_impact.json
score_testability.json
```

**Step 4 — Reflect and revise once.** `WRITER` receives the current claim in full, the frozen Problem Anchor, and the three score files including their justifications. It extracts the highest-leverage material correction on the weakest dimension, then emits a complete seven-key `claim.json`. The judges identify defects; they never rewrite the claim. The writer may clarify novelty against a nearest work, strengthen the consequence on both true/false branches, or repair directionality, thresholds, controls, and feasibility. It may not switch to a different behavior merely to earn a higher score, add experiments whose only purpose is to look sophisticated, or trade away impact to inflate testability.

Hold a **Problem Anchor** across the rounds: the behavior statement and the mechanism as frozen in Phases 2 and 6. Refinement sharpens how the claim is tested and written; it may not drift onto a different phenomenon. If a critique can only be answered by changing the phenomenon, that is a mechanism-direction switch, not a refinement.

**Step 5 — Evaluate the revision.** Run the same three judges again, independently and in parallel, in `eval-p2/`. This second score set is the final evaluation. The target for a strong claim is novelty ≥ 7, impact ≥ 7, clarity ≥ 5, and feasibility ≥ 5; these are quality targets, not a weighted score. If the writer identifies no material revision after pass 1, stop early and treat pass 1 as final. If the revision regresses without repairing the weaker dimension, retain the best-so-far draft rather than blindly shipping the last version.

**Step 6 — Verify and ship.** The orchestrator — not `WRITER`, not the reviewers — checks JSON validity, key names and order, plain-string values, the full `Quality checklist`, and internal numerical consistency. Mechanical faults (key order, escaping, a stray placeholder) it repairs directly; anything that changes the argument goes back through `WRITER` with the failing check quoted, so the prose stays in one voice. At the default the checker and the author are one model, so **run the checklist as a checklist** — item by item, against the file as written, not against what you remember intending. Items 1, 7, and 8 are found by looking. Then write only `claims/<NN>_<name>/claim.json` and close the claim; final score files remain in the trace and are summarized in the run report.

**Failure isolation.** If a claim cannot be brought through, record it in the behavior's `notes` and `status` and continue with the next. One bad claim never aborts the batch.

**No second plan.** The experiment design lives in `Experiments` and nowhere else. Do not emit `EXPERIMENT_PLAN.md`, `FINAL_PROPOSAL.md`, or `refine-logs/`, and do not invoke `/research-refine-pipeline`, `/research-refine`, or `/experiment-plan`. The executor-facing markers those plans carried — `kind:`, `method_sensitive:`, `depends_on:`, `grid:`, `cmd:` — are **forbidden in `claim.json`**: a reviewer holding only this file cannot decode them. The M0 gate survives as Experiment 1's four outcomes, written as prose.

#### The specification

Everything from here to `Quality checklist` is handed to `WRITER` in Step 2 and verified against in Step 4. `claim.json` is **the final result of the whole workflow** — a paper skeleton good enough to submit to a top AI conference, written for a human expert reviewer who has that file and nothing else.

**This stage plans; it does not run.** Every model, dataset, condition, and measurement named in `Experiments` has to be reachable today rather than aspirational. Nothing is executed here, and **anything phrased as a result is a fabrication**.

#### Feasibility and clarity

Before writing, and again before shipping: *first carefully consider the quality, novelty, and feasibility of the proposal you just created.*

**Feasibility is executability, not cost.** The question is whether the experiment can be run **as written**: every artifact it depends on already exists or the plan says how to build it, every step is a defined operation rather than a magic step ("automatically identify the relevant circuit" is a magic step), and the controls that a negative result needs are designed in rather than assumed. Novelty bought with an unrunnable plan is not novelty.

**Cost is not a feasibility risk.** Assume the executing lab has ample compute, ample annotator time, and full access to gated weights and paid data. GPU count, model size, the number of finetuning runs, annotation volume, and closed-weight access are budget and access questions, not executability questions — never shrink a design, drop a condition, downgrade a model, or add a cheaper fallback arm in order to look affordable. A claim made smaller to fit an imagined budget loses real novelty and impact to buy nothing.

**Quantify the resources anyway.** Figures are what let a later researcher plan the work: model ids with parameter counts, items per condition and total item count, number of training or finetuning runs, total GPU-hours, and annotation volume in items and annotator-hours where humans are involved. «A large language model», «a large-scale corpus», «several annotators» fail this. An undecomposed total is acceptable; silence is not.

**Clarity.** *Ensure the proposal is clear and concise, and the JSON is in the correct format.* A threshold with no stated basis, an equivalence claim with no margin, and a prediction with no direction are clarity failures, not stylistic ones.

#### Schema and fields

Seven keys, exactly these names, exactly this order, every value a plain prose string. No extra keys, no nested objects, no arrays. Paragraph breaks inside a value are `\n\n`.

```json
{
  "Name": "...",
  "Title": "...",
  "Short Hypothesis": "...",
  "Related Work": "...",
  "Abstract": "...",
  "Experiments": "...",
  "Risk Factors and Limitations": "..."
}
```

**`Name`** — a short descriptor: lowercase, no spaces, underscores allowed. It is the same snake_case slug, ≤ 6 words, naming the phenomenon, derived in Step 1; the directory name and this field must not diverge.

**`Title`** — catchy and informative.

**`Short Hypothesis`** carries the whole claim in one paragraph: the **triggering condition** (what has to be true for the phenomenon to appear), the **phenomenon** (a falsifiable regularity in observable behavior), the **internal object** held responsible, and **H1…Hk** — two to four sub-hypotheses, each with a stated direction. H1 is always the existence claim. The last H is the one that pays: a causal intervention or an edit that moves the behavior, not another correlation. Clarify the need for this specific direction, that this is the best setting to investigate it, and that there is no obviously simpler way to answer the question.

*Organize it around the advantage, not only the protocol.* Four fields of the behavior node carry what makes the claim worth reading: `statement`'s delta clause and `five_bars.nonobvious` for what the standing account predicts instead, `innovation.beyond_transfer` for what this establishes even if the effect lands exactly as predicted, `discovery_strategy_detail` for why one would expect it here at all, `impact.rationale` for who acts on the answer. A clause or a sentence each, written as part of the claim rather than as a note about it. Trigger + phenomenon + H-list + thresholds alone says what will be measured without saying what would be surprising about the answer.

**`Related Work`** names real, citable work — author and year — and for each says *what result it established*, then what this claim contradicts, extends past its stated scope, or looks at where it never looked. «They study X, we study Y» is a topical separation and does not count. It closes with at most one positioning sentence, every clause of which must survive checklist item 1.

**`Abstract`** (~250 words) reads like the abstract of a paper someone would actually open: human-legible motivation first, then the controlled design, then the hypotheses in a sentence each, then what a positive result gives the field. That ordinary arc is also what makes novelty and impact visible without ever asserting them. Opening on the design instead («This plan tests whether…») starts the reader past the motivation and the surprise.

It is assembled from four fields of the behavior node, every one **repackaged, never transcribed**:

1. **`discovery_strategy_detail` → the opening motivation**, rewritten as a claim about the world that makes the reader expect the phenomenon might exist — not as an account of the search that produced it. When the borrowed source is citable, the citation goes to `Related Work` and only its content stays here.
2. **`statement` → the controlled-design sentence.** The phenomenon and its trigger restated once in the paper's register, with the same direction and the same numbers `Short Hypothesis` uses. Keep the **delta clause** — it is the half most often dropped in this restatement and the half a reviewer is reading for — and keep it as a competing prediction rather than a hedge.
3. **`innovation` → what the paper adds.** `beyond_transfer` becomes the sentence saying what this establishes *that would still be worth knowing if the effect turns out exactly as expected*. `method` becomes a clause in the design sentence naming the instrument that makes the measurement possible, and it must match what `Experiments` does. Neither surfaces as a claim about the paper's own novelty: no «our key innovation is», no «unlike prior work we are the first».
4. **`five_bars` → the surprise and the scope.** `nonobvious` becomes what a reader would have predicted instead; `real` becomes the reason the effect is a phenomenon rather than an artifact; `specific` becomes the bound on what is claimed. `robust` and `tractable` stay out — they justify studying the behavior, which is Step 2's business — unless one carries a number `Experiments` also reports, which then appears once, here.

*The packaging is the point.* None of the source vocabularies may surface: no «discovery strategy», no «five bars», no «non-obvious», no «novelty delta», no «beyond transfer», no «we borrowed this from». Each field dissolves into a sentence that had to be written anyway. **The test: a reviewer must not be able to tell the Abstract was assembled from a JSON node**, nor recover which sentence came from which field.

> **Transcribed:** *Subliminal learning is a phenomenon where traits transmit through semantically unrelated data. This behavior is real because the effect has been observed at multiple scales, non-obvious because filtering is assumed to work, and specific because it is scoped to same-initialization teacher-student pairs. The idea was reached by transferring the notion of a carrier signal from steganography.*
>
> **Repackaged:** *A student model finetuned only on a teacher's number sequences — no trait words, no semantic content that survives filtering — still inherits the teacher's behavioral trait. Data filtering is the defense every distillation pipeline currently relies on, and it is defeated here by construction rather than by an oversight, in the way a steganographic channel defeats a content filter: the signal is carried by the choice among equally valid outputs, not by the outputs' meaning. We ask what that channel is made of, and find it survives only where teacher and student share an initialization — a bound that turns an alarming general result into a checkable deployment condition.*

**`Experiments`** is the field a reviewer skims hardest: labelled paragraphs separated by `\n\n`, in this order. Be specific in exactly how you would test the hypothesis, detail precise algorithmic changes, and include the evaluation metrics.

1. **Models** — named ids with sizes and access mode.
2. **Benchmark / data** — where it comes from (existing / adapted / constructed), item count, item structure, how ground truth is established. If constructed, say what a single item looks like.
3. **Conditions** — the manipulation as a labelled set (C0 baseline … Cn), plus any parametric sweep.
4. **Measurements** — what is read off per item and condition, and how each is computed.
5. **Experiment 1 … Experiment k** — one per hypothesis, in ladder order, each headed by the hypothesis it tests and the finding it would produce. Each states its goal, procedure, measurement, and **prediction — with a direction, and with the band in which the measurement would not decide**.
6. **Ablations and controls** — matched controls, off-target checks, confound checks.
7. **Resources** — the run in figures: total GPU-hours (per experiment where they differ), number of training or finetuning runs, items per condition and in total, and annotation volume in items and annotator-hours where humans are involved. This paragraph states what the work costs; it never argues that the cost is modest, and it is not a place to scope the design down.
8. **Metrics** — the flat list of every quantity reported.

**`Risk Factors and Limitations`** is numbered, and every entry is a threat that could actually land — the probe measures the wrong thing, the effect is a template artifact, the intervention has side effects, the ground truth is contestable — each paired with the specific mitigation already present in `Experiments`. A limitation with no mitigation is allowed only when genuinely out of scope, and must say so.

#### The experiment ladder

`Experiments` is organized as a ladder, cheapest and most falsifying first. Each rung becomes one numbered experiment, and a later rung is only worth running if the earlier ones hold.

| rung | what it establishes |
|---|---|
| 1 | the phenomenon happens at all, under its stated trigger |
| 2 | cheap correlational / attribution screening narrows the internal object to candidates |
| 3 | intervening on a candidate moves the behavior — sign, magnitude, dose–response |
| 4 | matched controls, off-target checks, and confound checks rule out the mundane rivals |
| 5 *(optional)* | how far it holds — phrasing, position, model family, interpretability replication |

**Experiment 1 is a gate with four outcomes**, all spelled out: *established* (the plan proceeds), *conditional* (it holds only under some conditions, and later experiments are scoped to those), *not established* (the claim dies), *inconclusive* (the measurement itself failed and must be fixed and re-run, not adjudicated). Its pass criterion must cover reproducibility across paraphrase, seed, and decoding; controlled confounds; a sample size clear of noise; and the ruling out of trivial explanations.

Where a threshold is stated, say what it rests on — measured in a cited paper, or an estimate. Estimates are fine; estimates dressed as measurements are not.

**The rungs are planning vocabulary and never surface in `claim.json`.** «Phenomenon-validation», «localization», «specificity», «M0» are this workflow's names for its own scaffolding, and a reviewer holding only this file cannot decode them. Each experiment is headed instead by the hypothesis it tests and the finding it would produce — `Experiment 1 (H1 — Half-life):`, `Experiment 4 (H4 — Activation edit):` — and opens with a sentence saying what it does in the paper's own terms.

#### The undecidable band

Every threshold splits the outcome space into three regions rather than two — clearly supporting, clearly refuting, and the band between where the planned measurement cannot decide. Finite samples, measurement noise, and any equivalence margin guarantee that band exists for H2…Hk as well as for the gate.

So each hypothesis states its own, in the experiment that tests it: **where the band lies**, in the threshold's own units; **what a result there means**, said plainly — H*i* is not supported at the planned power, the effect too small to separate from noise at this sample size, or the measurement too coarse to separate the mechanism from its rivals — and not «a weak trend consistent with H*i*», not silence; and **what follows**, fixed before the data rather than after: H*i* reported as undecided, the pre-specified extension run if the plan budgets one, and the experiments depending on H*i* stopped, scoped, or run unchanged.

`Risk Factors and Limitations` adds only what the experiment cannot: where the plan's own power estimate says the band is likely to be entered, with what it would cost to narrow it.

#### Numerical consistency

Every quantity carrying a number — threshold, margin, sample size, item count, budget — is defined once and written identically everywhere: same name, same value, same unit. A bar introduced in `Short Hypothesis` is the bar the matching experiment enforces, the one `Ablations and controls` and `Metrics` report against, and the one any risk entry mentioning it uses.

Because the design is written once, consistency is a **within-file** property and strictly checkable: every number either appears once, or appears several times at the same value and unit. When two occurrences disagree, decide which is right and fix every occurrence — never soften a number in one field to match another, and never let a percent become a proportion or tokens become layers.

A quantity whose value depends on a submethod not yet chosen is still **one** number: commit to the value the plan assumes, and name the dependency in `Risk Factors and Limitations` as an open choice with its options.

#### From working notes to paper

`LANDSCAPE.md` holds the survey; `hypothesis_library.json` holds the pool, the scores, and the eliminations. **A reviewer sees `claim.json` and nothing else**, and the whole difficulty of this phase lives in that gap. Every piece of working material either dissolves into one of the seven fields or stays behind:

| what the run produces | where it lands |
|---|---|
| the phenomenon and its trigger (`statement`) | `Short Hypothesis` opening; restated once in `Abstract`, same direction and numbers |
| where the idea came from (`discovery_strategy_detail`) | `Abstract`'s opening motivation; a clause in `Related Work` when the source is citable |
| what is new even if the transfer succeeds (`innovation.beyond_transfer`) | `Abstract`'s what-it-establishes sentence; `Related Work`'s separation clause — the field that stops «X, but in Y» from being the whole claim |
| the non-standard design move (`innovation.method`, the method-innovation line) | `Experiments`, in the sentence introducing the instrument; one clause in `Abstract`'s design sentence |
| the early mechanism direction (`mechanism_opportunity`) | Phase 6 expands it; the internal object and causal relation land in `Short Hypothesis`, while its test and controls land in `Experiments` |
| the surprise and the scope (`five_bars`: `nonobvious`, `real`, `specific`) | `Abstract`, dissolved into prose, never as labelled bars |
| the structural gap; the three nearest works | `Related Work` — the gap restated as what the literature has not done, the works roughly a clause each |
| the mechanism — internal object, causal relation | `Short Hypothesis`, the H-list |
| the boring nulls | `Experiments`, where each one's control is introduced; `Risk Factors and Limitations` for any left unhandled |
| the expert's prior (checklist 2) | `Abstract` or `Related Work` — whichever sentence explains why the result would surprise |
| the consumer on each branch (checklist 3); the breaking case (checklist 4) | `Abstract`'s closing sentence; `Risk Factors and Limitations` as the stated scope bound |
| the ladder, gates, controls, models, data | `Experiments` |
| `five_bars`' `robust` and `tractable`; scores, ranks, ids, rung names, eliminated behaviors | nowhere — they justify *studying* the behavior or are batch bookkeeping, and say nothing to a reviewer |

**The routing must not show.** The table says *where*, not that a sentence must appear. A row is discharged when its content is *there* — usually inside a sentence written for another reason, often as a subordinate clause, sometimes two rows at once. The test runs backwards: **a reviewer must not be able to reconstruct this table from the prose.** Nothing announces its own function — no «our contribution is novel because», no «the expert prior is». Adding a dedicated sentence for a row makes the paper worse, and a paper that reads like a completed form does not survive review.

> **Routing showing through:** *The expert prior here is that retraction fully erases the claim, so our result is non-obvious. If the claim is true, deployers of retrieval-augmented systems will audit their corrections; if false, they will not.*
>
> **Absorbed:** *A retraction is normally assumed to do what it says: the claim is withdrawn, and what follows is computed without it. We find instead that the withdrawn claim keeps shaping downstream inferences long after the model has verbally accepted the correction — an assumption that every multi-turn and retrieval-augmented deployment currently relies on untested.*

**One register for the agent, another for the reviewer.** Every row is sourced from something written to be *processed* — a bulleted gap, a scored node, a reviewer's objection — not to be *read*. Carrying it across means rewriting it in the paper's register: keep the numbers, the direction, and the controls; drop the operational scaffolding; restore what an executor never needed and a reviewer cannot do without — what the measurement is *for*, and what it would show.

> **Executor-facing:** `M2: for l in [12,16,20] patch resid_post @ last_tok, α∈{0.5,1,2}, n=200/cond, log Δlogprob(P) vs C0; gate |Δ|>2σ_seed; fallback l=8 if OOM.`
>
> **Reviewer-facing:** *Experiment 3 (H3 — Causal confirmation): We patch the residual stream at layers 12, 16, and 20 at the final token of the retraction, sweeping the edit strength over three values on 200 items per condition, and measure the change in log-probability of the retracted claim relative to the no-mention baseline. If the localized component is causal rather than merely correlated, the effect should be negative, should grow monotonically with edit strength, and should exceed the cross-seed noise we measure in Experiment 1.*

**Nothing may point at a file the reviewer does not have.** No «the gap identified in `LANDSCAPE.md`», no «behavior B7», no bare «Gap 3», no reference to the other claims — each `claim.json` stands entirely alone. Where such material earns a place it is restated in full. Fail: any noun phrase whose referent lives only in another file.

#### Writing for the reviewer

- **`Short Hypothesis`, `Related Work`, and `Abstract` are continuous prose** — no bullets, no fragments, no telegraphic notation. Readable end to end by someone who has never seen this workflow.
- **`Experiments` is structured at the label level and prose everywhere below it.** A label is a signpost, not a license to stop writing sentences. Write «We fit an exponential decay of the probe-minus-baseline difference against washout distance and report a per-model half-life in tokens», not «fit: exp decay; x: washout; out: half-life (tok)». Only item 7 is a list.
- **Every sentence carries its own referents.** Name the condition rather than pointing at «C2», say what a step is *for*, expand an abbreviation the first time. A label may be introduced and reused — but it must be introduced *inside* `claim.json`, in the field where it is first used.
- **No placeholders ship.** No `TBD`, no `<…>`. An unknown is either resolved or named in `Risk Factors and Limitations` as an open choice with its options.
- **Name a work only if you can cite it.** Author and year, and a result you can state. A fabricated citation invalidates the whole skeleton.
- **Prefer the number to the quantifier.** «1,500 items across four domains» over «a large benchmark».

#### Write order

**`Short Hypothesis` → `Related Work` → `Abstract` → `Experiments` → `Risk Factors and Limitations`**, then `Title` and `Name`. This is the argument's own dependency order: `Short Hypothesis` fixes everything downstream; `Related Work` decides how much of the design must be *distinguishing* rather than merely sound; `Abstract` repackages the node against that positioning; only then does `Experiments` have nothing left to invent. Writing the design first inverts this — the plan starts generating hypotheses to justify the experiments it wanted to run.

Two consequences, both binding:

- **Numbers originate upstream and `Experiments` inherits them.** A threshold, margin, sample size, or item count is fixed the first time it is claimed, and `Experiments` enforces *that* value at *that* unit. When writing `Experiments` reveals a number was wrong, fix it at every occurrence including the upstream one; never let `Experiments` quietly carry a second value.
- **The ladder is still a gate, just a later one.** Once the ladder is written, re-read `Short Hypothesis` against it. If some H has no rung that could falsify it, or Experiment 1 cannot kill the claim, or a rung had to invent a condition `Short Hypothesis` never mentioned, then the hypothesis was not ready — and it is `Short Hypothesis` that gets rewritten, not the ladder that gets bent to fit it.

#### Quality checklist

Run this on **each** `claim.json` before shipping. Each item is a **check that can fail on a fact**, never a quality the author can assert. What these checks turn up is content: each finding has a field waiting for it in the routing table and is written there as part of the argument, never as a self-assessment.

*Is the idea new*

1. **Three nearest works, each separated at the level of a finding.** For each, state the specific result it established and what this claim contradicts, extends past its scope, or looks at where it never looked. Fail: fewer than three can be named, or any separator is merely topical — and **a separator naming only a different domain, modality, objective, or model scale is incomplete unless it states the context-specific constraint, failure mode, measurement, capability, or decision that the transfer reveals**. The node committed to a `beyond_transfer`; if no separation clause carries it, either the claim drifted off its delta or the delta was never real. If genuinely nothing is close, decide which case it is — nobody asked the question, or nobody has a use for the answer — and if the second, the claim changes.
2. **The expert's prior is written down before the plan is.** State the direction and boundary a researcher in this area would predict for the key measurement without having read this claim. If it matches the claim's own prediction, the direction is not what is new — identify the precise boundary, interaction, or consequence that would still surprise the expert, and check that the experiment measures *that*. Fail: no experiment distinguishes the claim from the expert's prior.

*Would it matter*

3. **Both branches have a named consumer.** Who does something differently if the claim comes out true, and separately if false — a specific decision tied to an important problem, not «the community would understand this better». Fail: either branch is empty or the only consequence is intellectual interest.
4. **The stakes survive stripping the setting, and the scope has an edge.** Re-read with the high-stakes setting swapped for a neutral one. If the contribution evaporates, the contribution was the framing — either drop it or make the setting do real work, with the mechanism turning on something particular to that domain rather than on its stakes. Then name one concrete setting where the conclusion should **break**. Fail: the contribution is carried by the setting, or no breaking case can be named.

*Can it be settled*

5. **Experiment 1 can kill the claim.** Assume it returns *not established*: does `Short Hypothesis` die with it? If the claim could survive by reinterpreting the outcome as a measurement problem, the gate is hung on the wrong object — re-hang it. (*Inconclusive* is the branch for a broken measurement; it must not become a hiding place.)
6. **Every mundane explanation is paired with a control.** Match each boring null one-to-one against the controls. Any account with no control either gets one or moves into `Risk Factors and Limitations` as explicitly not ruled out. Listing a rival and then ignoring it is a fail.
7. **Every hypothesis has its undecidable band written out.** For each of H1…Hk, point to where the file says how wide the band is, that a result inside it leaves H*i* unsupported at the planned power, and what the dependent experiments do then. Fail: a prediction with only two outcomes; a band with no stated consequence; a non-significant result read as evidence for a null without an equivalence margin.
8. **Every number agrees with itself.** List every numeric quantity and check each occurrence against the others, comparing value *and* unit. Fail: one quantity holding two values; a bar set in `Short Hypothesis` that a later experiment does not enforce at that value; a threshold in `Metrics` that no experiment predicts against. Repair every occurrence; never drop the number instead.
9. **The design does something the standard recipe does not, and the paper says what it buys.** Point to the sentence in `Experiments` introducing the adapted instrument, imported paradigm, rescue arm, newly-defined unit, or measurement taken where nobody measures — and to the clause saying what it makes measurable that the default design could not. Fail: `Experiments` could be transplanted onto a different phenomenon by changing the nouns; or the node's `innovation.method` named a move no experiment implements. The permitted exception is the case the node declared — a standard design whose delta is carried entirely by the claim — and then item 1's separation must be doing all the work, visibly.

10. **Every dependency exists, and the cost is in figures.** Point to the models, datasets, and method implementations the plan relies on and confirm each is real today or that the plan says how to build it; then point to the `Resources` paragraph and check it carries numbers — GPU-hours, runs, items per condition, annotator-hours — rather than «large-scale» and «several». Fail: a step nobody knows how to implement; an artifact that does not exist with no construction plan; or a resource description with no figures in it. Not a fail: an expensive plan.

**Every failure is repaired in place, not noted.** If a failure cannot be repaired without changing the claim, switch the mechanism direction and rewrite. After two such restarts on the same behavior, stop working it, set `status: "blocked"` with what is blocking it, and promote the highest-ranked eliminated behavior into the vacated slot rather than shipping a weak skeleton.

**Batch independence.** The `TOP_N` claims are checked separately and must not converge: if two end up with the same phenomenon, the same H-list, or the same Experiment 1, one was never a distinct behavior — rewrite it onto its own phenomenon or replace it from the ranked list.

#### Closing pass

Read each draft **as if it were the only file that exists**: repair every referent that resolves only elsewhere, rewrite every sentence still addressed to the agent that will run it, and cut every sentence whose only job is to satisfy a row of the routing table. `claim.json` is **always English**, regardless of the language used elsewhere.

**This is the end of the workflow.** Once all `TOP_N` claim files are on disk, stop. Do not implement, launch, or queue any experiment, and do not chain into another skill.

## Output Protocols

> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — `hypothesis_library.json` is a living document updated in place (not timestamped).
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log `hypothesis_library.json` to MANIFEST.md on first creation.
> - **[Output Language Protocol](../shared-references/output-language.md)** — machine fields (ids, `pass`, `status`, strategy names, scores, `recommendation`, dates) stay English; free-text fields follow the project language. `claim.json` and `topic.md` are **always English** regardless — both are read by the evaluators.

## Review Tracing

Save a trace per `shared-references/review-tracing.md` to `.mechanist/traces/hypothesis-batch/<date>_run<NN>/` for every `mcp__llm-chat__chat` call — dedup, the delta repair pass, impact scoring, every final claim judge, and (when `WRITER = llm-chat`) every draft and revision pass. With `ROUNDS > 1`, put generation traces in an `r<NN>/` subfolder. Claim-writing passes are per claim: store the initial draft evaluation under `claims/<NN>_<name>/eval-p1/`, the revised-draft evaluation under `eval-p2/`, and the writer revision beside them in the claim trace directory.

## Key Rules

- **Never block on the user.** Run start to finish without waiting for input — the one exception is the cross-topic guard.
- **One model conceives and writes; another judges.** `WRITER` (session by default) authors both `hypothesis_library.json` and every `claim.json`, and never splits across phases. Every evaluation step runs on `REVIEWER_BACKEND` = `llm-chat` — routing dedup, scoring, the novelty gate, or the review through the writer collapses the pipeline into one model agreeing with itself. The orchestrator verifies rather than authors.
- **The library is behavior-first.** It stores one lightweight `mechanism_opportunity`, not a full mechanism axis. Phase 6 instantiates the falsifiable mechanism for `TOP_N` survivors only; the expanded form lives in claim context.
- **Run-level context runs once.** Invoke `/research-lit` once and full-load both strategy skills once before round 1. Reuse the resulting landscape and strategy context for all normal and top-up rounds. No per-round literature refresh and no refresh parameter exist.
- **Rounds accumulate, never repeat.** Persist at the end of every round and rebuild the next banlist from it. A round adding 0 survivors means saturation — stop and say so; never pad.
- **Semantic dedup, not string match.** Two behaviors are the same when they name the same phenomenon under the same trigger, whatever the wording. Template collapse counts as duplication.
- **Novelty is not a single template.** `beyond_transfer` records what the candidate adds beyond its source or nearest work: this may be a quantity, boundary, prediction, condition, context, or use. A new domain, modality, objective, or scale can be the contribution; state the intended angle when it is known.
- **Impact is not a method-only label.** Record why the behavior may matter and what could follow from the result, without forcing every candidate into the same audience or decision template.
- **Final evaluation is dimension-isolated.** Novelty, impact, clarity, and feasibility keep their official meanings and separate scores. The initial draft is judged, revised once from the written justifications, and judged again; no weighted total and no open-ended critique loop.
- **The method is part of the claim.** `innovation.method` → Phase 6 makes good on it or supersedes it → `Experiments` implements it. A design transplantable onto another phenomenon by changing the nouns is a control condition, not a contribution.
- **Never reuse ids; never delete a node.** Growth is append-only and eliminations stay with their reason, so the library is a stable, citable backlog.
- **Every node is self-contained.** The library outlives the run, and `LANDSCAPE.md` is regenerable scratch. Read any node cold, with no other file open, and it must still say what it means.
- **Score everything.** No behavior is persisted without `impact`; none enters Phase 5 without `novelty` and `review`.
- **Step 2 is parallel; Step 3 is serial.** Phases 3 and 4 are read-only fan-out. Claims are worked one at a time in rank order, each closed before the next opens.
- **`claim.json` is the product; everything else is scaffolding.** A beautiful library with `TOP_N` thin claim files is a failed run. Depth per claim beats size of the pool.
- **One design, written once.** The experiment design lives in `Experiments` and nowhere else.
- **One quantity, one number.** A threshold, margin, sample size, or budget holds a single value and unit everywhere it appears; disagreement is repaired at every occurrence.
- **Feasibility is executability; cost is not a defect.** A plan fails on a magic step, a missing artifact, or an absent control — never on GPU-hours, annotation volume, or gated access. State the resource figures; never shrink the claim to make them small.
- **Clarity is a check that can fail, not a matter of style.** Any threshold without a stated basis, equivalence claim without a margin, or prediction without a direction fails.
- **Report the undecidable band.** Reporting only pass/fail hides it, it does not remove it.
- **Large file handling:** if Write fails on size, retry via Bash heredoc silently.

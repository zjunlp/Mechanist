---
name: hypothesis-batch
description: "Three-step batch pipeline for research hypotheses. The positional argument is the user's whole INPUT INTENTION (direction + whatever angle, constraint, or wanted result they attached) — there is no separate topic argument and no intention flag; the topic label is distilled from it. (1) mass-generate a deduplicated, impact-scored library of candidate BEHAVIORS into `hypothesis_library.json` over `ROUNDS` accumulating rounds of `N_BEHAVIORS` each — every round generating twice, first cold (no discovery-strategy taxonomy in the prompt) and then strategy-guided, with each behavior required to state what is new beyond the domain it was transferred into; (2) evaluate the pool — novelty hard gate + external critical review — and select the top `TOP_N`; (3) attach a mechanism hypothesis to each survivor and write one reviewer-facing `claim.json` per claim — the experiment design included, as its `Experiments` field, with no separate plan file. The library holds behaviors only — no mechanism axis. A single `WRITER` setting picks which model authors both deliverables: `llm-chat` (the external `LLM_MODEL`) or `session` (the current Claude session). Use when the user wants a batch of paper-ready claim skeletons for one research direction."
argument-hint: "<intention — what you want out of this topic> [— n-behaviors: N] [— rounds: R] [— top-n: K] [— cold-n: N] [— writer: llm-chat|session]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__llm-chat__chat
---

# Workflow: Hypothesis Library → Selection → Claim Skeletons

Orchestrate the claim stage for: **$ARGUMENTS**.

## Overview

This skill runs three steps, non-interactively, end to end:

```
Step 1  BUILD    /research-lit  →  load behavior strategy  →  ROUNDS × round-loop      → hypothesis_library.json
                 (P1: retrieval)   (P1.5: no artifact,        (P2: cold pass → guided pass
                  ↳ RESEARCH_LIT.md   taxonomy withheld            → semantic dedup + delta
                  ↳ LANDSCAPE.md ──── from the cold pass)            filter → impact score
                        └──────────── grounds every round ──→        → persist)

Step 2  SELECT   /novelty-check (P3: hard gate) → /research-review (P4: veto + score)   → verdicts written
                 → rank impact ▸ reviewer ▸ novelty, cut to TOP_N (P5)                     back into the library

Step 3  PLAN     load mechanism strategy → attach mechanism (P6) → draft + refine          → claims/<NN>_<name>/
                 claim.json (P7), one claim at a time                                        claim.json, nothing else
```

**One deliverable per claim.** Step 3 writes `claim.json` and nothing beside it. The experiment design *is* the `Experiments` field — there is no separate `EXPERIMENT_PLAN.md` and no `FINAL_PROPOSAL.md` to keep in sync with it. A plan written twice, once for an executor and once for a reviewer, is the same design maintained in two places at two levels of detail; this workflow ships the reviewer's version and stops. `WRITER` authors it, and the same `WRITER` authored the library it came from, so consistency is intra-file and intra-model rather than a cross-file, cross-model reconciliation.

**Retrieval bounds the whole run.** Step 1 opens with `/research-lit` — Zotero, Obsidian, local PDFs, the web, and the cloud mechanic-db — and everything downstream is grounded on what it finds. `LANDSCAPE.md` is the carrier: round 1 aims one behavior at each structural gap it names, every later round reads it again for grounding, and the gaps it grounded land in each behavior's `gaps` field. Step 2 then retrieves a *second* time, per candidate, inside `/novelty-check`. 

**Batch shape: `ROUNDS × N_BEHAVIORS` in, `TOP_N` out.** Step 1 accumulates a library of candidate **behaviors** — phenomena only, no mechanism axis — each scored for impact. Step 2 applies novelty as a hard gate, has an external reviewer veto fatal design flaws, and cuts to `TOP_N` by ranking impact first, reviewer score second, novelty last. From Step 3 on, each survivor is worked **independently and one at a time**, in rank order, and gets its own mechanism hypothesis and its own directory.

**Deliverables.**

```
hypothesis_library.json      # ⭐ Step 1's pool; Step 2 writes its verdicts and ranks back into it
idea-stage/
  RESEARCH_LIT.md            # raw retrieval dump (audit-only)
  LANDSCAPE.md               # synthesized landscape
claims/
  01_<name>/                 # one directory per selected behavior, rank-ordered
    claim.json               # ⭐ the deliverable a human reviewer reads — the only file here
  02_<name>/
    …
  <TOP_N>_<name>/
```

The run ships exactly **two kinds of file**, and one model writes both: `hypothesis_library.json` — the run's canonical record, holding the pool, the scores, the eliminations and the ranks — and `TOP_N` × `claim.json`, each a self-contained paper skeleton written **for a human expert reviewer** who sees that file and nothing else. `LANDSCAPE.md` and `RESEARCH_LIT.md` are retrieval working material. The `claim.json` specification is Phase 7 and is binding.

## Constants

- **INTENTION** — **the positional argument itself**: everything the user typed before the first ` — `. There is no `— intention:` flag. It is free text stating what the user is actually after — the direction, and whatever angle, constraint, application, or kind of result they attached to it (`"LLM beliefs"` and `"LLM beliefs — I care about whether a retracted claim keeps steering later inferences, and I want something a single 8B model can settle"` are both valid, and the second one steers much harder). Injected verbatim into **every** brainstorm round's prompt (Phase 2), into the impact rationale, into the selection judgment (Phase 5), and into every `claim.json` draft and refinement prompt (Phase 7) — a candidate that ignores the stated intention ranks below one that serves it, at equal scores. Required: if it is empty, ask for it in one line and never invent one. Stored at the library's top level as `intention` so later rounds and re-runs inherit it.
- **TOPIC** — **derived from `INTENTION`, not passed separately.** Distil a short noun-phrase label naming the research direction (drop the angle, the constraint, and the wanted result — those live in `INTENTION`), plus a lowercase kebab-case `topic_slug`. Used only for library identity: the cross-topic guard, the `topic` field, and record-keeping. Generation and ranking read `INTENTION`, never `TOPIC`.
- **N_BEHAVIORS = 10** — target count of *new* behaviors to add **per round**. Override with `— n-behaviors: N`.
- **COLD_N = `max(1, round(N_BEHAVIORS / 5))`** — how many of each round's behaviors come from the **cold pass**: generated *before* the discovery-strategy taxonomy is shown, with no strategy vocabulary in the prompt at all. The remaining `N_BEHAVIORS − COLD_N` come from the strategy-guided pass. Override with `— cold-n: N`; `0` disables the cold pass (not recommended — it is the only part of the round that is not shaped by a checklist). At the default `N_BEHAVIORS = 10` this is 2 cold + 8 guided per round. The cold pass exists because a taxonomy read immediately before generating **anchors** the generation: every candidate arrives pre-shaped to fit a named lens, and the lenses' own blind spot becomes the round's blind spot. Cold candidates are the round's only chance to name something no lens would have asked for. They are held to exactly the same bars and the same dedup as guided ones — the pass is unprimed, not unfiltered.
- **ROUNDS = 3** — number of consecutive generation rounds in this invocation. Each round runs the full **generate → dedup → impact → persist** cycle and writes `hypothesis_library.json` **before the next round starts**, so the library accumulates. Every round rebuilds its banlist from the just-updated library, so earlier rounds' behaviors are **never** regenerated. Override with `— rounds: R`. Default `3 × 10` targets a pool of ~30. The loop self-terminates early if a round adds nothing after dedup (topic saturated — report it).
- **TOP_N = 10** — how many behaviors survive Phase 5 and get their own `claim.json`. Override with `— top-n: K`. Fixes the directory numbering (`01`…`<TOP_N>`).
- **IMPACT_WEB = true** — when true, run one quick web/arXiv search per surviving behavior to ground its impact score. Set `false` for a pure-LLM estimate (faster, may miss recent work).
- **REVIEWER_BACKEND = `llm-chat`** — external LLM via llm-chat MCP for generation, semantic dedup, and impact scoring (model defers to `LLM_MODEL`). Each sub-skill (`/research-lit`, `/novelty-check`, `/research-review`) declares the same default independently — this constant is not forwarded.
- **WRITER = `llm-chat`** — **the single model that authors both of this run's deliverables**: the behaviors in `hypothesis_library.json` (Phase 2) and every `claim.json` (Phase 7). Two values, set with `— writer:`:
  - **`llm-chat`** (default) — the external model via `mcp__llm-chat__chat`, resolved from `LLM_MODEL` (e.g. `gpt-5.6-luna`). Brings a set of priors different from the orchestrator's, which is what makes the brainstorm diverge.
  - **`session`** — the current session model (Claude). No MCP hop, full file access, no context-assembly cost.

  **One model for both ends, always.** The model that conceived a phenomenon is the model that writes it up, so the framing, the emphasis, and the sense of what is surprising carry through instead of being re-derived by a second reader. Never split the setting across phases: if Phase 2 and Phase 7 ran on different models, the run is inconsistent and the `claim.json` files must be redrafted. Everything *else* stays where it is — `REVIEWER_BACKEND` still governs review, dedup, and scoring, and the orchestrating agent always owns verification (schema, checklist, repairs) regardless of `WRITER`.
- **LIBRARY_FILE = `hypothesis_library.json`** — the single canonical pool file, at project root. One topic per file; created on first run.
- **OUTPUT_DIR = `idea-stage/`** — where `/research-lit`'s two files land.

### Argument parsing

`$ARGUMENTS` is shaped as `"<intention>" — <key>: <value>, <key>: <value>, ...`.

1. **`INTENTION` (positional, required)** — everything before the first ` — ` (em dash with spaces) or `--`, taken verbatim, punctuation and all. This is the whole user input intention; there is no separate topic argument and no `— intention:` flag. If it is empty, ask for it in one line; never invent one.
2. **`TOPIC` / `topic_slug`** — distilled from `INTENTION` (see Constants), never parsed from the argument list.
3. **Options (after ` — ` or `--`)** — comma-separated `key: value` pairs; whitespace around `:` and `,` is ignored. Canonical keys are hyphen-separated and lowercase (`n-behaviors`, `rounds`, `top-n`, `cold-n`, `writer`); underscore (`n_behaviors`) and env-style (`TOP_N`) are accepted. `n-behaviors` / `rounds` / `top-n` must parse as positive integers, and `cold-n` as a non-negative integer no larger than `n-behaviors`; anything else is a parse error — log `[arg-parse] <key>: "<value>" is not a positive integer` and stop. `writer` accepts `llm-chat` / `session` (case-insensitive); on any other value log `[arg-parse] writer: "<value>" not in {llm-chat, session} — falling back to default 'llm-chat'` and continue with the default. Unknown keys log `[arg-parse] unknown key: <name> — ignoring` and continue. A passed `— intention:` is an unknown key: it is ignored with that log line, because the intention is the positional.

**Beware the em dash.** `INTENTION` is free text and may itself contain an em dash. Only ` — ` immediately followed by a `<key>: <value>` pair opens the option list; an em dash followed by ordinary prose is part of the intention. When ambiguous, prefer the longer intention and log `[arg-parse] treated "— <text>" as part of the intention`.

## Example run

> Illustrative — the behaviors and numbers below show the *shape* of a run, not real generated output.

**Invocation**

```
/hypothesis-batch "Extend research on subliminal learning. You can find the definition of
subliminal learning in this paper: Subliminal Learning: Language models transmit behavioral
traits via hidden signals in data" — rounds: 10, n-behaviors: 10
```

**Parse**

| | |
|---|---|
| `INTENTION` | `Extend research on subliminal learning. … hidden signals in data` — verbatim, the two internal colons are prose, not keys |
| options | `ROUNDS = 10`, `N_BEHAVIORS = 10` |
| defaults | `TOP_N = 10`, `COLD_N = 2` (from `N_BEHAVIORS / 5`), `IMPACT_WEB = true` |
| `TOPIC` / `topic_slug` | `subliminal learning in language models` / `subliminal-learning` |
| shape | ~100 candidates in → 10 claims out |

The `—` before `rounds:` is followed by a `key: value` pair, so it opens the option list. The `—`-free colons inside the paper title stay in the intention. `INTENTION` names a specific reference paper, so `/research-lit` retrieves around it and every round is held to *extending* that result rather than restating it.

`— top-n:` is not passed here, so `TOP_N` falls to its default of 10 — that is the `10` in "87 candidates → top 10". **Pool size and batch size are independent knobs**, and they price differently: `rounds × n-behaviors` sets how wide Step 1 searches and how many candidates Step 2 must score, while `top-n` alone sets Step 3's cost — one drafting pass plus up to 5 refinement rounds per selected behavior. Appending `— top-n: 20` to the invocation above changes nothing before Phase 5; it just takes 20 of the 57 survivors instead of 10, doubling Step 3 and creating `claims/01_…` through `claims/20_…`. Widen the pool to search harder; raise `top-n` only when you actually intend to read that many skeletons.

**Step 1** — `/research-lit` writes `LANDSCAPE.md`; then 10 rounds, each pasting the accumulated banlist and one slice of the search space (r1 = the landscape's structural gaps, r2 = unused discovery strategies, r3+ = derived from what the library under-covers, on both the phenomena-class and the innovation-move axis). Each round: **2 cold** (no taxonomy in the prompt) → **8 guided** → semantic dedup and delta filter → impact score → persist. A representative node:

```
B23  cross-modal transfer · guided
     "A student finetuned only on a teacher's numeric outputs acquires the teacher's
      trait, but the transfer collapses once teacher and student tokenizers differ,
      even at identical initialization. The carrier account predicts the opposite —
      the signal lives in the choice among equally valid outputs, which survives
      re-encoding — so tokenizer identity should be irrelevant and it is not."
     innovation: beyond_transfer — "converts an all-or-none same-base rule into a
                 measured boundary: the vocabulary-overlap fraction at which transfer
                 halves"; method — "re-tokenizes one fixed corpus under six vocabularies
                 to vary the channel while holding the data constant, which the standard
                 teacher-swap design cannot do"
     five_bars: real/nonobvious/specific/robust/tractable — one line each
     impact: 8 · PROCEED · "bounds when data filtering is a real defense; distillation
             pipelines would need to check tokenizer identity, not just content"
```

Say rounds 8–10 return 3, 1, and 0 new behaviors after dedup: the loop stops early at round 10 with **87 candidates**, and the report says so.

**Step 2** — 87 `/novelty-check` calls: 19 eliminated as already reported (`status: eliminated`, kept in the file). 68 `/research-review` calls: 11 vetoed for fatal design flaws. The remaining 57 rank by impact → reviewer → novelty, with `INTENTION` breaking ties; the top 10 are taken, then two low-ranked duplicates of the "trait transfer survives filtering" class are swapped out for distinct phenomena.

**Step 3** — the 10 are worked **one at a time in rank order**, claim `01` closed before `02` opens. Each gets a mechanism hypothesis (internal object + causal relation + boring null), then one `claim.json` drafted by `WRITER` and refined against `REVIEWER_BACKEND` for up to 5 rounds — the experiment design included, as the `Experiments` field.

**On disk**

```
hypothesis_library.json          87 behaviors: 10 selected, 30 eliminated, 47 ranked-out
idea-stage/
  RESEARCH_LIT.md
  LANDSCAPE.md
claims/
  01_tokenizer_bound_trait_transfer/
    claim.json
  02_…/  …  10_…/
```

**Cost.** `rounds: 10` is a deliberately large pool, and Step 2 spends one `/novelty-check` **and** one `/research-review` per surviving candidate — here ~155 external reviewer calls, dwarfing Step 1's 20 brainstorm calls (two per round, cold and guided) plus the occasional delta-filter repair. Lower `rounds` for a cheaper pass; the library accumulates across invocations, so several small runs and one large run reach the same place.

## Step 1 — Build the hypothesis library

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape:

```
/research-lit "<INTENTION>"
```

Pass `INTENTION` verbatim — the whole positional argument, not `$ARGUMENTS` (which still carries the option list) and not the distilled `TOPIC`. The angle and constraint in the intention are exactly what should aim the retrieval.

**What this does:**
- Search Zotero, Obsidian, local PDFs, the web, and the cloud mechanic-db SEARCH service (via the skill `/mechanic-db-search`) for relevant papers
- Build a landscape map: sub-directions, approaches, open problems
- Identify structural gaps and recurring limitations
- Output two files: `idea-stage/RESEARCH_LIT.md` (raw retrieval dump, audit-only) and `idea-stage/LANDSCAPE.md` (synthesized landscape — Phase 2 reads this from disk)

### Phase 1.5: Behavior-Discovery Strategy Load

This phase loads strategy into context; it writes **no artifact**. Invoke `/mechanism-behavior-discovery` and read its `SKILL.md` in full — the standard for finding, sharpening, and validating a *new* behavioral phenomenon: the five bars **Real / Non-obvious / Specific / Robust / Tractable**, the discovery strategies, the **innovation moves** and the novelty delta they exist to produce, and the validation discipline. It decides *what behavior is worth explaining*. Read it, do not execute its phases, and do not expect an output file. Log `[behavior-strategy] loaded /mechanism-behavior-discovery`.

Hold the loaded guidance in context for Step 1 — do **not** copy it into any output file. The mechanism strategy is **not** loaded here; it belongs to Step 3 (Phase 6), because the library carries no mechanism axis.

**Two halves, loaded for two different moments.** What this skill supplies splits cleanly, and the round loop uses the halves at different times:

- **The bars and the innovation moves are always on.** The five bars, the novelty-delta test, and the three statement failure modes apply to every behavior in every pass, cold or guided. They are *filters on what counts as a candidate*, and a filter cannot anchor generation because it runs after it.
- **The discovery-strategy taxonomy is withheld from the cold pass.** The six named lenses, their numbering, and their vocabulary are generation *scaffolding*, and scaffolding placed before the first idea decides which ideas are reachable. They enter at Round step 2b and never at 2a. This quarantine is what `COLD_N` buys; loading the taxonomy here and then pasting it into every prompt would spend the budget and get nothing.

What the loaded strategy is used for (advisory — it never relaxes the novelty or feasibility filtering downstream): surface and *sharpen* candidate phenomena, stating each crisply against the five bars, and screen plausibility. A library entry **assumes** its phenomenon exists; its actual existence is settled only by running the claim's Experiment 1, which is downstream of this workflow — never asserted here.

### Phase 2: The round loop — generate, dedup, score, persist

This phase writes `hypothesis_library.json`. It runs the following cycle once per round, `round = 1..ROUNDS`.

**Library setup (once, before round 1).** Distil `TOPIC` and `topic_slug` from `INTENTION` first. If `hypothesis_library.json` exists, read it as the current pool. **Cross-topic guard:** if its `topic` differs semantically from this run's `TOPIC`, **halt and ask** (rename/move the old file, or confirm overwrite) — never silently overwrite another topic's library. A *different intention on the same topic* is **not** a cross-topic conflict: keep accumulating into the same library, overwrite the top-level `intention` with this run's, and note the shift in the Phase 5 report — the banlist still applies, so a re-run under a sharper intention mines new behaviors rather than regenerating old ones. Otherwise start an empty pool `{topic, topic_slug, intention, created, updated, behaviors: []}`.

**Round step 1 — Rebuild the banlist.** Re-read `hypothesis_library.json` (it grew in the previous round's persist step) and collect **all** behavior statements currently in it — including those added by earlier rounds of this same invocation, and including eliminated ones. The llm-chat model is stateless, so the prompt MUST paste this banlist verbatim and require outputs that are neither in it nor close variants of it.

**Round step 2 — Brainstorm.** Every round brainstorms in **two passes, in this order and never merged into one call**: a cold pass that runs before the discovery-strategy taxonomy is shown, then a guided pass that uses it. Both passes return the same fields (below) and both are held to the same bars; they differ only in what their prompt contains.

**Round step 2a — The cold pass (`COLD_N` behaviors).** One `WRITER` call whose prompt carries **only**: `INTENTION` verbatim, the `LANDSCAPE.md` gaps and open problems, the banlist, this round's slice, and the field spec. It carries **no** discovery-strategy list, no strategy names, no lens numbering, and no instruction to cover a taxonomy — and it says so explicitly, so the model does not reconstruct one from memory: *do not organize the output by any taxonomy of research strategies; propose whatever you would propose if none existed.*

Ask instead for the thing a lens cannot ask for: **what is actually strange, unexplained, or quietly assumed in this area** — the observation that does not fit, the assumption everyone is standing on, the question a practitioner in this field would ask that a researcher would not, the result that would be most annoying to whoever currently believes the standard account. One useful framing for this pass: *if you had to bet on one thing here being wrong, what would it be?*

`discovery_strategy` for a cold-pass behavior is set to `"cold-pass"` and stays that way — **never back-fill it with the lens it happens to resemble**. That relabelling is exactly the information the cold pass exists to preserve, and losing it makes round ≥ 3's coverage analysis (which reads the strategy distribution) blind to how much of the pool came from unprimed generation. Its `discovery_strategy_detail` still has to be written and still has to name a concrete provenance — a cold behavior is unprimed, not unmotivated.

**Round step 2b — The guided pass (`N_BEHAVIORS − COLD_N` behaviors).** One `WRITER` call, now with the full `/mechanism-behavior-discovery` apparatus in the prompt: the discovery strategies (spanning the lenses within this one call — do not hardcode a strategy count; use whatever set that skill currently specifies) and the **innovation moves**. The cold pass's outputs are appended to this prompt's banlist, so the guided pass cannot re-derive what the cold pass already found and is pushed into the space the cold pass left.

**Both passes, every behavior, these fields:**

- `statement` — the phenomenon, its triggering condition, and its novelty delta, written to the discipline in *Writing a `statement`* below. This is the field the whole library is judged on;
- `discovery_strategy` — which lens produced it, as a **bare human-readable name** (`cross-modal transfer`, `borrow from human sciences`, `cold-pass`). Never a numbered label copied out of the skill file — `"4 reuse-existing-CS-results"` leaks this workflow's scaffolding into a node that has to survive on its own;
- `discovery_strategy_detail` — one to two sentences of concrete provenance: which cross-discipline finding or method was borrowed and mapped onto what, or which past CS result was reused in which new setting. Provenance, **not** an experiment sketch: how the conjecture was *reached*, not how it would be run. A `detail` field that reads like a Methods paragraph means the behavior was written backwards from a protocol, and the statement almost always shows it;
- `innovation` — `beyond_transfer` and `method`, per *The novelty delta is a field, not a hope* below;
- `five_bars` — a one-liner for each of Real / Non-obvious / Specific / Robust / Tractable;
- `gaps` — the `LANDSCAPE.md` structural gaps it is grounded on, when it is; `[]` when it is not. **Each entry carries both the id and the gap restated in one self-contained line** — `{"id": "G2", "gap": "whether two traits held by one teacher transmit independently or compete for a shared carrier"}`, never the bare `"G2"`. The id is the join key back into `LANDSCAPE.md` (round 1's one-behavior-per-gap coverage check reads it, and so does the Phase 5 report); the restated line is what makes the node survive without it.

**Assign each round a different slice of the search space**, so the rounds diverge by construction rather than by luck. The slice is given to **both** passes — it bounds *where* to look, which is not the same as prescribing *how*, so it does not compromise the cold pass:

| Round | Assignment |
|---|---|
| 1 | The landscape's **structural gaps** — one behavior aimed at each gap `LANDSCAPE.md` names. |
| 2 | The **discovery strategies not yet used** in round 1. |
| ≥ 3 | The **phenomena classes underrepresented** after the previous rounds — read the accumulated library, name what kind of behavior is missing, and aim this round there. |

For round ≥ 3, run the coverage read along **two** axes, not one, and name the under-covered cell of each: the phenomena classes (what kind of behavior), and the **innovation moves** (which of `/mechanism-behavior-discovery`'s moves the pool's novelty deltas actually rest on). A library where every delta is "new domain" or "new trait" is under-covered on the second axis even when the first looks healthy, and that is the failure the round should be aimed at — a pool of transfers is not a pool of ideas.

Rounds from 3 on are written **after** reading the library, so their assignment is derived, not guessed. **Every round's prompt carries `INTENTION` verbatim, and every behavior must be answerable to it** — the round assignment slices the search space, the intention constrains what counts as a hit inside that slice. A behavior that would be excellent for the topic but does not serve the stated intention is a miss; say so in one line rather than generating it.

**Spread the altitude.** Per `/mechanism-behavior-discovery`, a candidate may be a broad regularity in how the model reasons or a narrow effect tightly scoped to one input→output pattern — both are good. Aim for a spread across the pool rather than a monoculture of tiny effects.

#### Writing a `statement`

`statement` is the node's load-bearing sentence and the only one most readers of the library ever process. Phase 3 runs its novelty search against it, Phase 4 reviews it, Phase 5 ranks on it, and Phase 7 repackages it into `Short Hypothesis` and the Abstract's design sentence. **A statement that reads like a sentence from the anchor paper's abstract will be scored as that paper** — the novelty check finds the source, and the node dies at the gate having never been given a chance to say what was actually new about it.

The failure is not carelessness; it is the path of least resistance. `INTENTION` names a reference result, the reference result has a canonical phrasing, and the fastest way to write a falsifiable sentence in that area is to take the canonical phrasing and change one slot — the objective, the trait, the modality, the domain. The pool then reads as one paper's result inflected `ROUNDS × N_BEHAVIORS` ways.

**Three tests, run on every statement before it is persisted.** Each fails on a fact, not on taste:

1. **Source-paraphrase test.** Put the statement next to the anchor paper's own claim. If it can be obtained by substituting nouns — a different trait, a different training objective, a different modality, a different model size — the statement is the source result with a slot filled and is not yet a behavior of its own.
2. **Sibling-swap test.** Put the statement next to the other behaviors of the same round. If one can be produced from another by editing a single noun phrase, they are one phenomenon with several instantiations, and the library should hold the phenomenon, not the list.
3. **Setup-to-claim ratio.** Count the clause carrying the *setting inherited from the source* against the clause carrying *what this node predicts*. If the setup is the longer half, the node is mostly a restatement of where it came from. Cut the setup to what is needed for falsifiability and spend the sentence on the prediction.

**What a statement must contain**, in whatever order reads best:

- **The triggering condition** — what has to be true for the phenomenon to appear, and, where it is what makes the claim sharp, the condition under which it should *not* appear.
- **The phenomenon** — a falsifiable regularity in observable behavior, with a direction, and with the quantity it is measured in named.
- **The delta clause** — what the standing account predicts *instead*, and what this node predicts against it. This is where `discovery_strategy_detail`'s content lands. The provenance does not stay parked in its own field waiting for Phase 7 to find it: **the borrowed idea's content is written into the statement as the reason the prediction has the shape it does**, while the fact that it was borrowed — the strategy name, the lens, the discipline it came from as a label — stays out. `discovery_strategy_detail` keeps the provenance for the *record*; the statement keeps its *consequence*.

**Register.** No taxonomy vocabulary («cross-domain transfer», «this behavior is tractable»), no account of the search («we borrowed from», «this strategy suggests»), no reference to the library, the round, or another node. Two to three sentences is the working range: one is usually too few to carry a delta clause, and past three the node has become a plan. Numbers beat quantifiers wherever a number can be committed to.

> **Slot-filled** — the anchor result with the objective swapped, setup longer than claim, no delta: *A student's DPO training on teacher-generated preference pairs about semantically neutral content will acquire the teacher's trait when the chosen and rejected responses differ only in latent trait expression and the teacher and student share a base initialization.*
>
> **Carrying its delta** — the same starting point, with the provenance absorbed and a prediction that competes: *Preference optimization should destroy a hidden trait channel rather than carry it: its gradient is a contrast between two responses, so any signal shared by the chosen and the rejected one cancels before it reaches the weights. We predict the opposite, and predict it to behave differently in kind — trait transfer under preference training survives, but its strength tracks the within-pair asymmetry of the carrier rather than the size of the corpus, so the standard hygiene of raising pair quality and pairing more tightly matched responses should increase transfer where it is expected to reduce it.*

The second version can only be produced by someone who thought about *why* the channel might behave differently under a contrastive objective; that reasoning is exactly what `discovery_strategy_detail` recorded, and writing it into the statement is what turns a slot-fill into a claim. It also fails none of the three tests, and it hands Phase 3 something to search for that is not the anchor paper.

#### The novelty delta is a field, not a hope

Every behavior carries an `innovation` object with two one-line entries, and both are answerable questions with checkable answers:

```json
"innovation": {
  "beyond_transfer": "<what is still new if the borrowed phenomenon reappears here exactly as its source predicts>",
  "method": "<the one move in the design that is not standard practice for this phenomenon>"
}
```

`beyond_transfer` is `/mechanism-behavior-discovery`'s novelty delta, written down. **"The domain is new", "the modality is new", "it is tested at a larger scale", and "nobody has run this exact combination" are not answers** — they describe where the work happens, not what it establishes. Real answers name a quantity that did not exist before (a rate, a capacity, a half-life, a boundary, an interaction), a prediction that contradicts the standing account, or a use the phenomenon is put to.

`method` is `/mechanism-explore`'s method-innovation line, one stage early — the adapted instrument, the imported paradigm, the measurement taken where nobody takes it, the rescue arm, the unit of analysis that had to be defined. **"Induce trait in teacher, SFT student, run trait probe" is not an answer** when that is the anchor paper's own design; it is the control condition the new design has to beat. A behavior may legitimately reuse a standard design *when `beyond_transfer` carries the whole delta* — say so in the field, in those words, rather than dressing an off-the-shelf protocol as a contribution.

**Repair, then drop.** A behavior whose `beyond_transfer` reduces to a domain, modality, or scale swap, or whose `method` restates the anchor design, goes back to `WRITER` **once** with the failing test quoted and an instruction to either find the delta or replace the behavior. If the second pass still has none, drop it before persisting and count it in the round report as `dropped: transfer-only`. This is the one place in Step 1 where a candidate is discarded on quality rather than duplication, and it is cheap here — Phase 3 would spend a full literature search discovering the same thing, and Phase 5 would cut it anyway after the pool had already been shaped around it.

**Round step 3 — Semantic dedup, then the delta filter.** Use `llm-chat` for semantic judgment, not string match: flag each new behavior `new` or `duplicate-of:<Bk>`. Two behaviors are the same behavior when they name the same phenomenon under the same trigger, whatever their wording says. Drop duplicates; merge any extra nuance into the existing node's `notes`.

Dedup runs over **both passes' output together**, and over the whole library, in one judgment — a cold behavior and a guided behavior that landed on the same phenomenon are duplicates like any other. When they do collide, **keep the cold one** and merge the guided one's nuance into it: the cold statement was reached without the scaffolding, which makes it the better record of what the phenomenon is, and it is usually the less templated of the two.

Dedup also catches **template collapse**, which plain semantic dedup does not: two behaviors that differ only in the slot filled into a shared setup sentence — same trigger, same measurement, same predicted direction, different trait or domain or objective — are one phenomenon, and the library keeps the general statement, listing the instantiations in `notes`. Ten trait names in ten nodes is one node with a list, and it is what makes a pool look full while covering one idea. Flag these as `duplicate-of:<Bk>` on the same footing as semantic duplicates.

Then apply the **delta filter** from *The novelty delta is a field, not a hope*: every surviving behavior's `innovation.beyond_transfer` and `innovation.method` are checked, failures go back to `WRITER` once, and anything still empty is dropped as `transfer-only` rather than persisted. Report both counts separately in the round ledger — `duplicates dropped` and `transfer-only dropped` diagnose different broken rounds.

**Round step 4 — Impact score.** For each surviving behavior, score its importance following `/impact-check`'s dimensions — does it solve a real problem, would it be used or cited, could it shift a field's direction, does it help applications or cross-disciplinary work, does it reveal an important phenomenon even with a simple method. If `IMPACT_WEB`, run one quick web/arXiv search per behavior first to ground the score. Return `score` (1–10, 10 = clearly important), a one-line `rationale` (why it matters + who would build on it), and a `recommendation` (`PROCEED` / `PROCEED WITH CAUTION` / `DEPRIORITIZE`). Stamp `method` (`llm-chat` / `llm-chat+web`) and `date`. Judge importance **on its own merits, not against `INTENTION`** — a behavior that serves the intention perfectly but matters to nobody scores low. The intention belongs in the `rationale`'s "who would build on it" half, and it does its ranking work later, as Phase 5's tiebreak. This is a lightweight triage score, not a publication-grade verdict — **no cut happens here.**

**Round step 5 — Merge and persist.** Assign ids by max-suffix+1, never reused: `B1`, `B2`, …. Set `status: "candidate"`, stamp `batch` (date + run index + round index, e.g. `2026-08-15.run01.r03`) and `updated`. Write `hypothesis_library.json` **now, before the next round** — this persisted state is what the next round reads as its banlist.

**Authorship vs. mechanics at this step.** `hypothesis_library.json` is a `WRITER` deliverable, exactly as `claim.json` is: every authored field of a behavior — `statement`, `five_bars`, `discovery_strategy_detail`, `innovation`, `notes`, and the `impact.rationale` line — is `WRITER`'s own wording, carried through verbatim. The orchestrating agent performs only the mechanics that `WRITER` cannot: assigning ids, stamping `pass` / `status` / `batch` / `updated`, stripping a numeric prefix off a `discovery_strategy` label, merging into the pool, and writing the file (the `llm-chat` backend has no file access). It never rewrites, paraphrases, tightens, or translates an authored field; a field that needs changing goes back through `WRITER`. This is what makes the same model that conceived a phenomenon in Phase 2 the one that writes it up in Phase 7 — the two deliverables share one voice by construction, not by reconciliation.

**Early stop.** If a round adds **0** survivors after dedup, the topic is saturated for this run: stop the loop and note it in the Phase 5 report rather than spinning further rounds. Never pad a round with near-duplicates to fill it.

Read the two drop counts before concluding saturation, because they mean opposite things. A round emptied by **duplicates** is saturated — the search space is exhausted at this slice, and another round finds the same things again. A round emptied by the **delta filter** is not: the space is still open and the generation collapsed into slot-filling, which is a prompt failure, not a topic failure. In that case run one more round with the failed statements pasted in as negative examples and `COLD_N` raised, before declaring saturation.

**Breadth is the point.** The pool exists to be cut, so `ROUNDS × N_BEHAVIORS` near-duplicates of one framing is a failed Step 1. Overshoot rather than undershoot: the pool must survive a novelty gate and a design veto and still leave `TOP_N`. A pool below `2 × TOP_N` after dedup means the rounds collapsed onto each other — run one extra round aimed at whatever the dedupe revealed as over-covered.

#### Library schema (canonical JSON — one topic per file)

Step 1 writes exactly these fields. Step 2 adds its own (see "Step-2 fields" below); nothing else is ever written here.

```json
{
  "topic": "<topic>",
  "topic_slug": "<slug>",
  "intention": "<INTENTION — the positional argument, verbatim>",
  "created": "<YYYY-MM-DD>",
  "updated": "<YYYY-MM-DD>",
  "behaviors": [
    {
      "id": "B1",
      "source": "discover",
      "pass": "<cold | guided>",
      "discovery_strategy": "<bare lens name, or \"cold-pass\" — never a numbered label from the skill file>",
      "discovery_strategy_detail": "<how this idea was reached: the concrete provenance of the conjecture — e.g. which finding/method from which discipline was borrowed and mapped onto what here, or which past CS result was reused in which new setting. Provenance, not a protocol.>",
      "statement": "<the phenomenon, its trigger, and its delta clause — two to three sentences, per 'Writing a statement'>",
      "innovation": {
        "beyond_transfer": "<what is still new if the borrowed phenomenon reappears exactly as its source predicts — never 'the domain is new'>",
        "method": "<the one move in the design that is not standard practice for this phenomenon, or an explicit 'standard design; the delta is entirely in beyond_transfer'>"
      },
      "five_bars": {"real":"","nonobvious":"","specific":"","robust":"","tractable":""},
      "impact": {
        "score": 8,
        "rationale": "<one line: why it matters + who would build on it>",
        "recommendation": "<PROCEED | PROCEED WITH CAUTION | DEPRIORITIZE>",
        "method": "llm-chat+web",
        "date": "<YYYY-MM-DD>"
      },
      "gaps": [
        {"id": "G2", "gap": "<the gap restated in one self-contained line — never the id alone>"}
      ],
      "notes": "<optional merged nuance>",
      "status": "candidate",
      "batch": "<YYYY-MM-DD.runNN.rNN>"
    }
  ]
}
```

**No mechanism axis.** The library holds behaviors only — no `mechanisms` array, no internal object, no causal relation, no per-mechanism novelty. The mechanism is attached in Step 3, to the `TOP_N` survivors only, and lives in their claim directories.

`source` is `discover` for every behavior this skill mines. `pass` records which half of Round step 2 produced it — `cold` or `guided` — and is stamped by the agent, not authored; it is what makes the cold pass auditable, so a later run can ask whether unprimed generation is actually earning its share of the survivors. `status` lifecycle: `candidate` (written here) → `selected` / `eliminated` (written by Phase 5) → `explored` (flipped by hand when the user promotes a claim into an `/auto` round).

## Step 2 — Evaluate and select the top N

### Phase 3: Deep Novelty Verification (hard gate)

Run a thorough novelty check on **every behavior in the library** with `status: "candidate"` — one `/novelty-check` per behavior, dispatched in parallel:

```
/novelty-check "[behavior Bk: statement + trigger + innovation.beyond_transfer + innovation.method + why it would be surprising]"
```

**Check the delta, not just the phenomenon.** Pass `innovation` into the prompt and require the verdict to address it: a behavior whose phenomenon is reported in the literature is **not** automatically eliminated if its `beyond_transfer` is a quantity, boundary, or prediction that no found work establishes — that is precisely the case the delta was written for, and eliminating it collapses the workflow back to hunting for phenomena nobody has ever mentioned. The elimination bar is *the claim as stated is already established*, not *this area has been studied*. Conversely, a behavior whose delta the search does find, in a paper the statement never anticipated, is eliminated even when its surface framing looks fresh. Record which of the two the verdict turned on in `novelty.verdict`'s accompanying note.

**What this does:**
- Multi-source literature search (arXiv, Scholar, Semantic Scholar)
- Cross-verify with the external LLM reviewer
- Check for concurrent work (last 3–6 months)
- Identify closest existing work and differentiation points

**This is the only hard gate.** Eliminate any behavior that turns out to be already reported: set `status: "eliminated"` with `selection.reason = "already published — <the work>"`. Behaviors are never deleted from the library; an eliminated node stays as a citable record of what was tried.

For each survivor, record its **three nearest works** with the specific finding each established — Phase 7's `Related Work` field and checklist item 1 both need exactly this, and re-deriving it later wastes a second literature pass.

### Phase 4: External Critical Review

Review **every behavior that survived novelty** — not just a shortlist. One `/research-review` per survivor, dispatched in parallel:

```
/research-review "[behavior Bk: statement + five bars + innovation + impact rationale + nearest works]"
```

**What this does:**
- The external LLM reviewer acts as a senior reviewer (NeurIPS/ICML level)
- Scores the behavior as a study target, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

Reviewing the full pool rather than a pre-selected `TOP_N` is deliberate: novelty and impact both judge *whether the question is worth asking*, and neither can tell whether the phenomenon can actually be measured. That is the reviewer's lens, and it is worth having **before** the batch is fixed rather than after.

The feedback has two distinct downstream uses, and Phase 5 depends on telling them apart:

- **Fatal design flaws** — the phenomenon is not falsifiable as stated, the measurement cannot reach the quantity it claims to measure, a confound is structural rather than controllable, no accessible model could exhibit the trigger. Refinement cannot rescue these; they are grounds for elimination.
- **Ordinary weaknesses** — incremental framing, execution risk, thin baselines, unclear presentation. These are exactly what Phase 7's refinement is for and must **not** eliminate anything.

Classify each review as one or the other when recording it.

#### Step-2 fields

Phases 3–5 write these back into each behavior node, alongside the Step-1 fields:

```json
{
  "novelty": {
    "score": 7,
    "verdict": "<NOVEL | ALREADY PUBLISHED>",
    "nearest_works": [
      {"work": "<author, year — title>", "established": "<the specific finding it established>", "separation": "<what this contradicts / extends past its scope / looks at where it never looked>"}
    ],
    "method": "llm-chat+web",
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

This is the only cut that produces the batch. It combines all three signals.

**Step 1 — Apply the veto.** Eliminate every behavior whose Phase 4 review found a **fatal design flaw**, regardless of its impact score. A phenomenon whose measurement cannot answer its own question does not become shippable by being important. Set `status: "eliminated"`, `selection.reason = "vetoed at external review — <the flaw>"`.

**Step 2 — Rank the rest.** Order by **impact first, reviewer score second, novelty third**:

- **Impact** dominates — a less-novel behavior on an important problem outranks a novel one nobody needs.
- **Reviewer score** breaks impact ties and pulls down behaviors the reviewer found weak-but-fixable.
- **Novelty** is the last tiebreak only. Everything still standing already passed Phase 3's gate, so it has little spread left to discriminate on.

`INTENTION` breaks ties before novelty does: at equal impact and reviewer score, the candidate that serves the stated intention outranks the one that ignores it. It never overrides the veto or the novelty gate — an intention-perfect behavior that is already published or structurally unmeasurable is still eliminated.

**Step 3 — Take the top `TOP_N`.** Everything below the cut gets `status: "eliminated"`, `selection.reason = "below rank <TOP_N>"`. This ranking fixes the folder numbering in Phase 7 — nothing downstream re-orders it.

**Step 4 — Check the spread.** If the top `TOP_N` collapse onto two or three phenomena classes, swap the lowest-ranked duplicates for the highest-ranked candidates covering a distinct class, and record each swap in `notes`. `TOP_N` skeletons on one phenomenon class is a worse batch than `TOP_N` on eight, even at slightly lower average score.

**If fewer than `TOP_N` survive**, run **one** top-up round: return to Phase 2, generate additional behaviors aimed at the gaps the eliminations exposed, and put them through Phases 3 → 5. If the batch is still short after that round, ship what survived and state the shortfall plainly. Never pad the batch with a behavior that was already eliminated, never overturn a novelty verdict or a design veto to reach `TOP_N`.

**Report.** Print: `INTENTION` (verbatim), the distilled `TOPIC`, `ROUNDS` requested vs. actually run (note early stop if a round saturated), a one-line per-round ledger (round → cold added / guided added → duplicates dropped → transfer-only dropped → running total), total pool size, eliminations by reason, the impact score distribution (min/median/max), and the selected `TOP_N` with their ranks and claim directories.

Add two lines that diagnose the *generation* rather than the batch, because they are what a later run acts on:

- **Cold-pass yield** — of the `ROUNDS × COLD_N` cold behaviors, how many survived dedup, how many survived Phase 3, and how many made the `TOP_N`. A cold yield at or above the guided yield says the taxonomy is costing more than it gives on this topic and `COLD_N` should rise next run; a cold yield of zero across all rounds says the cold prompt is not being kept clean, or the topic genuinely has no unprimed surface left.
- **Delta distribution** — a tally of what the selected behaviors' `innovation.beyond_transfer` entries actually claim (new quantity / contradicted prediction / measured boundary / new instrument / new use). If one bucket holds most of the batch, say so: the pool searched one way, and the next invocation's round ≥ 3 assignment should be aimed at the empty buckets.

## Step 3 — Mechanism and claim

### Phase 6: Mechanism Strategy Load

This phase loads strategy into context; it writes **no artifact**. Invoke `/mechanism-explore` via the Skill tool and read its `SKILL.md` in full — the macro-level strategy layer above the concrete method families, organized around six parallel directions (Location / Causal Intervention / Tuning & Editing / Formation Tracing / Unit Interpretation / Decision Auditing), the strategies that chain them, and the **method-innovation moves** that keep a chain from being an off-the-shelf recipe. It shapes *how to explain* each selected behavior. Read it, do not execute its phases, and do not expect an output file. Log `[mechanism-strategy] loaded /mechanism-explore`.

**Attach a mechanism to each selected behavior.** The library carries none, so this is where each of the `TOP_N` acquires one. For each selected behavior, frame a **falsifiable mechanistic hypothesis**:

- the **internal object** held responsible — layer / head / neuron / SAE feature / direction / circuit;
- the **predicted causal relation** — ablate → effect, steer → dose-response, patch → localization;
- at least one **boring null** — memorization / surface feature / shortcut / tokenizer / position;
- the `/mechanism-explore` combination strategy it commits to (e.g. Location → Causal Intervention), chosen for *this* behavior and justified in one line;
- **the method-innovation line** — what this investigation does that is not the standard recipe for a phenomenon of this kind, and what that buys. It is written against `/mechanism-explore`'s § Method Innovation and it inherits the behavior's own `innovation.method`, which was committed to back in Phase 2: **the mechanism plan makes good on that commitment or explicitly supersedes it with a stronger one**, and if it silently reverts to the default chain, the claim ships with a design the behavior's own library node already said was insufficient. A chain of standard steps with no such line is not ready to be written up.

Prefer a hypothesis on a **climbable ladder of evidence**. The direction is fixed here; the concrete submethod is whatever `Experiments` commits to. Hold the mechanism in context and feed it into Phase 7; it surfaces as `claim.json`'s H-list. **Do not write it back into `hypothesis_library.json`** — the library stays behavior-only.

### Phase 7: Write `claim.json` — the reviewer-facing deliverable

**From here on the batch splits.** Each of the `TOP_N` behaviors becomes one `claim.json`, written **independently, in its own directory**, and nothing is shared between them except the landscape.

**Run the claims one at a time, in the Phase 5 rank order** — claim `01` is finished and closed before claim `02` starts. Working one claim at a time is what keeps each claim's numbers, conditions, and slug from bleeding into its neighbours, which is what `Batch independence` protects. Phases 3 and 4 stay parallel — they are read-only fan-out and share no files. It is only Step 3 that serializes.

**Step 0 — Create the directory.** For the claim being worked, at its Phase 5 rank:

1. Derive `<name>`: a **snake_case slug, ≤ 6 words, naming the phenomenon** — the same slug that becomes `claim.json`'s `Name` field. Derive it once here and reuse it verbatim; the directory name and the `Name` field must not diverge.
2. Create `claims/<NN>_<name>/`, where `NN` is the zero-padded rank (`01`…`<TOP_N>`).
3. Write the path back to the behavior node as `selection.claim_dir`.
4. Log `[claim] <NN>_<name> — "<behavior statement>"`.

**Step 1 — Draft.** `WRITER` writes the seven keys in one pass, in the write order below. `WRITER` sees only what it is given, so assemble the input first:

- the behavior node in full — `statement`, `five_bars`, `discovery_strategy_detail`, `innovation`, `gaps` (id **and** restated line), `impact.rationale`;
- its three nearest works from `novelty.nearest_works`, each with the finding it established and the separation;
- the Phase 6 mechanism hypothesis — internal object, predicted causal relation, boring nulls, the combination strategy, the method-innovation line;
- the Phase 4 reviewer feedback, ordinary weaknesses included — those are what this draft is meant to fix;
- `INTENTION`, verbatim — the claim **serves** it and never quotes it. Its constraint half (the affordable scale, the setting, the kind of model that has to settle it) binds concrete choices in `Experiments`, and its wanted-result half is what the sentence naming who acts on the answer should actually be useful to. It never supplies framing vocabulary: a claim that echoes the user's phrasing reads as a restatement of the request rather than a paper;
- this phase's specification, from `Feasibility and clarity` to `Write order`.

When `WRITER = session` the agent drafts directly and can read whatever it needs; when `WRITER = llm-chat` the same material must be pasted into the `mcp__llm-chat__chat` prompt, because the chat model has no file access and no memory of having generated the behavior in Phase 2.

**Step 2 — Refine.** Send the draft to `REVIEWER_BACKEND` as a senior reviewer and revise, **up to 5 rounds, stopping at a score ≥ 9 or when a round yields no material change**. `llm-chat` is stateless, so each round's prompt carries the current draft in full plus a verbatim summary of the prior round's critique. The revision is always made by `WRITER`, never by the reviewer — the reviewer scores and objects, it does not rewrite.

Hold a **Problem Anchor** across the rounds: the behavior statement and the mechanism hypothesis as frozen in Phases 2 and 6. Refinement sharpens how the claim is tested and written; it may not drift onto a different phenomenon. If a round's critique can only be answered by changing the phenomenon, that is a Phase 6 mechanism-direction switch (see `Quality checklist`), not a refinement.

**Step 3 — Verify and ship.** The orchestrating agent — not `WRITER`, not the reviewer — checks JSON validity, key names and order, plain-string values, the full `Quality checklist`, and internal numerical consistency. Mechanical faults (key order, escaping, a stray placeholder) the agent repairs directly. Anything that changes the argument goes back through `WRITER` with the failing check quoted, so the prose stays in one voice. Then write `claims/<NN>_<name>/claim.json` and close the claim.

**Failure isolation.** If a claim cannot be brought through this phase, that failure stays local: record it in the behavior's `notes` and `status`, and continue with the next claim. One bad claim never aborts the batch.

**No second plan.** The experiment design lives in the `Experiments` field and nowhere else. Do not emit `EXPERIMENT_PLAN.md`, `FINAL_PROPOSAL.md`, or any `refine-logs/` artifact, and do not invoke `/research-refine-pipeline`, `/research-refine`, or `/experiment-plan` — those write an executor-facing plan this workflow does not ship, and a second copy of a design is a second thing to keep in sync. The executor-facing machine markers that plan carried — `kind: phenomenon-validation`, `method_sensitive:`, `depends_on:`, `grid:`, `cmd:` — are **forbidden in `claim.json`** for the same reason they always were: a reviewer holding only this file cannot decode them. The M0 gate survives as Experiment 1's four outcomes, written as prose.

#### The specification

Everything from here to `Quality checklist` is the specification handed to `WRITER` in Step 1 and the standard the agent verifies against in Step 3. It binds both. `claim.json` is **the final result of the whole workflow** — a paper skeleton good enough to submit to a top AI conference, written for a human expert reviewer who has that file and nothing else.

**This stage plans; it does not run.** Every model, dataset, condition, and measurement named in `Experiments` has to be reachable today rather than aspirational. But nothing is executed here, no GPU is touched, and **anything phrased as a result is a fabrication**.

#### Feasibility and clarity

Before writing, and again before shipping each file: *first carefully consider the quality, novelty, and feasibility of the proposal you just created.*

**Feasibility.** *Ensure that the proposal does not require resources beyond what an academic lab could afford.* In `Experiments`, *ensure these are simple and feasible*. *Do not make things overly complicated.* Novelty bought with an unrunnable plan is not novelty.

**Clarity.** *Ensure the proposal is clear and concise, and the JSON is in the correct format.* In `Short Hypothesis`, *clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.* In `Related Work`, *clearly clarify how the proposal distinguishes from the existing literature.* In `Experiments`, *be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.* A threshold with no stated basis, an equivalence claim with no margin, and a prediction with no direction are all clarity failures, not stylistic ones.

#### Schema

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

The claim JSON should include the following fields:

- "Name": A short descriptor of the idea. Lowercase, no spaces, underscores allowed.
- "Title": A catchy and informative title for the proposal.
- "Short Hypothesis": A concise statement of the main hypothesis or research question. Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.
- "Related Work": A brief discussion of the most relevant related work and how the proposal clearly distinguishes from it, and is not a trivial extension.
- "Abstract": An abstract that summarizes the proposal in conference format (approximately 250 words).
- "Experiments": A list of experiments that would be conducted to validate the proposal. Ensure these are simple and feasible. Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.
- "Risk Factors and Limitations": A list of potential risks and limitations of the proposal.

`Name` is additionally bound to the directory: it is the same snake_case slug, ≤ 6 words, naming the phenomenon, that was derived in Phase 7 — the directory name and the `Name` field must not diverge. The field-by-field section below is this workflow's binding elaboration of the seven descriptions above; where it is more specific, it governs.

#### Field by field

**`Short Hypothesis`** carries the whole claim in one paragraph. It names the **triggering condition** (what has to be true for the phenomenon to appear), the **phenomenon** (a falsifiable regularity in observable model behavior), the **internal object** held responsible (layer / head / neuron / SAE feature / direction / circuit), and **H1…Hk** — two to four sub-hypotheses, each with a stated direction. H1 is always the existence claim: does this happen at all. The last H is the one that pays: a causal intervention or an edit that moves the behavior, not another correlation.

*Organize it around the advantage, not only the protocol.* Four fields of the behavior node carry what makes the claim worth reading, and the paragraph should be shaped so a reviewer meets them: `statement`'s delta clause and `five_bars.nonobvious` for what the standing account predicts instead, `innovation.beyond_transfer` for what this establishes even if the effect lands exactly as predicted, `discovery_strategy_detail` for why one would expect it here at all, and `impact.rationale` for who acts on the answer. A clause or a sentence each, written as part of the claim rather than as a note about it. Trigger + phenomenon + H-list + thresholds alone says what will be measured without saying what would be surprising about the answer or why it matters — and when the same threshold and band are restated verbatim at every H, there is no room left for any of it.

**`Related Work`** names real, citable work — author and year — and for each says *what result it established*, then what this claim contradicts, extends past its stated scope, or looks at where it never looked. «They study X, we study Y» is a topical separation and does not count. It closes with at most one positioning sentence («the first to (i)… (ii)…»), and every clause in that sentence must survive checklist item 1.

**`Abstract`** reads like the abstract of a paper someone would actually open: the human-legible motivation first, then the controlled design, then the hypotheses in a sentence each, then what a positive result gives the field. That ordinary arc is also what makes the claim's novelty and impact visible without ever asserting them — `discovery_strategy_detail` motivates, `five_bars.nonobvious` and the `statement`'s delta clause supply the surprise, `innovation` supplies what the work adds, `impact.rationale` closes on who acts on the result. Opening on the design instead («This plan tests whether…», «We train a student on…») starts the reader past the motivation and the surprise, and the advantage never lands.

*Where its material comes from.* The Abstract is assembled from four fields of the behavior node — `discovery_strategy_detail`, `statement`, `innovation`, `five_bars` — and every one of them is **repackaged, never transcribed**. They enter in this order:

1. **`discovery_strategy_detail` → the opening motivation.** It records *how the conjecture was reached* — which cross-discipline finding or past result was borrowed and mapped onto what. Rewrite it as a claim about the world that makes the reader expect the phenomenon might exist, not as an account of the search that produced it. Its provenance survives as a reason to look here; the fact that it was a discovery *strategy* does not survive at all. When the borrowed source is itself citable, the citation goes to `Related Work` and only its content stays here.
2. **`statement` → the controlled-design sentence.** Restate the phenomenon and its triggering condition once, in the paper's register, with the same direction and the same numbers `Short Hypothesis` uses. This is a second statement of the same claim for a reader who will not read further, not a second, subtly different claim — if the two drift apart, checklist item 8 fails. The statement's **delta clause** — what the standing account predicts instead — is the half that most often gets dropped in this restatement, and it is the half a reviewer is reading for; keep it, and keep it as a competing prediction rather than a hedge.
3. **`innovation` → what the paper is claiming to add.** `beyond_transfer` becomes the sentence that says what this establishes *that would still be worth knowing if the effect turns out exactly as expected* — the quantity, the boundary, the contradicted prediction. `method` becomes a clause in the design sentence naming the instrument or paradigm that makes the measurement possible, and it must match what `Experiments` actually does. Neither surfaces as a claim about the paper's own novelty: no «our key innovation is», no «unlike prior work we are the first». The move is stated, and the reader draws the conclusion.
4. **`five_bars` → the surprise and the scope.** `nonobvious` becomes the sentence saying what a reader would have predicted instead, which is what makes the result worth an abstract; `real` becomes the reason the effect is a phenomenon rather than an artifact of the setup; `specific` becomes the bound on what is being claimed. `robust` and `tractable` stay out — they justify studying the behavior, which is Step 2's business, and say nothing to a reviewer — unless one of them carries a number that `Experiments` also reports, in which case that number appears once, here, in the design sentence.

*The packaging is the point.* None of the four source vocabularies may surface: no «discovery strategy», no «five bars», no «non-obvious», no «real / specific / robust / tractable» used as labels, no «novelty delta», no «beyond transfer», no «method innovation», no «we borrowed this from», no «this behavior is tractable because». Each source field dissolves into a sentence that had to be written anyway, exactly as `The routing must not show` and `One register for the agent, another for the reviewer` require. **The test: a reviewer must not be able to tell the Abstract was assembled from a JSON node** — and must not be able to recover which sentence came from which field.

> **Transcribed:** *Subliminal learning is a phenomenon where traits transmit through semantically unrelated data. This behavior is real because the effect has been observed at multiple scales, non-obvious because filtering is assumed to work, and specific because it is scoped to same-initialization teacher-student pairs. The idea was reached by transferring the notion of a carrier signal from steganography.*
>
> **Repackaged:** *A student model finetuned only on a teacher's number sequences — no trait words, no semantic content that survives filtering — still inherits the teacher's behavioral trait. Data filtering is the defense every distillation pipeline currently relies on, and it is defeated here by construction rather than by an oversight, in the way a steganographic channel defeats a content filter: the signal is carried by the choice among equally valid outputs, not by the outputs' meaning. We ask what that channel is made of, and find it survives only where teacher and student share an initialization — a bound that turns an alarming general result into a checkable deployment condition.*

**`Experiments`** is the field a reviewer skims hardest. It is written as labelled paragraphs separated by `\n\n`, in this order:

1. **Models** — named ids with sizes and access mode.
2. **Benchmark / data** — where it comes from (existing / adapted / constructed), item count, item structure, and how ground truth is established. If it is constructed, say what a single item looks like.
3. **Conditions** — the manipulation as a labelled set (C0 baseline … Cn), plus any parametric sweep.
4. **Measurements** — what is read off per item and condition, and how each is computed.
5. **Experiment 1 … Experiment k** — one per hypothesis, in ladder order, each headed by the hypothesis it tests and the finding it would produce. Each states its goal, its procedure, its measurement, and **its prediction — with a direction, and with the band in which the measurement would not decide**.
6. **Ablations and controls** — the matched controls, the off-target checks, the confound checks.
7. **Metrics** — the flat list of every quantity reported.

**`Risk Factors and Limitations`** is numbered, and every entry is a threat that could actually land — the probe measures the wrong thing, the effect is a template artifact, the intervention has side effects, the ground truth is contestable — each paired with the specific mitigation already present in `Experiments`. A limitation with no mitigation is allowed only when it is genuinely out of scope, and must say so.

#### The experiment ladder

`Experiments` is organized as a ladder, cheapest and most falsifying first. Each rung becomes one numbered experiment, and a later rung is only worth running if the earlier ones hold.

| rung | what it establishes |
|---|---|
| 1 | the phenomenon happens at all, under its stated trigger |
| 2 | cheap correlational / attribution screening narrows the internal object down to candidates |
| 3 | intervening on a candidate moves the behavior — sign, magnitude, dose–response |
| 4 | matched controls, off-target checks, and confound checks rule out the mundane rivals |
| 5 *(optional)* | how far it holds — phrasing, position, model family, interpretability replication |

**Experiment 1 is a gate with four outcomes**, all spelled out in the text: *established* (the plan proceeds), *conditional* (it holds only under some conditions, and the later experiments are scoped to those), *not established* (the claim dies), *inconclusive* (the measurement itself failed and must be fixed and re-run, not adjudicated). Its pass criterion must cover reproducibility across paraphrase, seed, and decoding; controlled confounds; a sample size clear of noise; and the ruling out of trivial explanations. This gate is the whole of the phenomenon-validation step — there is no separate plan carrying it.

Where a threshold is stated, say what it rests on — measured in a cited paper, or an estimate. Estimates are fine; estimates dressed as measurements are not.

**The rungs themselves are planning vocabulary and never surface in `claim.json`.** «Phenomenon-validation», «localization», «specificity», «M0» are this workflow's names for its own scaffolding, and a reviewer holding only `claim.json` has no way to decode them. Each experiment is headed instead by the hypothesis it tests and the finding it would produce — `Experiment 1 (H1 — Half-life):`, `Experiment 4 (H4 — Activation edit):` — and opens with a sentence saying what it does in the paper's own terms. The ladder should be legible from the **order and content** of the experiments, never from a label the reader has to look up.

#### The undecidable band

Experiment 1's *inconclusive* outcome is not special to the gate. Every threshold splits the outcome space into three regions rather than two — results that clearly support the hypothesis, results that clearly refute it, and the band between them where the planned measurement cannot decide — and finite samples, measurement noise, and any equivalence margin guarantee that band exists for H2…Hk as well.

So each hypothesis states its own, in the experiment that tests it: **where the band lies**, in the threshold's own units (an effect between 0.5σ and 2σ of cross-seed noise, say, or a half-life whose interval spans zero); **what a result there means**, said plainly — H*i* is not supported at the planned power, the effect being too small to separate from noise at this sample size, or the measurement too coarse to separate the mechanism from its rivals — and not «a weak trend consistent with H*i*», not silence; and **what follows**, fixed before the data rather than after it: H*i* reported as undecided, the pre-specified extension run if the plan budgets one (more items, more seeds, a finer measurement), and the experiments depending on H*i* stopped, scoped, or run unchanged.

That belongs where the reviewer meets the hypothesis. `Risk Factors and Limitations` adds only what the experiment cannot: where the plan's own power estimate says the band is likely to be entered — a small expected effect, few available items, a high-variance intervention — say so there, with what it would cost to narrow it.

#### Numerical consistency

Every quantity that carries a number — a threshold, a margin, a sample size, an item count, a budget — is defined once and written identically everywhere it appears: same name, same value, same unit. A bar introduced in `Short Hypothesis` is the bar the matching experiment's prediction enforces, the one `Ablations and controls` and `Metrics` report against, and the one any `Risk Factors and Limitations` entry mentioning it uses.

Because the design is written once, in this file, consistency is a **within-file** property and there is nothing to reconcile against a second copy. That makes it strictly checkable rather than merely aspirational: every number either appears once, or appears several times at the same value and unit. When two occurrences disagree, decide which is right and fix every occurrence — never soften a number in one field to match another, and never let a percent become a proportion or tokens become layers on the way from one field to the next.

A quantity whose value genuinely depends on a submethod not yet chosen is still **one** number: commit to the value the plan assumes, and name the dependency in `Risk Factors and Limitations` as an open choice with its options.

#### From working notes to paper

This run writes far more than it ships. `LANDSCAPE.md` holds the survey; `hypothesis_library.json` holds the pool, the scores, and the eliminations. **A reviewer sees `claim.json` and nothing else**, and the whole difficulty of this phase lives in that gap.

Every piece of working material either dissolves into one of the seven fields or stays behind. It never gets a field of its own, and it never goes unplaced by default:

| what the run produces | where it lands in `claim.json` |
|---|---|
| the phenomenon and its triggering condition (`statement`) | `Short Hypothesis`, opening sentences; restated once in `Abstract` as the controlled-design sentence, same direction and same numbers |
| where the idea came from — the cross-domain result or human finding it transfers (`discovery_strategy_detail`) | `Abstract`, the opening motivation, rewritten as a claim about the world rather than an account of the search; a clause in `Related Work` when the source is itself citable |
| what is new even if the transfer succeeds exactly (`innovation.beyond_transfer`) | `Abstract`, the sentence saying what the result establishes; `Related Work`, as the separation clause against the nearest work — this is the field that stops «X, but in Y» from being the whole claim |
| the design move that is not standard practice (`innovation.method`, Phase 6's method-innovation line) | `Experiments`, where the instrument or paradigm is introduced and justified in the sentence that introduces it; one clause in `Abstract`'s design sentence |
| why a reader would have predicted otherwise, and what the claim is bounded to (`five_bars`: `nonobvious`, `real`, `specific`) | `Abstract`, the surprise-and-scope sentences — dissolved into prose, never as labelled bars |
| the structural gap in the landscape | `Related Work`, restated as what the literature has not done |
| the mechanistic conjecture — internal object, causal relation (Phase 6) | `Short Hypothesis`, the H-list |
| the mundane rival accounts — the boring nulls | `Experiments`, where each one's control is introduced; `Risk Factors and Limitations` for any left unhandled |
| the three nearest works (Phase 3 / checklist 1) | `Related Work`, roughly a clause each |
| the expert's prior (checklist 2) | `Abstract` or `Related Work` — whichever sentence explains why the result would surprise |
| the consumer on each branch (checklist 3) | `Abstract`, closing sentence |
| the breaking case (checklist 4) | `Risk Factors and Limitations`, as the stated scope bound |
| the ladder, its gates, controls, models, data | `Experiments` |
| `five_bars`' remaining two bars (`robust`, `tractable`) | nowhere — they justify *studying* the behavior, which is Step 2's business, and say nothing to a reviewer; the exception is a number one of them carries that `Experiments` also reports, which appears once in `Abstract`'s design sentence |
| novelty / impact / reviewer scores, rank, ids, rung names, eliminated behaviors | nowhere — batch bookkeeping, stays in `hypothesis_library.json` |

**The routing must not show.** The table says *where*, not that a sentence must appear. It routes material already going into the paper; it is not a list of sentences to add. A row is discharged when its content is *there* — usually inside a sentence written for another reason, often as a subordinate clause, sometimes two rows at once. The test runs backwards: **a reviewer must not be able to reconstruct this table from the prose.** Nothing announces its own function — no «our contribution is novel because», no «the expert prior is», no «as a named consumer». If a row's content is already carried by a sentence that had to be written anyway, it is done; adding a dedicated sentence for it makes the paper worse, and a paper that reads like a completed form does not survive review.

> **Routing showing through:** *The expert prior here is that retraction fully erases the claim, so our result is non-obvious. If the claim is true, deployers of retrieval-augmented systems will audit their corrections; if false, they will not.*
>
> **Absorbed:** *A retraction is normally assumed to do what it says: the claim is withdrawn, and what follows is computed without it. We find instead that the withdrawn claim keeps shaping downstream inferences long after the model has verbally accepted the correction — an assumption that every multi-turn and retrieval-augmented deployment currently relies on untested.*

**One register for the agent, another for the reviewer.** Every row of the table is sourced from something written in a register that is not the paper's — a bulleted gap in `LANDSCAPE.md`, a scored node in `hypothesis_library.json`, a reviewer's objection from Phase 4. All of it was written to be *processed*, by a machine or by you later; none of it was written to be *read*. So carrying a sentence across means **rewriting it in the paper's register**: keep the numbers, the direction, and the controls; drop the operational scaffolding that matters only to whoever runs it; and restore what an executor never needed and a reviewer cannot do without — what the measurement is *for*, and what it would show.

> **Executor-facing:** `M2: for l in [12,16,20] patch resid_post @ last_tok, α∈{0.5,1,2}, n=200/cond, log Δlogprob(P) vs C0; gate |Δ|>2σ_seed; fallback l=8 if OOM.`
>
> **Reviewer-facing:** *Experiment 3 (H3 — Causal confirmation): We patch the residual stream at layers 12, 16, and 20 at the final token of the retraction, sweeping the edit strength over three values on 200 items per condition, and measure the change in log-probability of the retracted claim relative to the no-mention baseline. If the localized component is causal rather than merely correlated, the effect should be negative, should grow monotonically with edit strength, and should exceed the cross-seed noise we measure in Experiment 1.*

**Nothing may point at a file the reviewer does not have.** No «the gap identified in `LANDSCAPE.md`», no «behavior B7», no bare «Gap 3», and no reference to the other claims in the batch — each `claim.json` stands entirely alone. Where such material earns a place in the paper it is restated in full: the gap becomes a sentence about what the literature has not done, the rejected alternative becomes a design choice with its reason. Fail: any noun phrase in `claim.json` whose referent lives only in another file.

#### Writing for the reviewer

- **`Short Hypothesis`, `Related Work`, and `Abstract` are continuous prose** — no bullets, no sentence fragments, no telegraphic notation. They should be readable end to end by someone who has never seen this workflow.
- **`Experiments` is structured at the label level and prose everywhere below it.** The labels exist so a reviewer can find the model list without reading the whole field, but a label is a signpost, not a license to stop writing sentences. Write «We fit an exponential decay of the probe-minus-baseline difference against washout distance and report a per-model half-life in tokens; we predict a positive half-life for every model, longer for stronger initial assertions», not «fit: exp decay; x: washout; out: half-life (tok); pred: >0». Only item 7 is a list.
- **Every sentence carries its own referents.** Name the condition rather than pointing at «C2», say what a step is *for* rather than assuming the reader knows what «specificity» buys, and expand an abbreviation the first time it appears. A label may be introduced and then reused («(C2) P asserted then explicitly retracted» once, «C2» thereafter) — but it must be introduced *inside* `claim.json`, in the field where it is first used.
- **No placeholders ship.** No `TBD`, no `<…>`, no «details to be determined». An unknown is either resolved or named in `Risk Factors and Limitations` as an open choice with its options.
- **Name a work only if you can cite it.** Author and year, and a result you can state. A fabricated citation invalidates the whole skeleton.
- **Prefer the number to the quantifier.** «1,500 items across four domains» over «a large benchmark».

#### Write order

Write the argument first and the machinery last: **`Short Hypothesis` → `Related Work` → `Abstract` → `Experiments` → `Risk Factors and Limitations`**, and finally `Title` and `Name`; the title comes easiest once you know what the paper actually shows.

The order is the argument's own dependency order. `Short Hypothesis` fixes the triggering condition, the phenomenon, the internal object, and H1…Hk — everything downstream is an elaboration of it. `Related Work` then states what the three nearest works established and what this claim does that they did not, which is what decides how much of the design has to be *distinguishing* rather than merely sound. `Abstract` repackages the behavior node against that positioning. Only then is `Experiments` written, because by that point the ladder has nothing left to invent: each rung is the test of an H that already exists, and Experiment 1 is the gate on the phenomenon as `Short Hypothesis` already stated it. Writing the design first inverts this — the plan starts generating hypotheses to justify the experiments it wanted to run.

**Two consequences of writing `Experiments` last, both binding.**

- **Numbers originate upstream and `Experiments` inherits them.** A threshold, margin, sample size, or item count is fixed the first time it is claimed — usually in `Short Hypothesis`, sometimes in `Abstract`'s design sentence — and `Experiments` enforces *that* value at *that* unit, in the prediction, the controls, and the metrics list. When writing `Experiments` reveals a number was wrong (underpowered, unaffordable, wrong unit), fix it at every occurrence including the upstream one; never let `Experiments` quietly carry a second value. This is the same one-quantity-one-number rule read in the new direction.
- **The ladder is still a gate, just a later one.** Writing `Experiments` first had the virtue of forcing concreteness early. That check does not disappear — it moves: once the ladder is written, re-read `Short Hypothesis` against it. If some H has no rung that could falsify it, or Experiment 1 cannot kill the claim (checklist item 5), or a rung had to invent a condition `Short Hypothesis` never mentioned, then the hypothesis was not ready and it is `Short Hypothesis` that gets rewritten — not the ladder that gets bent to fit it. A claim that cannot be laddered is still not ready to be written up; it just fails at the end of the pass instead of the start.

#### Quality checklist

Run this on **each** `claim.json` before shipping it. Each item is a **check that can fail on a fact**, never a quality the author can assert. «This idea is non-obvious» is satisfied by typing it; «name the three nearest works and say which of their findings this contradicts» is not.

What these checks turn up is content, not scoring. Each finding has a field waiting for it in the routing table above and is written there as part of the paper's argument — never as a self-assessment of how the claim scores.

*Is the idea new*

1. **Three nearest works, each separated at the level of a finding.** Name the three closest works. For each, state the specific result it established and what this claim contradicts, extends past its scope, or looks at where it never looked. Fail: fewer than three can be named, or any separator is merely topical — and **a separator that names only a different domain, modality, objective, or model scale is topical**, however important the new domain is. The behavior node already committed to a `beyond_transfer`; if no separation clause in `Related Work` carries it, either the claim drifted off its delta during drafting or the delta was never real. If genuinely nothing is close, decide which case it is — nobody asked the question, or nobody has a use for the answer — and if it is the second, the claim changes.
2. **The expert's prior is written down before the plan is.** State the direction a researcher in this area would predict for the key measurement without having read this claim. If it matches the claim's own prediction, the direction is not what is new — say what is (the magnitude, the mechanism producing it, the setting) and check that the experiment measures *that*. Fail: no experiment distinguishes the claim from the expert's prior.

*Would it matter*

3. **Both branches have a named consumer.** Say who does something differently if the claim comes out true, and separately if it comes out false — a specific decision (what gets audited, what gets deployed, which assumption gets dropped), not «the community would understand this better». Fail: either branch is empty.
4. **The stakes survive stripping the setting, and the scope has an edge.** Re-read the claim with its high-stakes setting (clinical / legal / financial / safety) swapped for a neutral one. If the contribution evaporates, the contribution was the framing — either drop the framing or make the setting do real work, with the mechanism turning on something particular to that domain rather than on its stakes. Then name one concrete setting where the conclusion should **break**. Fail: the contribution is carried by the setting, or no breaking case can be named.

*Can it be settled*

5. **Experiment 1 can kill the claim.** Assume it returns *not established*: does `Short Hypothesis` die with it? If the claim could survive by reinterpreting the outcome as a measurement problem, the gate is hung on the wrong object — re-hang it. (*Inconclusive* is the branch for a broken measurement; it must not become a hiding place for the claim.)
6. **Every mundane explanation is paired with a control.** Match each boring null one-to-one against the controls in `Experiments`. Any account with no control either gets one or moves into `Risk Factors and Limitations` as explicitly not ruled out. Listing a rival and then ignoring it is a fail.
7. **Every hypothesis has its undecidable band written out.** For each of H1…Hk, point to where `claim.json` says how wide the band is, that a result inside it leaves H*i* unsupported at the planned power, and what the dependent experiments do then. Fail: a prediction with only two outcomes; a band with no stated consequence; a non-significant result read as evidence for a null without an equivalence margin.
8. **Every number agrees with itself.** List every numeric quantity in `claim.json` and check each occurrence of it against the others, comparing value *and* unit — a percent silently becoming a proportion, tokens becoming layers. Fail: one quantity holding two values across the seven fields; a bar set in `Short Hypothesis` that a later experiment does not enforce at that value; a threshold in `Metrics` that no experiment predicts against. Repair every occurrence; never drop the number instead.

9. **The design does something the standard recipe does not, and the paper says what it buys.** Point to the sentence in `Experiments` that introduces the adapted instrument, the imported paradigm, the rescue arm, the newly-defined unit, or the measurement taken at a stage nobody measures — and to the clause saying what it makes measurable that the default design could not. Fail: `Experiments` could be transplanted onto a different phenomenon in this area by changing the nouns; or the behavior's `innovation.method` named a move that no experiment implements. The permitted exception is the case the node declared — a standard design whose delta is carried entirely by the claim — and then item 1's separation must be doing all the work, visibly.

**Every failure is repaired in place, not noted.** If a failure cannot be repaired without changing the claim, switch the mechanism direction (Phase 6) and rewrite. After two such restarts on the same behavior, stop working it, set `status: "blocked"` on its library node with what is blocking it, and promote the highest-ranked eliminated behavior into the vacated slot rather than shipping a weak skeleton.

**Batch independence.** The `TOP_N` claims are checked separately and must not converge: if two `claim.json` files end up with the same phenomenon, the same H-list, or the same Experiment 1, one of them was never a distinct behavior — rewrite it onto its own phenomenon or replace it from the ranked list.

#### Closing pass

Read each draft **as if it were the only file that exists**: repair every referent that resolves only elsewhere, rewrite every sentence still addressed to the agent that will run it, and cut every sentence whose only job is to satisfy a row of the routing table. `claim.json` is **always English**, regardless of the language used in the other reports.

**This is the end of the workflow.** Once all `TOP_N` `claims/<NN>_<name>/claim.json` are on disk, stop. Do not implement, launch, or queue any experiment, and do not chain into another skill.

## Output Protocols

> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — `hypothesis_library.json` is a living document updated in place (not timestamped); save raw llm-chat passes to the run trace instead.
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log `hypothesis_library.json` to MANIFEST.md on first creation.
> - **[Output Language Protocol](../shared-references/output-language.md)** — machine fields (ids, `source`, `pass`, `status`, strategy names, scores, `recommendation`, `method`, dates) stay English; free-text `statement` / `discovery_strategy_detail` / `innovation` / `five_bars` / `rationale` / `notes` follows the project language. `claim.json` is **always English** regardless.

## Review Tracing

After each `mcp__llm-chat__chat` call (the cold pass, the guided pass, dedup, the delta-filter repair pass, impact scoring, and — when `WRITER = llm-chat` — every draft, refinement, and repair pass), save the trace per `shared-references/review-tracing.md` to `.mechanist/traces/hypothesis-batch/<date>_run<NN>/`. Keep the cold and guided passes as separate trace files (`cold.json` / `guided.json`) — the cold prompt's cleanliness is auditable only if the prompt itself was kept. With `ROUNDS > 1`, put each round's traces in a `r<NN>/` subfolder (e.g. `.mechanist/traces/hypothesis-batch/<date>_run<NN>/r03/`) so every round's passes are kept separately. Claim-writing passes are per claim, not per round — file them under `claims/<NN>_<name>/` in the trace directory.

## Key Rules

- **Never block on the user.** Run the whole pipeline start to finish without waiting for input — the one exception is the cross-topic guard in Phase 2. Narrate progress however is natural; the artifacts on disk are the deliverable.
- **Don't skip phases.** Each phase filters or refines. Skipping one leads to wasted effort or a silently malformed proposal.
- **The library holds behaviors only.** No mechanism axis, no internal object, no per-mechanism scoring in `hypothesis_library.json`. Mechanism is attached in Phase 6, to the `TOP_N` survivors only, and lives in their claim directories.
- **`claim.json` is the product; everything else is scaffolding.** A run that produces a beautiful library and `TOP_N` thin `claim.json` files has failed. Depth per claim beats size of the pool.
- **One model conceives and writes.** `WRITER` authors both `hypothesis_library.json` and every `claim.json`, and the setting never splits across phases. The orchestrating agent verifies rather than authors: repairs that change the argument go back through `WRITER`, and the agent only fixes mechanical faults.
- **One design, written once.** The experiment design lives in `claim.json`'s `Experiments` field and nowhere else. Never emit `EXPERIMENT_PLAN.md` / `FINAL_PROPOSAL.md` / `refine-logs/`, and never invoke `/research-refine-pipeline`, `/research-refine`, or `/experiment-plan` — a second copy of a design is a second thing to keep in sync, and this workflow ships only the reviewer's version.
- **Rounds accumulate, never repeat.** Persist the library at the end of every round and rebuild the next round's banlist from it, so earlier rounds' behaviors are banned rather than regenerated. A round that adds 0 survivors after dedup means the topic is saturated — stop early and say so; never pad with near-duplicates to fill a round.
- **Semantic dedup, not string match.** Reworded duplicates must be caught by LLM judgment. Two behaviors are the same when they name the same phenomenon under the same trigger, whatever their wording. **Template collapse counts as duplication**: behaviors that differ only in the slot filled into a shared setup — the trait, the domain, the objective — are one phenomenon with a list of instantiations, and the library keeps the phenomenon.
- **Every round generates twice: cold, then guided.** `COLD_N` behaviors are produced with no discovery-strategy taxonomy in the prompt at all, before the guided pass sees it. A taxonomy read immediately before generating decides which ideas are reachable, and the cold pass is the round's only unprimed surface. Never merge the two passes into one call, and never relabel a cold behavior with the lens it resembles.
- **Novelty is never domain transfer.** Every behavior states, in `innovation.beyond_transfer`, what is still new if the borrowed phenomenon reappears exactly as its source predicts — a quantity, a boundary, a contradicted prediction, a use. A new domain, modality, objective, or scale is where the work happens, not what it establishes. A behavior that cannot answer after one repair pass is dropped as `transfer-only` before it is persisted.
- **The method is part of the claim.** `innovation.method` names the one design move that is not standard practice for this phenomenon, Phase 6 makes good on it or supersedes it, and `Experiments` implements it. A design that could be transplanted onto a different phenomenon by changing the nouns is a control condition, not a contribution.
- **A `statement` is written, not slot-filled.** It carries the trigger, the phenomenon, and the delta clause saying what the standing account predicts instead — the provenance in `discovery_strategy_detail` surfaces there as the *reason* the prediction has its shape, never as an account of the search. A statement obtainable by paraphrasing the anchor paper, or by editing one noun in a sibling, is rewritten before it is persisted.
- **Never reuse ids; never delete a node.** Growth is append-only and eliminations stay in the file with their reason, so the library is a stable, citable backlog.
- **Every node is self-contained.** The library outlives the run that wrote it, and `idea-stage/LANDSCAPE.md` is regenerable scratch that the next `/research-lit` overwrites — so a node must never carry a bare pointer into it. Anything referenced from another file is restated in the node: a gap is `{"id", "gap"}` with the gap written out, not `"G2"`. Read any node cold, with no other file open, and it must still say what it means.
- **Score everything.** No behavior is persisted without an `impact` field; no behavior enters Phase 5 without a `novelty` and a `review` field.
- **Kill ideas early.** The cut from the pool to `TOP_N` is where the batch earns its quality — it is cheaper to eliminate candidates in Phases 3–5 than to write more skeletons.
- **The `TOP_N` are independent.** Never let one claim cite, assume, or depend on another; never let two converge onto the same phenomenon.
- **Step 3 is serial; Step 2 is parallel.** Work the claims one at a time in rank order, closing each before opening the next, so no claim's numbers or slug bleed into its neighbour. Phases 3 and 4 stay parallel: they are read-only fan-out over the pool and share no files.
- **One topic per file.** A cross-topic invocation halts and asks rather than overwriting. A new *intention* on the same topic is not a conflict — it accumulates into the same library.
- **The intention is the input.** The positional argument is the whole user intention; there is no `— intention:` flag and no separate topic argument. Carry it verbatim into every brainstorm round, the impact rationale, and the Phase 5 tiebreak — never a paraphrase, and never the distilled `TOPIC` in its place.
- **Empirical signal > theoretical appeal.** A behavior with grounding evidence outranks a "sounds great" one without it.
- **Feasibility is a first-class criterion.** At every stage where a proposal is written or refined, *first carefully consider the quality, novelty, and feasibility of the proposal you just created*. *Ensure that the proposal does not require resources beyond what an academic lab could afford*, and that the experiments validating it are *simple and feasible*. *Do not make things overly complicated.*
- **Clarity is a check that can fail, not a matter of style.** *Ensure the proposal is clear and concise, and the JSON is in the correct format.* *Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.* *Clearly clarify how the proposal distinguishes from the existing literature.* *Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.* Any threshold without a stated basis, equivalence claim without a margin, or prediction without a direction fails this rule.
- **Report the undecidable band.** Every hypothesis has a range of outcomes its measurement cannot decide; say where that range is, and that a result inside it leaves the claim unsupported at the planned power. Reporting only pass/fail hides the band, it does not remove it.
- **One quantity, one number.** A threshold, margin, sample size, or budget holds a single value and unit everywhere it appears in `claim.json`; disagreement is repaired at every occurrence, never smoothed over in one field to match another.
- **Document everything.** Dead ends are as valuable as the headline results.
- **Be honest with the reviewer.** Include negative pilot results and failures in the review prompt.
- **Large file handling**: if Write fails on size, retry via Bash heredoc silently.

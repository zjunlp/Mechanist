---
name: auto-claim
description: "Workflow 1: Claim-stage pipeline, controlled by two orthogonal axes. BEHAVIOR_SOURCE selects the behavior stage: `given` (default; behavior taken from task.md and assumed to hold — no ideation, no novelty, no M0), `given-validation` (behavior taken from task.md but the experiment plan opens with an M0 phenomenon-validation gate), or `discovery` (mine a NEW behavior via /mechanism-behavior-discovery + full ideation: research-lit → idea-creator → novelty-check → impact-check → research-review → research-refine-pipeline, impact-first ranking; plan opens with M0). MECHANISM selects the mechanism stage: `discovery` (default; system routes — claim loads /mechanism-explore to shape direction) or `given` (user named the mechanism method/family in task.md — capture it and forward as CHOSEN_FAMILY, no routing). resource_fidelity:strict (exact models/datasets, no downscaling) is stamped iff BEHAVIOR_SOURCE=given AND MECHANISM=given (the reproduction combination). Always emits `idea-stage/IDEA_REPORT.md` + `refine-logs/{FINAL_PROPOSAL,EXPERIMENT_PLAN}.md`. Use when user says \"idea discovery pipeline\", \"找idea全流程\", \"从零开始找方向\", \"复现 task.md\", or wants the claim stage of /auto."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, AskUserQuestion, Skill, mcp__llm-chat__chat
---

# Workflow 1: Claim Stage — Behavior (given / given-validation / discovery) × Mechanism (given / discovery)

Orchestrate the claim stage for: **$ARGUMENTS**. Two orthogonal constants drive everything: **`BEHAVIOR_SOURCE`** (where the behavior comes from + whether it is validated) and **`MECHANISM`** (who picks the mechanism method).

## Overview

This skill chains sub-skills into a single automated pipeline. All combinations share Phases 0, 0.5, 1, 4.5, 5, and 5.5; they differ in how the claim(s) entering Phase 4.5 are produced (Phase 2 + the ideation Phases 3/3.5/4) and in what Phase 1.75 loads.

**Behavior stage — `BEHAVIOR_SOURCE`** decides the behavior origin, whether ideation runs, and whether the plan opens with an M0 phenomenon-validation gate:

- **`given`** (default) — the behavior is already specified in the direction / `task.md` and **assumed to hold**. Faithfully capture it (no ideation, no novelty, **no M0**) and go straight to the mechanism:
  ```
  /research-lit → faithful behavior capture (from task.md) → /research-refine-pipeline
  ```
- **`given-validation`** — the behavior is captured the same way (no mining, no ideation, no novelty) **but its existence is validated first**: the experiment plan opens with a hard **M0 gate** that the experiment stage runs before any mechanism compute.
  ```
  /research-lit → faithful behavior capture (from task.md) → /research-refine-pipeline (plan opens with M0)
  ```
- **`discovery`** — the behavior itself is mined: `/mechanism-behavior-discovery` sharpens a *new* candidate phenomenon, then full ideation generates and ranks mechanistic ideas; the plan opens with the **M0 gate** too.
  ```
  /research-lit → /idea-creator → /novelty-check → /impact-check → /research-review → /research-refine-pipeline
    (survey)      (brainstorm)    (verify novel)   (verify it     (critical feedback)  (refine method + plan)
                                                    matters)
  ```
  The final idea is selected by **combined impact + novelty, with impact weighted first** (a less-novel idea on an important problem outranks a novel idea nobody needs).

**Mechanism stage — `MECHANISM`** decides who picks the mechanism method:

- **`discovery`** (default) — the system routes. The claim stage loads `/mechanism-explore` (the domain-general strategy layer above `/mechanism-skills`) as a *reference* shaping the **hypothesis direction** (Phase 2) and **experiment plan** (Phase 4.5); the concrete family is chosen later by the experiment stage's `/mechanism-skills` routing.
- **`given`** — the user named the mechanism method/family in `task.md` (or the direction). Capture it (Phase 1.75) and record it in `FINAL_PROPOSAL.md` / `EXPERIMENT_PLAN.md` so the experiment stage commits it directly as `CHOSEN_FAMILY` — no routing, and `/mechanism-explore` is not needed to pick a direction. If no concrete mechanism method/family is named anywhere, stop with `[mechanism] mechanism:given requires a mechanism method/family in task.md or the direction — none found`.

`/mechanism-explore` and `/mechanism-behavior-discovery` are reference-only (principles, no executable phases, no new artifact).

**Resource-Fidelity Harness (the reproduction combination).** **Iff `BEHAVIOR_SOURCE = given` AND `MECHANISM = given`**, the claim stage captures the exact models / datasets / data sizes named in `task.md` as binding and writes `resource_fidelity: strict` into `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md`, so the experiment stage uses them as specified with **no cost-driven downscaling** (no smaller-model swap, no data subsetting). Every other combination leaves the marker unstamped (cost-aware). See Phase 2 and Phase 4.5.

The final deliverables are always `idea-stage/IDEA_REPORT.md` plus a refined proposal (`refine-logs/FINAL_PROPOSAL.md`) and experiment plan (`refine-logs/EXPERIMENT_PLAN.md`). `discovery` ranks generated ideas and pins the top one; `given` / `given-validation` enumerate the behavior/claims captured from `task.md` and route all of them into a single unified proposal and experiment plan.

## Constants

- **BEHAVIOR_SOURCE = `given`** — Behavior stage. `given` (default): the behavior is already specified in `task.md` and **assumed to hold** — Phase 2 faithfully captures it, the ideation Phases 3/3.5/4 are skipped, and the plan carries **no M0** gate. `given-validation`: same faithful capture (no mining, no ideation, no novelty), but Phase 4.5 opens the plan with an **M0 phenomenon-validation gate** so the experiment stage validates existence before any mechanism compute. `discovery`: Phase 1.75 first loads `/mechanism-behavior-discovery` to mine and *sharpen* a *new* candidate phenomenon (its five bars — Real / Non-obvious / Specific / Robust / Tractable — and its sharpening discipline), then the ideation Phases 2/3/3.5/4 generate + rank mechanistic ideas, and the plan opens with the **M0 gate** too. The claim only **assumes** the phenomenon (for `given-validation` / `discovery`); its real existence is tested by the experiment-stage M0 gate (`/auto-experiment` Phase 1.25), not at claim time. For `given` / `given-validation`, the behavior is taken from `task.md` when present, otherwise from the `$ARGUMENTS` direction (or a `given_behavior` the orchestrator clarified) — `task.md` is recommended but **not** required. The behavior must be *concrete*; a vague topic with no concrete behavior is handled by the Given-Behavior Comprehension Gate (orchestrator) and its backstop (Phase 1.75 / `agents/claim.md` step 0.6) — which switches to `discovery` or asks the user — **not** by a hard halt. Accepts `given` / `given-validation` / `discovery` (case-insensitive). When invoked via `/auto`, forwarded from `/auto`'s `BEHAVIOR_SOURCE` flag through `agents/claim.md`. Pilot-related constants below (`PILOT_*`, `MAX_PILOT_IDEAS`, `MAX_TOTAL_GPU_HOURS`) and `CHOSEN_IDEA` apply only to `BEHAVIOR_SOURCE=discovery` (ideation) and are ignored for `given` / `given-validation`.

- **MECHANISM = `discovery`** — Mechanism stage. `discovery` (default): the system routes the mechanism family — Phase 1.75 loads `/mechanism-explore` to shape the hypothesis direction (Phase 2) and experiment plan (Phase 4.5); the concrete family is picked later by the experiment stage's `/mechanism-skills` routing. `given`: the user named the mechanism method/family in `task.md` (or the direction) — Phase 1.75 captures it and Phase 4.5 records it (`chosen_mechanism: <method>`) in the proposal/plan so the experiment stage commits it directly as `CHOSEN_FAMILY` (no routing; `/mechanism-explore` is not loaded). A behavioral-only reproduction (no mechanism claim) may instead declare itself behavioral-only → `chosen_mechanism: not-applicable` (experiment commits `routing: not-applicable`). If `MECHANISM=given` but neither a named method nor a behavioral-only declaration is present, stop with `[mechanism] mechanism:given requires a named mechanism method/family OR an explicit behavioral-only declaration in task.md or the direction — none found`. Accepts `given` / `discovery` (case-insensitive). When invoked via `/auto`, forwarded from `/auto`'s `MECHANISM` flag through `agents/claim.md`. **Resource fidelity:** the harness marker `resource_fidelity: strict` is stamped **iff `BEHAVIOR_SOURCE=given` AND `MECHANISM=given`** (the reproduction combination); see Phase 2 / Phase 4.5.

- **PILOT_MAX_HOURS = 4** — Skip any pilot experiment estimated to take > N hours per GPU. Flag as "needs manual pilot" in the report. *(`BEHAVIOR_SOURCE=discovery` only.)*
- **PILOT_TIMEOUT_HOURS = 6** — Hard timeout: kill any running pilot that exceeds N hours. Collect partial results if available. *(`BEHAVIOR_SOURCE=discovery` only.)*
- **MAX_PILOT_IDEAS = 3** — Run pilots for at most N top ideas in parallel. Additional ideas are validated on paper only. *(`BEHAVIOR_SOURCE=discovery` only.)*
- **MAX_TOTAL_GPU_HOURS = 10** — Total GPU budget across all pilots. If exceeded, skip remaining pilots and note in report. *(`BEHAVIOR_SOURCE=discovery` only.)*

- **AUTO_PROCEED = true** — When `true` (default), every checkpoint **skips the `AskUserQuestion` UI call entirely** and proceeds with the recommended option — there is no timer and no waiting. When `false`, each checkpoint calls `AskUserQuestion` and blocks until the user responds (so an unattended run with `AUTO_PROCEED=false` can deadlock indefinitely; wrap with `timeout` externally if you need a hard cap).
- **RESUME = false** — When `true`, each phase checks if its primary artifact already exists non-empty and skips itself if so. Useful for picking up after a crash or for re-running only the missing phases. Default `false` = every phase always runs and overwrites prior artifacts. Resume never deletes pre-existing files.
- **REVIEWER_BACKEND = `llm-chat`** — External LLM reviewer via llm-chat MCP (model defers to `LLM_MODEL` env). Always ask the external reviewer for strict, high-rigor feedback. Each sub-skill (`/research-lit`, `/idea-creator`, `/novelty-check`, `/impact-check`, `/research-review`, `/research-refine-pipeline`) **declares the same default independently** — this constant is NOT forwarded by `/auto-claim`. To switch backend for a specific sub-skill (e.g., `oracle-pro` for GPT-5.4 Pro via Oracle MCP), pass `— reviewer: <name>` when invoking that sub-skill directly.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during Phase 1. When `false` (default), only fetches metadata. Passed through to `/research-lit`.
- **COMPACT = false** — When `true`, generate compact summary files for short-context models and session recovery. Writes `idea-stage/IDEA_CANDIDATES.md` (top 3-5 ideas only) at the end of this workflow. Downstream skills read this instead of the full `idea-stage/IDEA_REPORT.md`.
- **REF_PAPER = false** — Reference paper to base ideas on. Accepts: local PDF path, arXiv URL, or any paper URL. When set, the paper is summarized first (`idea-stage/REF_PAPER_SUMMARY.md`), then idea generation uses it as context. Combine with `base repo` for "improve this paper with this codebase" workflows.
- **CHOSEN_IDEA = 1** — *(`BEHAVIOR_SOURCE=discovery` only; ignored for `given` / `given-validation`.)* 1-based rank of the idea (from `idea-stage/IDEA_REPORT.md`'s Ranked Ideas section) that Phase 4.5 refines into `FINAL_PROPOSAL.md` + `EXPERIMENT_PLAN.md`. Default `1` = the top-ranked idea (current behavior). Set to `2`, `3`, … to refine a backup idea instead — used by `/auto`'s Claim Gate "switch <N>" branch (`agents/claim.md` forwards the value, and pre-deletes the prior proposal/plan so this skill's resume check sees them missing and re-runs Phase 4.5). When `CHOSEN_IDEA > 1`, Phase 4.5 rewrites only those two files; `IDEA_REPORT.md`, novelty checks, and external review (Phases 1–4) are kept intact since they are idea-agnostic at the ranked-list level. For `given` / `given-validation` there is no ranking and no selection — all captured behavior/claims are refined together — so the value is silently ignored (with a one-line warning if it was explicitly set).

> 💡 Standalone overrides: `/auto-claim — behavior-source: given, mechanism: given` (faithfully reproduce the claims in `task.md`), `/auto-claim "direction" — behavior-source: discovery`, `— ref-paper: https://arxiv.org/abs/2406.04329`, `— compact: true`, or `— chosen-idea: 2` (`behavior-source: discovery` only; re-refines onto idea #2, requires `IDEA_REPORT.md` to already exist non-empty).

## Pipeline

### Resume protocol (only when `RESUME = true`)

Skip entirely if `RESUME = false` (default).

When `true`, each phase below begins with a **skip-if-present** check. The protocol is uniform:

1. Test the phase's primary artifact with `[ -s <path> ]` (exists **and** non-empty).
2. If present: log `[resume] phase <N> skipped — <artifact> exists` and proceed to the next phase without invoking the sub-skill.
3. If absent or empty: run the phase normally.

Phase ↔ primary artifact mapping:

| Phase | Modes | Primary artifact (skip key) |
|---|---|---|
| 0.5 | both | `idea-stage/REF_PAPER_SUMMARY.md` |
| 1   | both | Side files `idea-stage/RESEARCH_LIT.md` (raw retrieval dump, audit-only) and `idea-stage/LANDSCAPE.md` (synthesized landscape, read from disk by Phase 2 in both modes) are written by `/research-lit`. Neither is a skip key — Phase 1 is gated jointly with Phase 2 (and Phase 3 in discovery) on `IDEA_REPORT.md`. If `IDEA_REPORT.md` is missing, Phase 1 re-runs and overwrites both side files fresh. |
| 1.75 | all | None — context-only load of `/mechanism-explore` (when `MECHANISM=discovery`) + `/mechanism-behavior-discovery` (when `BEHAVIOR_SOURCE=discovery`) + mechanism-method capture (when `MECHANISM=given`); no artifact. It always runs; resume never skips it (it is cheap and its guidance must be in context for Phase 2 / Phase 4.5). |
| Claim-production block (`discovery`: 1–3.5 / `given`·`given-validation`: 1–2) | all | `idea-stage/IDEA_REPORT.md` — if present non-empty, treat the whole block as a single skip unit and jump to Phase 4 (`discovery`) or Phase 4.5 (`given` / `given-validation`). |
| 4 | `BEHAVIOR_SOURCE=discovery` only | `idea-stage/IDEA_REPORT.md` containing a non-empty `## External Review` section — same file as the block above, but a finer-grained sub-check: Phase 4 only re-runs if the file exists yet has no `## External Review`. |
| 4.5 | all | `refine-logs/FINAL_PROPOSAL.md` **and** `refine-logs/EXPERIMENT_PLAN.md` (both required). **`discovery` override**: when `CHOSEN_IDEA != 1`, ignore this skip key and re-run Phase 4.5 unconditionally — the existing proposal/plan are scoped to the previously-chosen idea and would be silently kept stale otherwise. Standalone `discovery` callers should pre-clean with `rm -f refine-logs/FINAL_PROPOSAL.md refine-logs/EXPERIMENT_PLAN.md` (the orchestrator's `agents/claim.md` does this automatically); even without the pre-clean this override forces Phase 4.5 to re-run. `given` / `given-validation` have no equivalent override since there is no per-idea selection. |
| 5 | both | Always runs (cheap report rewrite that ensures the file reflects current state). |
| 5.5 | both | `idea-stage/IDEA_CANDIDATES.md` (only relevant when `COMPACT = true`). |

> **Why the claim-production block shares one skip key.** `LANDSCAPE.md` is intentionally not a skip key — a stale or partial landscape from an interrupted run is not trustworthy, so re-running Phase 1 to overwrite it cleanly is preferable to silently consuming it. The cost is re-doing retrieval when only a later phase failed; the benefit is that Phase 2 always reads a `LANDSCAPE.md` produced by the same successful Phase 1 within the current run.

Resume never deletes pre-existing files. If you want to force a phase to re-run, delete its primary artifact before invoking the skill.

### Phase 0: Load Research Brief (if available)

Before starting any other phase, check for a detailed research brief in the project:

1. Look for `task.md` in the project root (or path passed as `$ARGUMENTS`)
2. If found, read it and extract:
   - Problem statement and context
   - Claims
   - Resources 
   - Constraints (compute, data, timeline, venue)
   - What the user already tried / what didn't work
   - Domain knowledge and non-goals
   - Other tips 
   - Existing results (if any)
3. Use this as the primary context for all subsequent phases — it replaces the one-line prompt
4. If both `task.md` and a one-line `$ARGUMENTS` exist, merge them (brief takes priority for details, argument sets the direction)


### Phase 0.5: Reference Paper Summary (when REF_PAPER is set)

**Skip entirely if `REF_PAPER` is `false`.**

Summarize the reference paper before searching the literature:

1. **If arXiv URL** (e.g., `https://arxiv.org/abs/2406.04329`):
   - Invoke `/arxiv "ARXIV_ID" — download` to fetch the PDF
   - Read the first 5 pages (title, abstract, intro, method overview)

2. **If local PDF path** (e.g., `papers/reference.pdf`):
   - Read the PDF directly (first 5 pages)

3. **If other URL**:
   - Fetch and extract content via WebFetch

4. **Generate `idea-stage/REF_PAPER_SUMMARY.md`**:

```markdown
# Reference Paper Summary

**Title**: [paper title]
**Authors**: [authors]
**Venue**: [venue, year]

## What They Did
[2-3 sentences: core method and contribution]

## Key Results
[Main quantitative findings]

## Limitations & Open Questions
[What the paper didn't solve, acknowledged weaknesses, future work suggestions]

## Potential Improvement Directions
[Based on the limitations, what could be improved or extended?]

## Codebase
[If `base repo` is also set: link to the repo and note which parts correspond to the paper]
```

**🚦 Checkpoint:** Present the summary to the user:

```
📄 Reference paper summarized:
- Title: [title]
- Key limitation: [main gap]
- Improvement directions: [2-3 bullets]

Proceeding to literature survey with this as context.
```

Phase 1 and Phase 2 will use `idea-stage/REF_PAPER_SUMMARY.md` as additional context — `/research-lit` searches for related and competing work, `/idea-creator` generates ideas that build on or improve the reference paper.

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape:

```
/research-lit "$ARGUMENTS"
```

**What this does:**
- Search Zotero, Obsidian, local PDFs, the web, and the cloud mechanic-db SEARCH service (via the skill `/mechanic-db-search`) for relevant papers
- Build a landscape map: sub-directions, approaches, open problems
- Identify structural gaps and recurring limitations
- Output two files: `idea-stage/RESEARCH_LIT.md` (raw retrieval dump, audit-only) and `idea-stage/LANDSCAPE.md` (synthesized landscape — Phase 2 reads this from disk)

**🚦 Checkpoint:** Present the landscape summary to the user. Ask:

```
📚 Literature survey complete. Here's what I found:
- [key findings, gaps, open problems]

Does this match your understanding? Should I adjust the scope before proceeding?
```

Gating rule (no timer; AUTO_PROCEED controls whether the UI prompt is shown at all):
- **AUTO_PROCEED=true** (default) — skip the prompt entirely and proceed to Phase 2 (idea generation when `BEHAVIOR_SOURCE=discovery`; faithful behavior capture when `given` / `given-validation`).
- **AUTO_PROCEED=false** — call `AskUserQuestion`, block until the user answers:
  - **approves** → proceed to Phase 2.
  - **requests changes** (e.g., "focus more on X", "ignore Y", "too broad") → refine the search with updated queries, re-run `/research-lit` with adjusted scope, and present again. Repeat until the user is satisfied.

### Phase 1.75: Mechanism Strategy Load + Behavior/Mechanism Capture

This phase loads strategy into context and captures user-pinned inputs; it writes **no artifact**. It is a *reference* step — its job is to put the relevant strategy skills in context so Phase 2 (hypothesis direction) and Phase 4.5 (experiment plan) can apply them, and to record a user-given mechanism method when `MECHANISM=given`. Three independent decisions:

**(a) Behavior strategy — branch on `BEHAVIOR_SOURCE`:**

- `given` / `given-validation` — **precondition:** the behavior must be **concretely specified** (a specific, falsifiable model-observable output pattern, ideally with its triggering condition) in the direction / `task.md`, or supplied as a `given_behavior` resolved by the orchestrator's Given-Behavior Comprehension Gate. If only a bare topic / research direction is present (e.g. *"explore the mechanics of LLM beliefs"*) with no concrete behavior and no `given_behavior`, do **not** let Phase 2 silently invent one and do **not** silently fall back to `discovery` — apply the comprehension backstop (`agents/claim.md` step 0.6): **always `AskUserQuestion`** (switch-to-discovery, recommended / specify-behavior) and **wait**, regardless of `AUTO_PROCEED` (a vague given direction is a decision only the user can make — no timeout, no auto-fallback). On switch-to-discovery, proceed as `BEHAVIOR_SOURCE=discovery` below. `/mechanism-behavior-discovery` is **not** loaded for `given` / `given-validation` (the behavior is taken from `task.md`, not mined). Log `[behavior-strategy] <given|given-validation> — behavior taken from task.md (no mining)`.
- `discovery` — invoke `/mechanism-behavior-discovery` and read its `SKILL.md` in full (the standard for finding, sharpening, and validating a *new* behavioral phenomenon — the five bars Real / Non-obvious / Specific / Robust / Tractable, the discovery strategies, and the validation discipline). It decides *what behavior is worth explaining*. Log `[behavior-strategy] discovery — loaded /mechanism-behavior-discovery`.

**(b) Mechanism strategy — branch on `MECHANISM`:**

- `discovery` (default) — invoke `/mechanism-explore` via the Skill tool and read its `SKILL.md` in full; the strategy shapes *how to explain* the behavior (the hypothesis direction in Phase 2 and the experiment plan in Phase 4.5). The concrete family is chosen later by the experiment stage. Log `[mechanism-strategy] discovery — loaded /mechanism-explore`.
- `given` — do **not** load `/mechanism-explore` (no direction to pick — the method is user-given). Two acceptable inputs:
  - **A named mechanism method/family** in `task.md` (or the direction) → capture it verbatim and hold it as `chosen_mechanism`; Phase 4.5 records it so the experiment stage commits it as `CHOSEN_FAMILY`.
  - **An explicit behavioral-only declaration** (the work makes *no* mechanism claim — e.g. a pure behavioral-claim reproduction such as verifying accuracy gaps / asymmetries) → set `chosen_mechanism: not-applicable`; Phase 4.5 records it, the orchestrator forwards `CHOSEN_FAMILY=not-applicable`, and the experiment stage commits `routing: not-applicable` and runs no mechanism milestone.

  Only if **neither** a named method **nor** a behavioral-only declaration is present, stop with `[mechanism] mechanism:given requires a named mechanism method/family OR an explicit behavioral-only declaration in task.md or the direction — none found`. Log `[mechanism-strategy] given — captured chosen_mechanism="<method | not-applicable>"`.

Hold the loaded guidance in context for the rest of the run — do **not** copy it into any output file.

What the loaded strategy is used for (advisory — it never relaxes `/idea-creator`'s novelty / feasibility / pilot filtering):

- **Phase 2 (hypothesis direction)** — frame candidate ideas as *falsifiable mechanistic hypotheses* (name the implicated internal object and the predicted causal relation) with at least one "boring" null (memorization / surface feature / shortcut), and favor ideas on a climbable ladder of evidence. When `BEHAVIOR_SOURCE = discovery`, the upstream step first surfaces and *sharpens* candidate phenomena (per `/mechanism-behavior-discovery`); the claim **assumes** the chosen phenomenon exists and attaches the mechanistic hypothesis — its *actual* existence is tested later by the experiment-stage M0 gate, not asserted here.
- **Phase 4.5 (experiment plan)** — shape the plan to climb the ladder of evidence: a cheap correlational/attribution screen to localize candidates → a causal intervention (ablation / patching / steering) to confirm the survivors → matched-control + off-target + confound checks for specificity. Each intervention milestone records the expected **sign**, **magnitude / dose-response**, and a **specificity control**. When `BEHAVIOR_SOURCE ∈ {given-validation, discovery}`, the plan **opens with a phenomenon-validation gate (M0)**; the experiment stage runs M0 first and proceeds to the mechanism milestones only on a four-state verdict of `established` / `conditional` (see Phase 4.5 and `/auto-experiment` Phase 1.25). `BEHAVIOR_SOURCE = given` has **no M0**.

### Phase 2: Produce the Claims to Verify

This phase writes `idea-stage/IDEA_REPORT.md`, the list of claims that Phase 4.5 will refine into a proposal and experiment plan. The behavior depends on `BEHAVIOR_SOURCE`.

*In `BEHAVIOR_SOURCE = discovery`* — idea generation, filtering, and pilots.

Invoke `/idea-creator` with the landscape context (and `idea-stage/REF_PAPER_SUMMARY.md` if available):

```
/idea-creator "$ARGUMENTS"
```

**What this does:**
- If `idea-stage/REF_PAPER_SUMMARY.md` exists, include it as context — ideas should build on, improve, or extend the reference paper.
- Read `idea-stage/LANDSCAPE.md` from disk (written by Phase 1 / `/research-lit`), then brainstorm 8–12 concrete ideas via the external LLM reviewer (llm-chat).
- Filter by feasibility, compute cost, quick novelty search.
- Deep-validate top ideas (full novelty check + devil's advocate).
- Run parallel pilot experiments on available GPUs (top ideas, up to `MAX_PILOT_IDEAS`).
- Rank by empirical signal.
- Output `idea-stage/IDEA_REPORT.md` with a `## Ranked Ideas` section.

**Apply the Phase 1.75 mechanism strategy.** When `MECHANISM=discovery`, pass `/mechanism-explore`'s framing into `/idea-creator` so each generated idea is stated as a falsifiable mechanistic hypothesis (internal object + predicted causal relation + at least one boring null), and bias ranking toward ideas with a climbable ladder of evidence. (When `MECHANISM=given`, no `/mechanism-explore` direction was loaded — the captured `chosen_mechanism` is the method, so frame ideas around testing the behavior with that method.) `BEHAVIOR_SOURCE = discovery` always first applies `/mechanism-behavior-discovery` to surface and *sharpen* candidate *phenomena* from the landscape (state each crisply per the five bars and screen plausibility) — the claim **assumes** the chosen phenomenon exists and attaches a mechanistic hypothesis; the phenomenon's actual existence is tested by the M0 gate in the experiment stage, not claimed here. This shapes idea *framing* only — novelty, feasibility, and pilot filtering are unchanged.

**🚦 Checkpoint:** Present the ranked ideas to the user.

```
💡 Generated X ideas, filtered to Y, piloted Z. Top results:

1. [Idea 1] — Pilot: POSITIVE (+X%)
2. [Idea 2] — Pilot: WEAK POSITIVE (+Y%)
3. [Idea 3] — Pilot: NEGATIVE, eliminated

Which ideas should I validate further? Or should I regenerate with different constraints?
```

Gating rule (no timer; AUTO_PROCEED controls whether the UI prompt is shown at all):
- **AUTO_PROCEED=true** (default) — skip the prompt entirely and proceed to Phase 3 with the top-ranked ideas.
- **AUTO_PROCEED=false** — call `AskUserQuestion`, block until the user answers:
  - **picks ideas** → proceed to Phase 3 with the chosen set.
  - **unhappy with all ideas** → collect feedback ("what's missing?", "what direction do you prefer?"), update the prompt with the user's constraints, and re-run Phase 2. Repeat until the user selects at least 1 idea.
  - **wants to adjust scope** → go back to Phase 1 with a refined direction.

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`* — faithful behavior/claim capture from `task.md`.

No idea-generation sub-skill is invoked. The orchestrator captures the behavior (and any claims stated about it) directly from `task.md`, using `idea-stage/LANDSCAPE.md` only as supporting context (e.g., to identify standard baselines, datasets, or metric definitions referenced by the behavior). The landscape never overrides what `task.md` says. `given` and `given-validation` capture identically — they differ only downstream in Phase 4.5 (given-validation opens the plan with M0; given does not).

**Extraction rules** — be faithful, not literal. The point is to turn the claims as the user wrote them into well-formed, individually verifiable predicates, without altering their meaning.

| Allowed | Forbidden |
|---|---|
| Split one paragraph into multiple independent verifiable sub-claims when it bundles several. | Changing the semantics, direction, or strength of any claim. |
| Merge duplicated or restated claims from different parts of `task.md` into one. | Adding assertions that `task.md` does not state or clearly imply. |
| Rewrite vague or colloquial phrasing into a measurable predicate (subject, target, metric, direction made explicit). | Dropping any claim that `task.md` explicitly states. |
| Add structural fields (Hypothesis, Measurable predicate, Expected direction) derived strictly from `task.md`'s wording. | "Critically tightening" a claim's scope to make it easier to verify — that is Phase 4.5's job on the *testing method*, not Phase 2's job on the *claim*. |

Every extracted claim must carry an `Original` field with the exact source excerpt, so any later phase can audit faithfulness end-to-end.

**Resource capture.** Alongside each captured behavior/claim, record the experimental resources `task.md` specifies — model(s) (full id / size), dataset(s), and required data size / split (`used_n`). **In the reproduction combination (`BEHAVIOR_SOURCE=given` + `MECHANISM=given`) these are *binding*** (the downstream plan and runs must use them as specified, no cost-driven substitution); Phase 4.5 stamps them as `resource_fidelity: strict` and the experiment stage enforces them. In every other combination they are recorded as the user's **preferred** resources and remain cost-aware — but "cost-aware" is *minimize cost **subject to** the science, within the declared budget*, **not** "always pick the cheapest". Read any GPU / compute budget declared in `task.md`: **when the declared budget covers the user's preferred full-scale model / data, plan at that full scale** (set `used_n = available_n`, use the named model at full size) rather than a cheaper default — the experiment stage may only scale them **down** when the budget genuinely does not cover the full run, and then it stops and surfaces it rather than silently downscaling (see `/auto-experiment` GPU-budget rule). When no budget is declared, stay cost-aware but still avoid gratuitous downscaling of the user's named resources — record them at full scale unless a cheaper screen is *scientifically* (ladder-of-evidence), not merely cost-, justified. If `task.md` names them globally rather than per-claim, capture them once in a top-level `## Resources` block (label it `(binding)` only under the reproduction combination) and reference it. If a required resource is unspecified in `task.md`, record it as `unspecified — to be resolved in Phase 4.5` rather than inventing a cheaper default.

**Output schema** — `idea-stage/IDEA_REPORT.md` for `given` / `given-validation`:

```markdown
# Idea Report — Captured Behavior

**Behavior-source**: <given | given-validation>
**Mechanism**: <given | discovery>
**Claim source**: task.md (faithful capture)
**Date**: [today]

## Claims to Verify

### Claim 1: <short title>

**Original (verbatim excerpt from task.md):**
> <quoted source text>

**Extracted statement**: <cleaned, measurable form>
**Hypothesis**: H1 — <one sentence>
**Measurable predicate**: <metric on dataset under condition satisfies …>
**Expected direction**: <up | down | equal | threshold>
**Resources (binding)**: model(s): <exact id / size>; dataset(s): <name>; used_n: <required size / split> — *(exact, as task.md specifies; "unspecified — resolve in Phase 4.5" if absent)*
**Status**: pending verification
**Notes**: <e.g., "split from §2 ¶3"; "merged with the duplicate at §4"; "metric inferred from task.md's evaluation paragraph">

### Claim 2: <short title>
…
```

**🚦 Checkpoint:** Present the extracted claims to the user.

```
🧾 Extracted N claim(s) from task.md:

1. [Claim 1 title] — [one-line measurable predicate]
2. [Claim 2 title] — [one-line measurable predicate]
…

Did I miss, merge, or misread any claim? If so, point it out and I'll re-extract.
```

Gating rule:
- **AUTO_PROCEED=true** (default) — skip the prompt entirely and proceed to Phase 4.5 with all captured behavior/claims (Phases 3 and 4 are skipped for `given` / `given-validation`).
- **AUTO_PROCEED=false** — call `AskUserQuestion` and block:
  - **approves** → proceed to Phase 4.5.
  - **flags a missed / wrong / over-merged claim** → re-capture with the user's correction and present again.

### Phase 3: Deep Novelty Verification *(`BEHAVIOR_SOURCE=discovery` only)*

**Skip entirely unless `BEHAVIOR_SOURCE = discovery`.** `given` / `given-validation` do not perform novelty checks — the behavior comes from `task.md` and is taken as given, not assessed for prior-art uniqueness.

For each top idea (positive pilot signal), run a thorough novelty check:

```
/novelty-check "[top idea 1 description]"
/novelty-check "[top idea 2 description]"
```

**What this does:**
- Multi-source literature search (arXiv, Scholar, Semantic Scholar)
- Cross-verify with the external LLM reviewer
- Check for concurrent work (last 3-6 months)
- Identify closest existing work and differentiation points

**Update `idea-stage/IDEA_REPORT.md`** with deep novelty results. Eliminate any idea that turns out to be already published.

### Phase 3.5: Deep Impact Verification *(`BEHAVIOR_SOURCE=discovery` only)*

**Skip entirely unless `BEHAVIOR_SOURCE = discovery`.** `given` / `given-validation` take the behavior in `task.md` as given and do not weigh its importance.

For each idea that survived novelty (Phase 3), run an impact check on the **problem/behavior** it studies:

```
/impact-check "[top idea 1 — behavior/problem + hypothesis]"
/impact-check "[top idea 2 — behavior/problem + hypothesis]"
```

**What this does:** judges whether the studied problem/behavior is *important* — solves a real problem, is likely to be used/cited, could shift a field's direction, helps applications/industry/society/cross-disciplinary work, or reveals an important phenomenon even with a simple method. Outputs `Impact: X/10` + `PROCEED / PROCEED WITH CAUTION / DEPRIORITIZE`.

**Update `idea-stage/IDEA_REPORT.md` and re-rank.** Add an `Impact: X/10` line to each surviving idea, then **re-order the `## Ranked Ideas` list by impact first, novelty second** — impact dominates the ranking and novelty only breaks ties. Move low-impact ideas down (deprioritize); eliminate one only if its impact is clearly negligible. This impact-first order is exactly what Phase 4.5's `CHOSEN_IDEA` indexes into, so the top-ranked idea is the one that best combines importance and newness.

### Phase 4: External Critical Review *(`BEHAVIOR_SOURCE=discovery` only)*

**Skip entirely unless `BEHAVIOR_SOURCE = discovery`.** `given` / `given-validation` do not run a separate external review at this stage — `/research-refine-pipeline` (Phase 4.5) already performs its own iterative external review of the testing method and experiment plan, which is the right place to scrutinize how each claim will actually be verified.

For the surviving top idea(s), get brutal feedback:

```
/research-review "[top idea with hypothesis + pilot results]"
```

**What this does:**
- The external LLM reviewer acts as a senior reviewer (NeurIPS/ICML level)
- Scores the idea, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

**Update `idea-stage/IDEA_REPORT.md`** with reviewer feedback and revised plan.

### Phase 4.5: Method Refinement + Experiment Planning

**Step 0 — Resolve what to refine.** The behavior depends on `BEHAVIOR_SOURCE`.

*In `BEHAVIOR_SOURCE = discovery`* (uses the `CHOSEN_IDEA` constant, default `1`):

1. Open `idea-stage/IDEA_REPORT.md`'s `## Ranked Ideas` section and enumerate the surviving (non-eliminated) ideas in rank order (this order is the impact-first, novelty-second ranking written by Phase 3.5). The N-th surviving entry corresponds to `CHOSEN_IDEA = N`.
2. If `CHOSEN_IDEA > number of surviving ideas`, log `[chosen-idea] requested N=<N> but only <K> ideas survived ranking — falling back to N=1` and use idea #1 (the top idea). This guards against an orchestrator forwarding a stale rank after eliminations.
3. Extract that idea's title, hypothesis, pilot results, and reviewer feedback. These four things feed `/research-refine-pipeline` below.
4. Log `[chosen-idea] refining idea #<N> — "<title>"` so the run history is explicit about which backup was picked when `N > 1`.

When `CHOSEN_IDEA != 1`, also confirm that the prior `refine-logs/FINAL_PROPOSAL.md` + `refine-logs/EXPERIMENT_PLAN.md` are absent (`agents/claim.md` deletes them before invoking this skill; standalone callers must pre-clean manually). If they are present, refuse to overwrite silently: log `[chosen-idea] N=<N> but stale proposal/plan present — refusing to silently overwrite; delete refine-logs/FINAL_PROPOSAL.md and refine-logs/EXPERIMENT_PLAN.md before re-invoking` and stop.

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`*:

1. Open `idea-stage/IDEA_REPORT.md`'s `## Claims to Verify` section and load **all** captured behavior/claims. There is no ranking step and no selection — every one is carried forward. If `CHOSEN_IDEA` was explicitly set, log `[chosen-idea] CHOSEN_IDEA applies only to BEHAVIOR_SOURCE=discovery and is being ignored` and continue.
2. Build the refinement input as: the full claim list (each with its `Original` excerpt, `Extracted statement`, `Hypothesis`, `Measurable predicate`, and `Expected direction`) plus the landscape context from `idea-stage/LANDSCAPE.md`. There are no pilot results and no external-review feedback to attach — `/research-refine-pipeline` refines the **testing method and experiment plan around the behavior/claims**, never the behavior/claims themselves.
3. Log `[capture] refining unified proposal covering <N> behavior/claim(s)`.

**Step 1 — Refine.** Invoke `/research-refine-pipeline` with the input from Step 0.

*In `BEHAVIOR_SOURCE = discovery`*:

```
/research-refine-pipeline "[idea #CHOSEN_IDEA: title + description + pilot results + reviewer feedback]"
```

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`*:

```
/research-refine-pipeline "[N behavior/claims — each with title, original excerpt, extracted statement, hypothesis, measurable predicate, expected direction; plus landscape context from idea-stage/LANDSCAPE.md]"
```

**What `/research-refine-pipeline` does:**
- Freeze a **Problem Anchor** to prevent scope drift. For `discovery` the anchor is the idea's problem statement; for `given` / `given-validation` the anchor is the set of behavior/claims as captured in Phase 2 — they themselves never move.
- Iteratively refine the **method / testing approach** via external LLM review (up to 5 rounds, until score ≥ 9). For `given` / `given-validation` this refines only *how* to test (controls, ablations, metric choice, statistical power), never the behavior/claims.
- Generate a claim-driven experiment roadmap with ablations, budgets, and run order. For `given` / `given-validation` every milestone is tagged with which behavior/claim(s) it covers.
- **(Mechanism milestones — ladder of evidence, from the Phase 1.75 strategy):** shape the roadmap to climb the ladder of evidence — a cheap correlational/attribution screen to localize candidates → a causal intervention (ablation / patching / steering) to confirm the survivors → matched-control + off-target + confound milestones for specificity — and have each intervention milestone record the expected sign, magnitude / dose-response, and its specificity control. Because the concrete mechanism **submethod is not chosen until the experiment stage** (`/auto-experiment` Phase 1.5), any milestone field whose correct value depends on that submethod — typically `n_pairs`, intervention `sites`, the exact effect `metric`, and the per-run GPU-hours estimate — is necessarily provisional here. Tag each such milestone with a `method_sensitive: [<field>, ...]` line (English machine field, written verbatim regardless of report language) so the experiment stage knows which fields it may re-bind at routing time without it counting as a plan rewrite. This is omitted **only under `resource_fidelity: strict`** (the reproduction combo `given`+`given`), where these values are pinned exact and must **not** carry `method_sensitive` (see the strict bullet below). Every cost-aware combination keeps `method_sensitive`.
- **(Mechanism stamp — branch on `MECHANISM`):**
  - When **`MECHANISM=discovery`**, stamp a lightweight `mechanism_strategy:` block into the **top metadata** of `refine-logs/EXPERIMENT_PLAN.md` (and mirror it verbatim into `refine-logs/FINAL_PROPOSAL.md`) capturing the strategic decision taken from `/mechanism-explore` — which of the six research directions (Location / Causal Intervention / Tuning & Editing / Formation Tracing / Unit Interpretation / Decision Auditing) the plan pursues, **in execution order**, plus the directions deliberately **not** pursued with a one-line reason each. This is the audit anchor for the strategy decision, which otherwise evaporates when the claim agent's context closes (the `/mechanism-explore` skill itself writes no artifact). Shape (English machine fields; the free-text reasons follow the report language):

    ```yaml
    mechanism_strategy:
      directions: [Location, Causal Intervention]   # in execution order
      rejected:
        - Tuning & Editing — <one-line why not>
        - Formation Tracing — <one-line why not>
      note: <one line tying the chosen directions back to this project's claim(s)>
    ```
  - When **`MECHANISM=given`**, no `/mechanism-explore` direction was loaded, so stamp `mechanism_strategy: n/a` (skip the block) **and** stamp `chosen_mechanism: <the method/family captured in Phase 1.75, or `not-applicable` for a behavioral-only reproduction>` into the top metadata of both files. The orchestrator reads `chosen_mechanism` and forwards it to the experiment stage as `CHOSEN_FAMILY` — committing the named family directly (Phase 1.5 Mode B) with no routing, or `routing: not-applicable` when the value is `not-applicable`.
- **(Phenomenon-validation gate M0 — `BEHAVIOR_SOURCE ∈ {given-validation, discovery}`):** the claim only **assumes** the phenomenon exists; whether it is *real* is tested in the experiment stage, not here. So the roadmap's **first milestone** is a hard gate that **must carry the machine marker `kind: phenomenon-validation`** (the title may be phrased / localized freely — the experiment stage detects it by this field, never by the title). With an explicit pass criterion:
  - reproduces across **paraphrase, seed, and decoding settings** (not one exact string);
  - **confounds controlled** (length, token frequency, position, format, label identity, few-shot leakage);
  - **statistical reality** — sample size large enough to clear noise (honor `task.md` / project minimums; ≥ ~50 by default), with variability reported, not a single number;
  - the **trivial-explanation check** ruled out (tokenizer / sampling / eval-bug).
  All mechanism milestones (M1…Mn) **declare `depends_on: [M0]`**. The experiment stage (`/auto-experiment` Phase 1.25) runs M0 **first** and branches on a **four-state verdict**: `established` → run the mechanism milestones; `conditional` → restrict mechanism analysis to the conditions where the phenomenon holds (runtime scoping — the experiment stage does **not** rewrite this plan), and tag the claim `conditional`; `not-established` → stop the pipeline and write a **negative-result** report (skip verify + iteration); `inconclusive` (M0 test itself broken/underpowered) → fix & re-run M0 at the script/run level, never run mechanism on an untested phenomenon. **`BEHAVIOR_SOURCE = given` produces NO M0** — the behavior is taken as already validated by prior work, so the plan goes straight to the mechanism milestones, and those milestones **must NOT declare `depends_on: [M0]`** (there is no M0 to wait on — a dangling `depends_on: [M0]` would deadlock the queue). The M0 milestone + `depends_on: [M0]` rule above applies to `given-validation` and `discovery` only.
- **(Resource-Fidelity Harness — reproduction combo `given`+`given` only):** **iff `BEHAVIOR_SOURCE=given` AND `MECHANISM=given`**, the plan must use the **exact** models / datasets / data sizes captured in Phase 2, at the specified scale. Forbidden in the plan: substituting a smaller / cheaper model, subsetting or down-sampling the data, or dropping a must-run experiment to save compute. Stamp `resource_fidelity: strict` into the top metadata of both `FINAL_PROPOSAL.md` and `EXPERIMENT_PLAN.md`, and set each milestone's planned `used_n` to the full specified amount. The experiment stage reads this marker and enforces the harness downstream. Every other combination leaves the marker unstamped (cost-aware).
- Output: `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/EXPERIMENT_TRACKER.md`.

**`EXPERIMENT_TRACKER.md` ownership (planning level).** Phase 4.5 writes the tracker as a **plan-level table**: one row per planned run, with `Status` set to `pending` and `Notes` / result columns empty. The file is **not** rewritten downstream; `/auto-experiment` Phase 5 *updates rows in place* (flips `Status` from `pending` → `running` → `done` / `failed` and fills in result/notes columns) and *appends rows* only when Phase 5.6 plans new ablations. `/auto-iteration-loop` does not touch this file at all — iteration-round runs live under `runs/iteration_round_<N>/` and are tracked in `review-stage/AUTO_REVIEW.md` instead. This split keeps the plan-driven audit trail (this file) separate from the iteration-driven audit trail (the review log).

**`EXPERIMENT_PLAN.md` shape (queue-aware).** Each milestone block in `EXPERIMENT_PLAN.md` MAY declare two queue-related fields so `/auto-experiment` Phase 4.0 can route to `/experiment-queue` instead of `/run-experiment`:

- `depends_on: [<milestone-name>, ...]` — this milestone's runs must wait until every listed upstream milestone is `completed` before launching. Use for teacher → student chains, baseline → ablation chains, or any phase where a downstream run needs an upstream artifact (checkpoint, dataset, calibration result). The names refer to other milestone blocks in the same `EXPERIMENT_PLAN.md`.
- `grid: { <param-name>: [<value>, <value>, ...], ... }` — Cartesian-product expansion. Each combination produces one run with the params substituted via `${param-name}` placeholders into the milestone's `cmd:` template. Use for multi-seed sweeps (e.g., `grid: { seed: [42, 200, 201], n_hidden: [64, 128, 256], n_train_subset: [50000, 150000, 500000] }` → 27 runs). When `grid:` is present, the milestone's `cmd:` is treated as a template (rather than a literal command) and `id:` may also be a template (e.g., `s${seed}_N${n_hidden}_n${n_train_subset}`).
- `kind: phenomenon-validation` — **stable machine marker** identifying the M0 phenomenon-validation gate (`BEHAVIOR_SOURCE ∈ {given-validation, discovery}` only). This is the **canonical signal** `/auto-experiment` Phase 1.25 keys on — **not** the milestone's title. The marker is an English machine field (per the Output-language protocol) and must be written verbatim regardless of the report language, so the title heading may be phrased / localized freely. A `given-validation` / `discovery` plan has exactly one `kind: phenomenon-validation` milestone (M0); `given` plans have none.
- `method_sensitive: [<field>, ...]` — **per intervention milestone.** Lists the milestone fields whose correct value depends on the mechanism submethod that is bound at `/auto-experiment` Phase 1.5 (typically `n_pairs`, `sites`, `metric`, `gpu_hours`). It licenses the experiment stage to re-bind those fields at routing/commit time and record the delta in `MECHANISM_ROUTING.md` — **without** rewriting this plan (see `/auto-experiment` Phase 1.5 "Plan reconciliation"). Omit entirely under `resource_fidelity: strict` (the reproduction combo pins these exact); kept in every cost-aware combination.

In addition to the per-milestone fields above, `EXPERIMENT_PLAN.md` carries top-metadata machine markers stamped by Phase 4.5: `resource_fidelity: strict` (reproduction combo only — the harness switch), `mechanism_strategy:` (the strategic-direction block above when `MECHANISM=discovery`; `n/a` when `MECHANISM=given`), and `chosen_mechanism: <method>` (only when `MECHANISM=given` — the user's committed mechanism family).

A milestone with **either** `depends_on` or `grid` (or `≥10` listed runs even without those fields) triggers `/auto-experiment` Phase 4.B (queue dispatch). See `/auto-experiment` "Phase 4.0: Route by milestone size and dependencies" for the precise routing table.

Example queue-friendly milestone block:

```markdown
### M2: Multi-seed main method
**Depends on**: M1 (baselines)
**Grid**:
  seed: [42, 200, 201]
  n_hidden: [64, 128, 256, 512]
  n_train_subset: [50000, 150000, 500000]
**Cmd template**: `python run_method.py --seed ${seed} --n_hidden ${n_hidden} --n_train_subset ${n_train_subset} --backbone softmax --K 500 --L 96`
**Expected output (template)**: `results/main_N${n_hidden}_seed${seed}_n${n_train_subset}.json`
**Priority**: MUST-RUN
**Estimated GPU-hours per run**: 1.5h
```

This produces 36 runs and routes to `/experiment-queue` automatically. For a small milestone (≤ 5 explicit runs, no `depends_on`, no `grid`), keep the legacy shape — `/auto-experiment` Phase 4.A handles it via per-run `/run-experiment` dispatches.

**🚦 Checkpoint:** Present the refined proposal summary.

*In `BEHAVIOR_SOURCE = discovery`*:

```
🔬 Method refined and experiment plan ready:
- Problem anchor: [anchored problem]
- Method thesis: [one sentence]
- Dominant contribution: [what's new]
- Must-run experiments: [N blocks]
- First 3 runs to launch: [list]

Proceed to implementation? Or adjust the proposal?
```

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`*:

```
🔬 Verification approach refined and experiment plan ready:
- Claims covered: [N claims, listed by title]
- Testing approach: [one sentence on how the suite verifies them]
- Must-run experiments: [N blocks, one or more per claim]
- First 3 runs to launch: [list]

Proceed to implementation? Or adjust the verification plan?
```

- **User approves** (or `AUTO_PROCEED = true`) → proceed to Phase 5 (Final Report).
- **User requests changes** → pass feedback to `/research-refine` for another round.

### Phase 5: Final Report

Finalize `idea-stage/IDEA_REPORT.md` with all accumulated information. The template depends on `BEHAVIOR_SOURCE`.

*In `BEHAVIOR_SOURCE = discovery`*:

```markdown
# Idea Discovery Report

**Direction**: $ARGUMENTS
**Behavior-source**: discovery
**Mechanism**: <given | discovery>
**Date**: [today]
**Pipeline**: research-lit → idea-creator → novelty-check → impact-check → research-review → research-refine-pipeline

## Executive Summary
[2-3 sentences: best idea, key evidence, recommended next step]

## Literature Landscape
[from Phase 1]

## Ranked Ideas
[from Phase 2, updated with Phase 3-4 results]

### 🏆 Idea 1: [title] — RECOMMENDED
- Pilot: POSITIVE (+X%)
- Impact: X/10 — why it matters: [importance + who would care] (ranked first)
- Novelty: CONFIRMED (closest: [paper], differentiation: [what's different])
- Reviewer score: X/10
- Next step: route to mechanism family (/mechanism-skills) → implement full experiment (/auto-experiment) → /auto-iteration-loop

### Idea 2: [title] — BACKUP
...

## Eliminated Ideas
[ideas killed at each phase, with reasons]

## Refined Proposal
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Next Steps
- [ ] /mechanism-skills to route the method to a concrete mechanism family + submethod (Workflow 1.25, emits `refine-logs/MECHANISM_ROUTING.md`)
- [ ] /auto-experiment to implement and deploy from the routing + plan (Workflow 1.5)
- [ ] /auto-verify to stress-test the resulting claims (Workflow 1.75)
- [ ] /auto-iteration-loop to iterate until submission-ready (Workflow 2)
- [ ] Or invoke /auto for the autonomous idea → routing → experiments → verify → review chain
```

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`*:

```markdown
# Captured-Behavior Report

**Direction**: $ARGUMENTS (supplementary scope only — behavior/claims are sourced from task.md)
**Behavior-source**: <given | given-validation>
**Mechanism**: <given | discovery>
**Date**: [today]
**Pipeline**: research-lit → faithful behavior capture → research-refine-pipeline

## Executive Summary
[2-3 sentences: which claims will be verified, what the unified proposal covers, what to run first]

## Literature Landscape
[from Phase 1 — context for baselines, datasets, and metric definitions; never used to alter the claims]

## Claims to Verify
[from Phase 2 — full list, in extraction order]

### Claim 1: [title]
- Original (verbatim from task.md): [excerpt]
- Extracted statement: [cleaned predicate]
- Hypothesis: [one sentence]
- Measurable predicate: [metric on dataset under condition]
- Expected direction: [up | down | equal | threshold]
- Status: pending verification
- Verified by milestone(s): [link(s) to EXPERIMENT_PLAN.md]

### Claim 2: [title]
…

## Refined Proposal
- Proposal: `refine-logs/FINAL_PROPOSAL.md` (unified testing approach covering all claims)
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md` (milestones tagged with the claim(s) each verifies)
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Next Steps
- [ ] /mechanism-skills to route the testing approach to a concrete mechanism family + submethod (Workflow 1.25)
- [ ] /auto-experiment to implement and run the verification suite (Workflow 1.5)
- [ ] /auto-verify to stress-test each verified claim under method/dataset/model swaps (Workflow 1.75)
- [ ] /auto-iteration-loop to iterate the verification suite until reviewer-ready (Workflow 2)
- [ ] Or invoke /auto for the autonomous claim → routing → experiments → verify → review chain
```

### Phase 5.5: Write Compact Files (when COMPACT = true)

**Skip entirely if `COMPACT` is `false`.**

Write `idea-stage/IDEA_CANDIDATES.md` — a lean summary of the top entries from `idea-stage/IDEA_REPORT.md`. The schema depends on `BEHAVIOR_SOURCE`.

*In `BEHAVIOR_SOURCE = discovery`* — the top 3–5 surviving ideas:

```markdown
# Idea Candidates

| # | Idea | Pilot Signal | Impact | Novelty | Reviewer Score | Status |
|---|------|-------------|--------|---------|---------------|--------|
| 1 | [title] | +X% | X/10 | Confirmed | X/10 | RECOMMENDED |
| 2 | [title] | +Y% | X/10 | Confirmed | X/10 | BACKUP |
| 3 | [title] | Negative | — | — | — | ELIMINATED |

## Active Idea: #1 — [title]
- Hypothesis: [one sentence]
- Key evidence: [pilot result]
- Next step: /mechanism-skills (Workflow 1.25, route to mechanism family) → /auto-experiment (Workflow 1.5, implement + deploy) — or /research-refine to revise the proposal first
```

*In `BEHAVIOR_SOURCE ∈ {given, given-validation}`* — every captured behavior/claim, no ranking:

```markdown
# Claim Candidates

**Behavior-source**: <given | given-validation>
**Mechanism**: <given | discovery>
**Claim source**: task.md

| # | Claim | Measurable Predicate | Status |
|---|-------|----------------------|--------|
| 1 | [title] | [metric on dataset under condition] | pending verification |
| 2 | [title] | [metric on dataset under condition] | pending verification |
| … | …     | …                    | …                    |

## Active Plan
- Unified proposal: `refine-logs/FINAL_PROPOSAL.md`
- Milestones: see `refine-logs/EXPERIMENT_PLAN.md`
- Next step: /mechanism-skills (Workflow 1.25, route the testing approach) → /auto-experiment (Workflow 1.5, run the verification suite)
```

This file is intentionally small (~30 lines) so downstream skills and session recovery can read it without loading the full `idea-stage/IDEA_REPORT.md`.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- **Don't skip phases beyond what `BEHAVIOR_SOURCE` already prescribes.** Each phase filters or refines. Skipping a phase outside the prescribed flow leads to wasted effort or silently malformed outputs downstream.
- **Checkpoint between phases.** Briefly summarize what was found before moving on.
- **`discovery`: kill ideas early.** It's better to kill 10 bad ideas in Phase 3 than to implement one and fail.
- **`discovery`: empirical signal > theoretical appeal.** An idea with a positive pilot outranks a "sounds great" idea without evidence.
- **`given` / `given-validation`: claim fidelity > convenience.** Never simplify, narrow, or strengthen the captured behavior/claim to make it easier to verify — that distorts the result. Phase 4.5 may sharpen the *testing method*, never the behavior/claim.
- **Document everything.** Dead ends in `discovery` and faithfulness-audit decisions in `given` / `given-validation` capture (e.g., why two paragraphs were merged into one claim) are as valuable as the headline results.
- **Be honest with the reviewer.** In `discovery`, include negative pilot results and failures in the review prompt. In `given` / `given-validation`, surface any capture ambiguities to `/research-refine-pipeline` so the testing method accounts for them.

## Composing with Downstream Workflows

After this pipeline produces a validated top idea (`discovery`) or a unified plan over the captured behavior/claims (`given` / `given-validation`), hand off to the next workflows in order:

```
/auto-claim "direction" [— behavior-source: given | given-validation | discovery, mechanism: given | discovery]   ← you are here (Workflow 1)
/mechanism-skills                    ← Workflow 1.25: route the method / testing approach to a mechanism family + submethod (skipped when MECHANISM=given — the family is already chosen)
/auto-experiment                     ← Workflow 1.5: implement + deploy from the routing + plan
/auto-verify                         ← Workflow 1.75: stress-test passed claims
/auto-iteration-loop [reviewer-context-only, optional]   ← Workflow 2: iterate until submission-ready. The optional arg is reviewer context only — NOT a starting point. Run /auto-claim + /auto-experiment + /auto-verify first if those artifacts don't exist.

Or use /auto for the autonomous claim → routing → experiments → verify → review chain (the `behavior-source` + `mechanism` flags drive the whole pipeline).
```

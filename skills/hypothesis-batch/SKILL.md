---
name: hypothesis-batch
description: "Automated pipeline for generating and refining multiple research hypotheses."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__llm-chat__chat
---

# Workflow: Claim Stage — Behavior Discovery × Mechanism Discovery

Orchestrate the claim stage for: **$ARGUMENTS**.

## Overview

This skill chains sub-skills into a single automated, non-interactive pipeline:

```
/research-lit → /idea-creator → /novelty-check → /impact-check → /research-review → /research-refine-pipeline
  (survey)      (brainstorm)    (verify novel)   (verify it     (critical feedback)  (refine method + plan)
                                                  matters)
```

**Batch shape: 30 in, 10 out.** Phase 2 brainstorms **~30** candidate ideas across three angle-partitioned `/idea-creator` rounds. Novelty (Phase 3) is a hard gate; impact (Phase 3.5) and external review (Phase 4) then score **every survivor**, and Phase 4.25 makes the single cut to **10** — vetoing fatal design flaws outright, then ranking by impact first, reviewer score second, novelty last. From Phase 4.5 on, each of the 10 is worked **independently and in parallel**, and each gets its own directory.

**Deliverables.**

```
idea-stage/
  RESEARCH_LIT.md          # raw retrieval dump (audit-only)
  LANDSCAPE.md             # synthesized landscape
  IDEA_REPORT.md           # all ~30 ideas, ranked, with eliminations — the batch index
claims/
  01_<name>/               # one directory per surviving idea, rank-ordered
    FINAL_PROPOSAL.md
    EXPERIMENT_PLAN.md
    claim.json             # ⭐ the deliverable a human reviewer reads
  02_<name>/
    …
  10_<name>/
```

`claim.json` is the point of the whole run: a self-contained paper skeleton written **for a human expert reviewer**, who sees that file and nothing else. Everything above it is working material. Its specification is Phase 4.8 and is binding.

## Pipeline

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

### Phase 1.75: Mechanism Strategy Load

This phase loads strategy into context; it writes **no artifact**. It is a *reference* step — its job is to put the relevant strategy skills in context so Phase 2 (hypothesis direction) and Phase 4.5 (experiment plan) can apply them. Both skills are principles only: read them, do not execute their phases, and do not expect an output file from either.

1. **Behavior strategy** — invoke `/mechanism-behavior-discovery` and read its `SKILL.md` in full (the standard for finding, sharpening, and validating a *new* behavioral phenomenon — the five bars Real / Non-obvious / Specific / Robust / Tractable, the discovery strategies, and the validation discipline). It decides *what behavior is worth explaining*. Log `[behavior-strategy] discovery — loaded /mechanism-behavior-discovery`.
2. **Mechanism strategy** — invoke `/mechanism-explore` via the Skill tool and read its `SKILL.md` in full; the strategy shapes *how to explain* the behavior (the hypothesis direction in Phase 2 and the experiment plan in Phase 4.5). It fixes the direction only — the concrete family is left unbound. Log `[mechanism-strategy] discovery — loaded /mechanism-explore`.

Hold the loaded guidance in context for the rest of the run — do **not** copy it into any output file.

What the loaded strategy is used for (advisory — it never relaxes `/idea-creator`'s novelty / feasibility / pilot filtering):

- **Phase 2 (hypothesis direction)** — first surface and *sharpen* candidate phenomena (per `/mechanism-behavior-discovery`), then frame candidate ideas as *falsifiable mechanistic hypotheses* (name the implicated internal object and the predicted causal relation) with at least one "boring" null (memorization / surface feature / shortcut), favoring ideas on a climbable ladder of evidence. The claim **assumes** the chosen phenomenon exists and attaches the mechanistic hypothesis — its *actual* existence is tested by the M0 gate when the plan is run, not asserted here.
- **Phase 4.5 (experiment plan)** — shape the plan to climb the ladder of evidence: a cheap correlational/attribution screen to localize candidates → a causal intervention (ablation / patching / steering) to confirm the survivors → matched-control + off-target + confound checks for specificity. Each intervention milestone records the expected **sign**, **magnitude / dose-response**, and a **specificity control**. The plan **opens with a phenomenon-validation gate (M0)** that the mechanism milestones all depend on (see Phase 4.5).

### Phase 2: Produce the Candidate Ideas

This phase writes `idea-stage/IDEA_REPORT.md`, the ranked candidate pool that Phases 3–3.5 cut down to 10.

**Three rounds, not one call.** `/idea-creator` generates 8–12 ideas per invocation — that count is fixed inside its own prompt template and is not a parameter, so a single call cannot produce 30. Run it **three times** and merge:

```
/idea-creator "$ARGUMENTS — angle: <round assignment>; do not regenerate or closely vary: <titles from earlier rounds>"
```

Assign each round a **different slice of the search space**, so the rounds diverge by construction rather than by luck:

| Round | Assignment |
|---|---|
| 1 | The landscape's **structural gaps** — one idea aimed at each gap `LANDSCAPE.md` names. |
| 2 | The **mechanism directions from `/mechanism-explore` not yet used** in round 1 (Location / Causal Intervention / Tuning & Editing / Formation Tracing / Unit Interpretation / Decision Auditing). |
| 3 | The **phenomena classes underrepresented** after rounds 1–2 — read the two merged rounds, name what kind of behavior is missing, and aim the third round there. |

Pass the titles already generated as an explicit exclusion in each later round. Round 3 is written **after** reading rounds 1–2, so its assignment is derived, not guessed.

**What each round does:**
- Read `idea-stage/LANDSCAPE.md` from disk (written by Phase 1 / `/research-lit`), then brainstorm 8–12 concrete ideas via the external LLM reviewer (llm-chat).
- Filter by feasibility, compute cost, quick novelty search.
- Deep-validate the leading ideas (full novelty check + devil's advocate).
- Rank by empirical signal.

**Merge into `idea-stage/IDEA_REPORT.md`.** Concatenate the three rounds into one `## Ranked Ideas` section, then **deduplicate**: two ideas are the same idea when they share a phenomenon *and* an internal object, whatever their titles say. Keep the better-stated one, record the merge. Target **~30** candidates; 24–36 is fine, and a merged pool below ~20 means the rounds collapsed onto each other — run a fourth round on whatever the dedupe revealed as over-covered.

**Breadth is the point.** The pool exists to be cut, so 30 near-duplicates of one framing is a failed Phase 2. Overshoot rather than undershoot: the pool must survive a novelty gate and a design veto and still leave 10.

**Apply the Phase 1.75 strategy.** Pass `/mechanism-explore`'s framing into `/idea-creator` so each generated idea is stated as a falsifiable mechanistic hypothesis (internal object + predicted causal relation + at least one boring null), and bias ranking toward ideas with a climbable ladder of evidence. First apply `/mechanism-behavior-discovery` to surface and *sharpen* candidate *phenomena* from the landscape (state each crisply per the five bars and screen plausibility) — the claim **assumes** the chosen phenomenon exists and attaches a mechanistic hypothesis; the phenomenon's actual existence is tested by the M0 gate in the experiment stage, not claimed here. This shapes idea *framing* only — novelty, feasibility, and pilot filtering are unchanged.

### Phase 3: Deep Novelty Verification

Run a thorough novelty check on **every surviving candidate** — one `/novelty-check` per idea, dispatched in parallel:

```
/novelty-check "[idea N description]"      # for each surviving idea
```

**What this does:**
- Multi-source literature search (arXiv, Scholar, Semantic Scholar)
- Cross-verify with the external LLM reviewer
- Check for concurrent work (last 3-6 months)
- Identify closest existing work and differentiation points

**Update `idea-stage/IDEA_REPORT.md`** with deep novelty results. Eliminate any idea that turns out to be already published, and record for each survivor its **three nearest works** with the specific finding each established — Phase 4.8's `Related Work` field and checklist item 1 both need exactly this, and re-deriving it later wastes a second literature pass.

### Phase 3.5: Deep Impact Verification

For each idea that survived novelty (Phase 3), run an impact check on the **problem/behavior** it studies — one `/impact-check` per idea, in parallel:

```
/impact-check "[idea N — behavior/problem + hypothesis]"      # for each survivor
```

**What this does:** judges whether the studied problem/behavior is *important* — solves a real problem, is likely to be used/cited, could shift a field's direction, helps applications/industry/society/cross-disciplinary work, or reveals an important phenomenon even with a simple method. Outputs `Impact: X/10` + `PROCEED / PROCEED WITH CAUTION / DEPRIORITIZE`.

**Update `idea-stage/IDEA_REPORT.md`.** Add an `Impact: X/10` line to each surviving idea. **No cut happens here** — impact is one of three signals the Phase 4.25 selection combines.

### Phase 4: External Critical Review

Review **every idea that survived novelty** — not just a shortlist. One `/research-review` per idea, dispatched in parallel:

```
/research-review "[idea N with hypothesis + evidence]"      # for each survivor
```

**What this does:**
- The external LLM reviewer acts as a senior reviewer (NeurIPS/ICML level)
- Scores the idea, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

Reviewing the full pool rather than a pre-selected 10 is deliberate: novelty and impact both judge *whether the question is worth asking*, and neither can tell whether the proposed design could actually answer it. That is the reviewer's lens, and it is worth having **before** the batch is fixed rather than after.

**Update `idea-stage/IDEA_REPORT.md`** with each idea's reviewer score and feedback. The feedback has two distinct downstream uses, and Phase 4.25 depends on telling them apart:

- **Fatal design flaws** — the hypothesis is not falsifiable as stated, the measurement cannot reach the quantity it claims to measure, a confound is structural rather than controllable, the intervention cannot be run on any accessible model. Refinement cannot rescue these; they are grounds for elimination.
- **Ordinary weaknesses** — incremental framing, execution risk, thin baselines, unclear presentation. These are exactly what Phase 4.5's refinement is for and must **not** eliminate anything.

Classify each review as one or the other when recording it.

### Phase 4.25: Select the Batch of 10

This is the only cut that produces the batch. It combines all three signals.

**Step 1 — Apply the veto.** Eliminate every idea whose Phase 4 review found a **fatal design flaw**, regardless of its impact score. An idea whose measurement cannot answer its own question does not become shippable by being important. Record it under `## Eliminated Ideas` with reason `vetoed at external review — <the flaw>`.

**Step 2 — Rank the rest.** Order by **impact first, reviewer score second, novelty third**:

- **Impact** dominates — a less-novel idea on an important problem outranks a novel idea nobody needs.
- **Reviewer score** breaks impact ties and pulls down ideas the reviewer found weak-but-fixable.
- **Novelty** is the last tiebreak only. Everything still standing already passed Phase 3's novelty gate, so it has little spread left to discriminate on.

**Step 3 — Take the top 10.** Everything below the cut moves to `## Eliminated Ideas` with reason `below rank 10`. This ranking fixes the folder numbering in Phase 4.5 — nothing downstream re-orders it.

**Step 4 — Check the spread.** If the top 10 collapse onto two or three phenomena, swap the lowest-ranked duplicates for the highest-ranked candidates that cover a distinct phenomenon, and note each swap. Ten skeletons on one phenomenon is a worse batch than ten on eight, even at slightly lower average score.

**If fewer than 10 survive**, run **one** top-up round: return to Phase 2, generate additional ideas aimed at the gaps the eliminations exposed, and put them through Phases 3 → 4.25. If the batch is still short after that round, ship what survived and state the shortfall plainly in `IDEA_REPORT.md` — never pad the batch with an idea that was already eliminated, never overturn a novelty verdict or a design veto to reach 10.

### Phase 4.5: Per-Claim Refinement + Experiment Planning

**From here on the batch splits.** Each of the 10 ideas is refined **independently, in its own directory**, and nothing is shared between them except the landscape. Run the 10 in parallel.

**Step 0 — Create the directories.** For each idea, in the Phase 4.25 rank order:

1. Derive `<name>`: a **snake_case slug, ≤ 6 words, naming the phenomenon** — the same slug that becomes `claim.json`'s `Name` field in Phase 4.8. Derive it once here and reuse it verbatim; the directory name and the `Name` field must not diverge.
2. Create `claims/<NN>_<name>/`, where `NN` is the zero-padded rank (`01`…`10`).
3. Log `[claim] <NN>_<name> — "<idea title>"`.

Every artifact from this phase onward is written **inside that directory**. Nothing goes to a shared `refine-logs/`.

**Step 1 — Refine each idea.** For each of the 10, invoke `/research-refine-pipeline` with that idea's title, description, evidence, and its Phase 4 reviewer feedback:

```
/research-refine-pipeline "[idea <NN>: title + description + evidence + reviewer feedback]"
```

and write its outputs to `claims/<NN>_<name>/FINAL_PROPOSAL.md` and `claims/<NN>_<name>/EXPERIMENT_PLAN.md`.

**What `/research-refine-pipeline` does** (per idea):
- Freeze a **Problem Anchor** (the idea's problem statement) to prevent scope drift.
- Iteratively refine the **method / testing approach** via external LLM review (up to 5 rounds, until score ≥ 9).
- Generate a claim-driven experiment roadmap with ablations, budgets, and run order.

- **(Mechanism milestones — ladder of evidence, from the Phase 1.75 strategy):** shape the roadmap to climb the ladder of evidence — a cheap correlational/attribution screen to localize candidates → a causal intervention (ablation / patching / steering) to confirm the survivors → matched-control + off-target + confound milestones for specificity — and have each intervention milestone record the expected sign, magnitude / dose-response, and its specificity control. Because the plan commits to a *direction*, not to a concrete mechanism **submethod**, any milestone field whose correct value depends on that submethod — typically `n_pairs`, intervention `sites`, the exact effect `metric`, and the per-run GPU-hours estimate — is necessarily provisional. Tag each such milestone with a `method_sensitive: [<field>, ...]` line (English machine field, written verbatim regardless of report language) marking the fields that must be re-bound once a submethod is picked.

- **(Phenomenon-validation gate M0):** the claim only **assumes** the phenomenon exists; whether it is *real* is settled by running the plan, not by writing it. So the roadmap's **first milestone** is a hard gate that **must carry the machine marker `kind: phenomenon-validation`** (the title may be phrased / localized freely — the marker is what identifies the gate mechanically). With an explicit pass criterion:
  - reproduces across **paraphrase, seed, and decoding settings** (not one exact string);
  - **confounds controlled** (length, token frequency, position, format, label identity, few-shot leakage);
  - **statistical reality** — sample size large enough to clear noise (honor any project minimums; ≥ ~50 by default), with variability reported, not a single number;
  - the **trivial-explanation check** ruled out (tokenizer / sampling / eval-bug).

  All mechanism milestones (M1…Mn) **declare `depends_on: [M0]`**, and the M0 block spells out the **four-state verdict** that governs them: `established` → run the mechanism milestones; `conditional` → restrict mechanism analysis to the conditions where the phenomenon holds and tag the claim `conditional`; `not-established` → stop and report a negative result; `inconclusive` (the M0 test itself is broken or underpowered) → fix and re-run M0. Never run mechanism work on an untested phenomenon.
- Output: `claims/<NN>_<name>/FINAL_PROPOSAL.md`, `claims/<NN>_<name>/EXPERIMENT_PLAN.md`.

**Failure isolation.** If refinement fails for one idea, that failure stays local: record it in that directory and in `IDEA_REPORT.md`, and continue with the other nine. One bad claim never aborts the batch.

**`EXPERIMENT_PLAN.md` shape.** Each milestone block MAY declare these fields:

- `depends_on: [<milestone-name>, ...]` — this milestone's runs must wait until every listed upstream milestone is complete before launching. Use for teacher → student chains, baseline → ablation chains, or any milestone that needs an upstream artifact (checkpoint, dataset, calibration result). The names refer to other milestone blocks in the same `EXPERIMENT_PLAN.md`.
- `grid: { <param-name>: [<value>, <value>, ...], ... }` — Cartesian-product expansion. Each combination produces one run with the params substituted via `${param-name}` placeholders into the milestone's `cmd:` template. Use for multi-seed sweeps (e.g., `grid: { seed: [42, 200, 201], n_hidden: [64, 128, 256], n_train_subset: [50000, 150000, 500000] }` → 27 runs). When `grid:` is present, the milestone's `cmd:` is treated as a template (rather than a literal command) and `id:` may also be a template (e.g., `s${seed}_N${n_hidden}_n${n_train_subset}`).
- `kind: phenomenon-validation` — **stable machine marker** identifying the M0 gate, so it can be found by field rather than by title. The marker is an English machine field (per the Output-language protocol) and must be written verbatim regardless of the report language, leaving the title heading free to be phrased / localized. Every plan has exactly one `kind: phenomenon-validation` milestone (M0).
- `method_sensitive: [<field>, ...]` — **per intervention milestone.** Lists the fields whose correct value depends on the mechanism submethod (typically `n_pairs`, `sites`, `metric`, `gpu_hours`) and therefore must be re-bound before the milestone can run.

In addition to the per-milestone fields above, `EXPERIMENT_PLAN.md` carries the top-metadata machine marker `mechanism_strategy:` (the strategic-direction block above).

Example milestone block:

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

This block expands to 36 runs. For a small milestone (≤ 5 runs, no `depends_on`, no `grid`), just list the runs explicitly instead.

### Phase 4.8: Write `claim.json` — the reviewer-facing deliverable

Write one `claim.json` per directory: `claims/<NN>_<name>/claim.json`. **This is the final result of the whole workflow** — a paper skeleton good enough to submit to a top AI conference, written for a human expert reviewer who has `claim.json` and nothing else.

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

`Name` is additionally bound to the directory: it is the same snake_case slug, ≤ 6 words, naming the phenomenon, that was derived in Phase 4.5 — the directory name and the `Name` field must not diverge. The field-by-field section below is this workflow's binding elaboration of the seven descriptions above; where it is more specific, it governs.

#### Field by field

**`Short Hypothesis`** carries the whole claim in one paragraph. It names the **triggering condition** (what has to be true for the phenomenon to appear), the **phenomenon** (a falsifiable regularity in observable model behavior), the **internal object** held responsible (layer / head / neuron / SAE feature / direction / circuit), and **H1…Hk** — two to four sub-hypotheses, each with a stated direction. H1 is always the existence claim: does this happen at all. The last H is the one that pays: a causal intervention or an edit that moves the behavior, not another correlation.

**`Related Work`** names real, citable work — author and year — and for each says *what result it established*, then what this claim contradicts, extends past its stated scope, or looks at where it never looked. «They study X, we study Y» is a topical separation and does not count. It closes with at most one positioning sentence («the first to (i)… (ii)…»), and every clause in that sentence must survive checklist item 1.

**`Abstract`** reads like the abstract of a paper someone would actually open: the human-legible motivation first, then the controlled design, then the hypotheses in a sentence each, then what a positive result gives the field.

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

**Experiment 1 is a gate with four outcomes**, all spelled out in the text: *established* (the plan proceeds), *conditional* (it holds only under some conditions, and the later experiments are scoped to those), *not established* (the claim dies), *inconclusive* (the measurement itself failed and must be fixed and re-run, not adjudicated). Its pass criterion must cover reproducibility across paraphrase, seed, and decoding; controlled confounds; a sample size clear of noise; and the ruling out of trivial explanations. This is the same gate as `EXPERIMENT_PLAN.md`'s M0, rewritten as prose.

Where a threshold is stated, say what it rests on — measured in a cited paper, or an estimate. Estimates are fine; estimates dressed as measurements are not.

**The rungs themselves are planning vocabulary and never surface in `claim.json`.** «Phenomenon-validation», «localization», «specificity», «M0», `kind: phenomenon-validation`, `method_sensitive` are this workflow's names for its own scaffolding, and a reviewer holding only `claim.json` has no way to decode them. Each experiment is headed instead by the hypothesis it tests and the finding it would produce — `Experiment 1 (H1 — Half-life):`, `Experiment 4 (H4 — Activation edit):` — and opens with a sentence saying what it does in the paper's own terms. The ladder should be legible from the **order and content** of the experiments, never from a label the reader has to look up.

#### The undecidable band

Experiment 1's *inconclusive* outcome is not special to the gate. Every threshold splits the outcome space into three regions rather than two — results that clearly support the hypothesis, results that clearly refute it, and the band between them where the planned measurement cannot decide — and finite samples, measurement noise, and any equivalence margin guarantee that band exists for H2…Hk as well.

So each hypothesis states its own, in the experiment that tests it: **where the band lies**, in the threshold's own units (an effect between 0.5σ and 2σ of cross-seed noise, say, or a half-life whose interval spans zero); **what a result there means**, said plainly — H*i* is not supported at the planned power, the effect being too small to separate from noise at this sample size, or the measurement too coarse to separate the mechanism from its rivals — and not «a weak trend consistent with H*i*», not silence; and **what follows**, fixed before the data rather than after it: H*i* reported as undecided, the pre-specified extension run if the plan budgets one (more items, more seeds, a finer measurement), and the experiments depending on H*i* stopped, scoped, or run unchanged.

That belongs where the reviewer meets the hypothesis. `Risk Factors and Limitations` adds only what the experiment cannot: where the plan's own power estimate says the band is likely to be entered — a small expected effect, few available items, a high-variance intervention — say so there, with what it would cost to narrow it.

#### Numerical consistency

Every quantity that carries a number — a threshold, a margin, a sample size, an item count, a budget — is defined once and written identically everywhere it appears: same name, same value, same unit. Within `claim.json`, a bar introduced in `Short Hypothesis` is the bar the matching experiment's prediction enforces, the one `Ablations and controls` and `Metrics` report against, and the one any `Risk Factors and Limitations` entry mentioning it uses. Across the directory, `claim.json`, `EXPERIMENT_PLAN.md`, and `FINAL_PROPOSAL.md` describe a single study, so wherever the same quantity appears in more than one of them — `n` per condition, the sweep values, Experiment 1's pass criterion, the GPU-hour estimate — the values match.

When they disagree, decide which value is right and edit every file that carries it. `claim.json` is the plan rewritten in the reviewer's register: rewriting the prose is expected, rewriting the numbers is not, so never round or simplify a number on the way in, and never leave the plan at the old value after sharpening the claim. A `method_sensitive` field is provisional, which means one number awaiting re-binding — not a different number in each file.

#### From working notes to paper

This run writes far more than it ships. `LANDSCAPE.md` holds the survey; `IDEA_REPORT.md` holds the scores and the eliminations; `FINAL_PROPOSAL.md` and `EXPERIMENT_PLAN.md` hold the executor-facing plan. **A reviewer sees `claim.json` and nothing else**, and the whole difficulty of this phase lives in that gap.

Every piece of working material either dissolves into one of the seven fields or stays behind. It never gets a field of its own, and it never goes unplaced by default:

| what the run produces | where it lands in `claim.json` |
|---|---|
| the phenomenon and its triggering condition | `Short Hypothesis`, opening sentences |
| where the idea came from — the cross-domain result or human finding it transfers | `Abstract`, the opening motivation; a clause in `Related Work` when the source is itself citable |
| the structural gap in the landscape | `Related Work`, restated as what the literature has not done |
| the mechanistic conjecture — internal object, causal relation | `Short Hypothesis`, the H-list |
| the mundane rival accounts | `Experiments`, where each one's control is introduced; `Risk Factors and Limitations` for any left unhandled |
| the three nearest works (Phase 3 / checklist 1) | `Related Work`, roughly a clause each |
| the expert's prior (checklist 2) | `Abstract` or `Related Work` — whichever sentence explains why the result would surprise |
| the consumer on each branch (checklist 3) | `Abstract`, closing sentence |
| the breaking case (checklist 4) | `Risk Factors and Limitations`, as the stated scope bound |
| the ladder, its gates, controls, models, data | `Experiments` |
| novelty / impact / reviewer scores, rank, direction combinations, rung names, rejected ideas | nowhere — batch bookkeeping, stays in `IDEA_REPORT.md` |

**The routing must not show.** The table says *where*, not that a sentence must appear. It routes material already going into the paper; it is not a list of sentences to add. A row is discharged when its content is *there* — usually inside a sentence written for another reason, often as a subordinate clause, sometimes two rows at once. The test runs backwards: **a reviewer must not be able to reconstruct this table from the prose.** Nothing announces its own function — no «our contribution is novel because», no «the expert prior is», no «as a named consumer». If a row's content is already carried by a sentence that had to be written anyway, it is done; adding a dedicated sentence for it makes the paper worse, and a paper that reads like a completed form does not survive review.

> **Routing showing through:** *The expert prior here is that retraction fully erases the claim, so our result is non-obvious. If the claim is true, deployers of retrieval-augmented systems will audit their corrections; if false, they will not.*
>
> **Absorbed:** *A retraction is normally assumed to do what it says: the claim is withdrawn, and what follows is computed without it. We find instead that the withdrawn claim keeps shaping downstream inferences long after the model has verbally accepted the correction — an assumption that every multi-turn and retrieval-augmented deployment currently relies on untested.*

**One register for the agent, another for the reviewer.** Every row of the table is sourced from something written in a register that is not the paper's — a bulleted gap in `LANDSCAPE.md`, a scored entry in `IDEA_REPORT.md`, an executor-facing milestone in `EXPERIMENT_PLAN.md` covering the same experiments as `Experiments`. All of it was written to be *processed*, by a machine or by you later; none of it was written to be *read*. So carrying a sentence across means **rewriting it in the paper's register**: keep the numbers, the direction, and the controls; drop the operational scaffolding that matters only to whoever runs it; and restore what an executor never needed and a reviewer cannot do without — what the measurement is *for*, and what it would show.

> **Executor-facing:** `M2: for l in [12,16,20] patch resid_post @ last_tok, α∈{0.5,1,2}, n=200/cond, log Δlogprob(P) vs C0; gate |Δ|>2σ_seed; fallback l=8 if OOM.`
>
> **Reviewer-facing:** *Experiment 3 (H3 — Causal confirmation): We patch the residual stream at layers 12, 16, and 20 at the final token of the retraction, sweeping the edit strength over three values on 200 items per condition, and measure the change in log-probability of the retracted claim relative to the no-mention baseline. If the localized component is causal rather than merely correlated, the effect should be negative, should grow monotonically with edit strength, and should exceed the cross-seed noise we measure in Experiment 1.*

**Nothing may point at a file the reviewer does not have.** No «the gap identified in `LANDSCAPE.md`», no «see `EXPERIMENT_PLAN.md`», no «idea #3 in the batch», no bare «Gap 3», and no reference to the other nine claims — each `claim.json` stands entirely alone. Where such material earns a place in the paper it is restated in full: the gap becomes a sentence about what the literature has not done, the rejected alternative becomes a design choice with its reason. Fail: any noun phrase in `claim.json` whose referent lives only in another file.

#### Writing for the reviewer

- **`Short Hypothesis`, `Related Work`, and `Abstract` are continuous prose** — no bullets, no sentence fragments, no telegraphic notation. They should be readable end to end by someone who has never seen this workflow.
- **`Experiments` is structured at the label level and prose everywhere below it.** The labels exist so a reviewer can find the model list without reading the whole field, but a label is a signpost, not a license to stop writing sentences. Write «We fit an exponential decay of the probe-minus-baseline difference against washout distance and report a per-model half-life in tokens; we predict a positive half-life for every model, longer for stronger initial assertions», not «fit: exp decay; x: washout; out: half-life (tok); pred: >0». Only item 7 is a list.
- **Every sentence carries its own referents.** Name the condition rather than pointing at «C2», say what a step is *for* rather than assuming the reader knows what «specificity» buys, and expand an abbreviation the first time it appears. A label may be introduced and then reused («(C2) P asserted then explicitly retracted» once, «C2» thereafter) — but it must be introduced *inside* `claim.json`, in the field where it is first used.
- **No placeholders ship.** No `TBD`, no `<…>`, no «details to be determined». An unknown is either resolved or named in `Risk Factors and Limitations` as an open choice with its options.
- **Name a work only if you can cite it.** Author and year, and a result you can state. A fabricated citation invalidates the whole skeleton.
- **Prefer the number to the quantifier.** «1,500 items across four domains» over «a large benchmark».

#### Write order

Write `Experiments` first — the ladder forces the claim to become concrete, and a claim that cannot be laddered is not ready to be written up. Then `Short Hypothesis`, `Related Work`, `Abstract`, `Risk Factors and Limitations`, and finally `Title` and `Name`; the title comes easiest once you know what the paper actually shows.

#### Quality checklist

Run this on **each** `claim.json` before shipping it. Each item is a **check that can fail on a fact**, never a quality the author can assert. «This idea is non-obvious» is satisfied by typing it; «name the three nearest works and say which of their findings this contradicts» is not.

What these checks turn up is content, not scoring. Each finding has a field waiting for it in the routing table above and is written there as part of the paper's argument — never as a self-assessment of how the claim scores.

*Is the idea new*

1. **Three nearest works, each separated at the level of a finding.** Name the three closest works. For each, state the specific result it established and what this claim contradicts, extends past its scope, or looks at where it never looked. Fail: fewer than three can be named, or any separator is merely topical. If genuinely nothing is close, decide which case it is — nobody asked the question, or nobody has a use for the answer — and if it is the second, the claim changes.
2. **The expert's prior is written down before the plan is.** State the direction a researcher in this area would predict for the key measurement without having read this claim. If it matches the claim's own prediction, the direction is not what is new — say what is (the magnitude, the mechanism producing it, the setting) and check that the experiment measures *that*. Fail: no experiment distinguishes the claim from the expert's prior.

*Would it matter*

3. **Both branches have a named consumer.** Say who does something differently if the claim comes out true, and separately if it comes out false — a specific decision (what gets audited, what gets deployed, which assumption gets dropped), not «the community would understand this better». Fail: either branch is empty.
4. **The stakes survive stripping the setting, and the scope has an edge.** Re-read the claim with its high-stakes setting (clinical / legal / financial / safety) swapped for a neutral one. If the contribution evaporates, the contribution was the framing — either drop the framing or make the setting do real work, with the mechanism turning on something particular to that domain rather than on its stakes. Then name one concrete setting where the conclusion should **break**. Fail: the contribution is carried by the setting, or no breaking case can be named.

*Can it be settled*

5. **Experiment 1 can kill the claim.** Assume it returns *not established*: does `Short Hypothesis` die with it? If the claim could survive by reinterpreting the outcome as a measurement problem, the gate is hung on the wrong object — re-hang it. (*Inconclusive* is the branch for a broken measurement; it must not become a hiding place for the claim.)
6. **Every mundane explanation is paired with a control.** Match each rival account one-to-one against the controls in `Experiments`. Any account with no control either gets one or moves into `Risk Factors and Limitations` as explicitly not ruled out. Listing a rival and then ignoring it is a fail.
7. **Every hypothesis has its undecidable band written out.** For each of H1…Hk, point to where `claim.json` says how wide the band is, that a result inside it leaves H*i* unsupported at the planned power, and what the dependent experiments do then. Fail: a prediction with only two outcomes; a band with no stated consequence; a non-significant result read as evidence for a null without an equivalence margin.
8. **Every number agrees with itself.** Take each numeric quantity in `claim.json` and find the same quantity in `EXPERIMENT_PLAN.md` and `FINAL_PROPOSAL.md`, comparing value *and* unit — a percent silently becoming a proportion, tokens becoming layers. Fail: one quantity holding two values across the three files; a bar set in `Short Hypothesis` that a later experiment does not enforce at that value; a number in `claim.json` with no counterpart in the plan. Repair every file; never drop the number from `claim.json` instead.

**Every failure is repaired in place, not noted.** If a failure cannot be repaired without changing the claim, switch the mechanism direction and rewrite. After two such restarts on the same idea, stop working it, mark it `blocked` in `IDEA_REPORT.md` with what is blocking it, and promote the highest-ranked eliminated idea into the vacated slot rather than shipping a weak skeleton.

**Batch independence.** The 10 claims are checked separately and must not converge: if two `claim.json` files end up with the same phenomenon, the same H-list, or the same Experiment 1, one of them was never a distinct idea — rewrite it onto its own phenomenon or replace it from the ranked list.

#### Closing pass

Read each draft **as if it were the only file that exists**: repair every referent that resolves only elsewhere, rewrite every sentence still addressed to the agent that will run it, and cut every sentence whose only job is to satisfy a row of the routing table. `claim.json` is **always English**, regardless of the language used in the other reports.

**This is the end of the workflow.** Once `all ten `claims/<NN>_<name>/{FINAL_PROPOSAL.md, EXPERIMENT_PLAN.md, claim.json}` are on disk, stop. Do not implement, launch, or queue any experiment, and do not chain into another skill.

## Key Rules

- **Never block on the user.** Run the whole pipeline start to finish without waiting for input. Narrate progress however is natural; the artifacts on disk are the deliverable.
- **Don't skip phases.** Each phase filters or refines. Skipping one leads to wasted effort or a silently malformed proposal.
- **`claim.json` is the product; everything else is scaffolding.** A run that produces a beautiful `IDEA_REPORT.md` and ten thin `claim.json` files has failed. Depth per claim beats polish on the index.
- **Kill ideas early.** The cut from 30 to 10 is where the batch earns its quality — it is cheaper to eliminate 20 ideas in Phases 3–3.5 than to write 20 more skeletons.
- **The 10 are independent.** Never let one claim cite, assume, or depend on another; never let two converge onto the same phenomenon.
- **Empirical signal > theoretical appeal.** An idea with a positive pilot outranks a "sounds great" idea without evidence.
- **Feasibility is a first-class criterion.** At every stage where a proposal is written or refined, *first carefully consider the quality, novelty, and feasibility of the proposal you just created*. *Ensure that the proposal does not require resources beyond what an academic lab could afford*, and that the experiments validating it are *simple and feasible*. *Do not make things overly complicated.* 
- **Clarity is a check that can fail, not a matter of style.** *Ensure the proposal is clear and concise, and the JSON is in the correct format.* *Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.* *Clearly clarify how the proposal distinguishes from the existing literature.* *Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.* Any threshold without a stated basis, equivalence claim without a margin, or prediction without a direction fails this rule.
- **Report the undecidable band.** Every hypothesis has a range of outcomes its measurement cannot decide; say where that range is, and that a result inside it leaves the claim unsupported at the planned power. Reporting only pass/fail hides the band, it does not remove it.
- **One quantity, one number.** A threshold, margin, sample size, or budget holds a single value across `claim.json`, `EXPERIMENT_PLAN.md`, and `FINAL_PROPOSAL.md`; disagreement is repaired in every file, never smoothed over in the one a reviewer reads.
- **Document everything.** Dead ends are as valuable as the headline results.
- **Be honest with the reviewer.** Include negative pilot results and failures in the review prompt.
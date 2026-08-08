---
name: hypothesis-batch
description: "Batch-generate research hypotheses with experiment plans for a single topic, through a «draft → coarse filter → refine → final filter» funnel. One round yields ~10 (behavior + mechanism) candidates, accumulated into hypothesis_library.json. Each hypothesis has two parts: claim (phenomenon + mechanistic conjecture + directional prediction) and plan (evidence ladder + decision gates + controls + budget). Each candidate is scored as a whole on IMPACT and NOVELTY. Use when the user asks to «batch generate hypotheses», «diversify the hypothesis library», or «batch generate hypotheses»."
argument-hint: "<topic> [— behavior: <text | Bk>] [— n-drafts: N] [— final: F] [— rounds: R] [— library: <path>]"
---

# Hypothesis Batch

Batch-generate research hypotheses with experiment plans for a single topic, through a «draft → coarse filter → refine → final filter» funnel. One round yields ~10 (behavior + mechanism) candidates, accumulated into hypothesis_library.json. Each hypothesis has two parts: claim (phenomenon + mechanistic conjecture + directional prediction) and plan (evidence ladder + decision gates + controls + budget).

Selecting a hypothesis and running the experiments is something the user does manually afterwards. This skill does not read or write `research_memory.json`, and does not produce `task.md` / `FINAL_PROPOSAL.md`.

## Artifacts

Everything goes into `hypothesis_library.json`. It is a tree, `behaviors[] → mechanisms[]`; **one hypothesis = one leaf + its parent's phenomenon**.

```jsonc
{
  "topic":"",
  "behaviors":[{
    "id":"B1",
    "source":"discover | given",
    "phenomenon":{
      "statement":"<one-sentence falsifiable phenomenon>",
      "trigger":"<triggering condition>",
      "five_bars":{"real":"","nonobvious":"","specific":"","robust":"","tractable":""},
      "origin":{"strategy":"<which discovery strategy was used>","detail":"<how this idea came about>","grounding":["<the specific LANDSCAPE Gap it targets>"]}
    },

    "mechanisms":[{
      "id":"B1-M1",

      "claim":{
        "statement":"<a paragraph stating the hypothesis clearly: which internal object, what causal relation holds between it and the phenomenon, and intervening on it moves which metric in which direction by how much>",
        "competing_accounts":"<a paragraph: what mundane explanations could produce the same phenomenon, and why they cannot be ruled out a priori>",
        "directions":["Location","Causal Intervention"],
        "strategy":"Mechanistic evidence"
      },

      "plan":{
        "ladder":[{
          "id":"M0",
          "kind":"phenomenon-validation | localization | intervention | specificity",
          "goal":"", "procedure":"", "measure":"",
          "gate":{"pass":"<quantified>","conditional":"<null if not applicable>","refute":"<quantified, mutually exclusive with pass>","inconclusive":"",
                  "basis":"<where the threshold comes from: which instrument-sheet entry / which paper / estimate — to be calibrated at M0>"},
          "controls":[{"name":"","rules_out":"<which explanation it rules out>"}],
          "depends_on":[], "cost":{"runs":0,"gpu_hours":0}
        }],
        "resources":{
          "models":["<named id + scale>"],
          "data":[{"provenance":"existing | adapted | constructed","source":"","used_n":"","note":""}],   // provenance here means "where the data comes from", unrelated to the phenomenon's origin
          "compute":{"by_milestone":{"M0":0},"total_gpu_hours":0}
        },
        "risks":[{"risk":"","fallback":"<an executable fallback, or «no substitute needed»>"}]
      },

      "impact":{"score":8,"rationale":""},
      "novelty":{"score":7,"closest":"","differentiation":""},
      "status":"selected | cut",
      "status_reason":"<one line: why it was cut. Leave empty for selected>"
    }]
  }]
}
```

**The phenomenon lives on the behavior node, in exactly one copy** —— it is not duplicated just because two mechanisms hang off it. Conceptually «one hypothesis = claim + plan», where the full claim = the parent's `phenomenon` + this leaf's `claim`.

**Both scores hang on the leaf, and both are assigned against the full claim.** Two dimensions are kept because «important phenomenon but stale method» and «new method but nobody cares» are two different kinds of bad, and collapsing them into one score hides that; but **both judges must see the phenomenon and the mechanism** —— scoring an axis in isolation throws away information the judgment needs. Two mechanisms under the same phenomenon each get their own scores, and they should differ.

**Every candidate that passes the initial screen enters the library, with `status` recording its fate** —— only `selected` (the final artifacts that passed the final filter) and `cut` (those that didn't). This keeps the whole funnel auditable after the fact, and the `cut` batch is exactly the pool to draw from when backfilling at the final filter. `status_reason` gets one line on why it was cut: for coarse-filter rejects, whether the score was too low or which diversity constraint blocked it; for final-filter rejects, which quality-checklist item it failed. `selected` needs no reason. Candidates that fail the initial screen do not enter the library.

## Funnel

| Stage | Count | Output |
|---|---|---|
| Draft | 30 | Phenomenon + mechanism skeleton, **no `plan`** |
| Coarse filter | → 12 | Dedup + scoring + diversity constraints |
| Refine | 12 | Write the full `claim` + `plan` |
| Final filter | → 10 | The final artifacts that pass the quality checklist |

The 2 between 12 and 10 are a **buffer, not a quota**: cut by the checklist; if all 12 qualify, cut the lowest-scoring ones to fill the gap and note «cut to hit the number»; if more than 2 fail, backfill from the cut pool and rewrite.

## Constants

- **N_DRAFTS / KEEP / FINAL = 30 / 12 / 10** —— the three funnel tiers; override with `— n-drafts:` `— final:`.
- **FANOUT_MAX = 2** —— **fan-out** means how many mechanisms hang under one behavior (how many angles are used to explain the same phenomenon). At most 2; the 2nd must switch to a different direction combination and give a reason. Do not pad to fill the quota.
- **ROUNDS = 1** —— how many times to run the funnel. Rebuild the banlist after each round is written to disk; earlier artifacts are only banned, never regenerated. Override with `— rounds:`.
- **BEHAVIOR_SOURCE** —— if `— behavior:` is given, it is `given` (phenomenon fixed, only mechanisms are added; the value may be free text or an existing node such as `B3`); otherwise `discover` (both axes are generated).
- **Files** —— `hypothesis_library.json` (the tree) + `instrument_sheet.json` (the instrument sheet), in the project root by default; change the path with `— library:`.

## The Two Axes

**behavior axis** —— read `/mechanism-behavior-discovery` and use its discovery strategies as lenses. Every phenomenon must pass five bars (Real / Non-obvious / Specific / Robust / Tractable) and be a one-sentence falsifiable regularity **with a triggering condition**.

**mechanism axis** —— read `/mechanism-explore` and generate along its direction combinations:

| strategy | directions |
|---|---|
| Mechanistic evidence | Location → Causal Intervention |
| Capability / editing | Location → Tuning & Editing |
| Complete account | Location → Causal Intervention → Formation Tracing |
| Explaining a model | Location → Unit Interpretation |
| Decision reliability | Location → Unit Interpretation → Decision Auditing |

**Directions have prerequisites; switch when they are not met**: Formation Tracing needs public training checkpoints; Tuning & Editing needs the behavior to be worth improving; Decision Auditing needs a decision that carries a reliability cost. Record one line in the trace for each direction that was swapped out.

Every mechanistic conjecture must name: the internal object (layer / head / neuron / SAE feature / direction / circuit), the predicted causal relation, and ≥1 mundane explanation (memorization / surface features / shortcuts / tokenizer / position).

## Procedure

Setup (once per topic) → loop body 1–6 (run `ROUNDS` times) → wrap-up.

### Setup

**Read the library.** Read `hypothesis_library.json`. If the topic in it differs semantically from this run's topic, **stop and ask** —— never silently overwrite. If it does not exist, create an empty tree.

**Ground in the literature.** Run `/research-lit "<topic>"` (skill `/mechanic-db-search` included) to obtain `LANDSCAPE.md`. The Structural Gaps in that file are the preferred generation lens, and its Banlist is merged into the ban list. An existing file for the same topic can be reused directly.

**Build the instrument sheet.** Write `instrument_sheet.json` —— this is what makes **checkable** thresholds possible at batch scale: numbers all come from the sheet, rather than each hypothesis improvising its own.

```jsonc
{
  "models":   [{"id":"", "size":"", "access":"open|gated|api",
                "sae":{"source":"","widths":[],"layers":[]},
                "checkpoints":"<whether public checkpoints exist, which decides whether Formation Tracing is usable>",
                "fallback":"<same-family downgrade model if unavailable>"}],
  "datasets": [{"name":"","split":"","available_n":0,"elicits":"<what behavior it can elicit>"}],
  "metrics":  [{"name":"","definition":"","typical_range":"","seed_noise":"<cross-seed variation, the basis for setting thresholds>"}],
  "cost_model": {"<unit operation>":"<GPU-hours>"}
}
```

> **At the start of every round**, re-read the library and rebuild the banlist; **at the end of every round**, write to disk.

### 1. Draft

Generate 30 drafts, pasting the full banlist into the prompt, requiring no duplicates or near-paraphrases.

**BEHAVIOR_SOURCE** = `discover`: spread across at least **15 distinct behaviors**, with 1–2 mechanisms under each behavior.
**BEHAVIOR_SOURCE** = `given`: do not generate phenomena; only add the direction combinations not yet covered for that phenomenon.

Besides `statement` / `trigger` / `five_bars`, every phenomenon must fill in `phenomenon.origin` —— **a record of how this phenomenon was thought up**, in three fields:

- `strategy` —— which discovery strategy was used (cross-domain transfer / borrowing from human science / cross-modal transfer / reusing an existing CS result / interrogating conditions and causes)
- `detail` —— one or two sentences: which finding from which discipline was borrowed, and what it was mapped onto
- `grounding` —— which Gap in `LANDSCAPE.md` it targets; prioritize thinking into those blank spots

This block exists for auditing where ideas came from after the fact —— without it, the library holds only conclusions, and you cannot see how this batch of hypotheses grew or which lenses it covered.

**Write only the skeleton, no `plan`** —— expensive plan-writing is deferred until after the coarse filter.

### 2. Dedup

Use semantic judgment (**not string matching**), in two layers:

- **Phenomenon layer** —— compare each new phenomenon against all phenomena already in the library; mark `new` or `duplicate`
- **Mechanism layer** —— for each surviving phenomenon, compare each new mechanism against the mechanisms already under that phenomenon; mark `new` or `duplicate`

**Duplicates are discarded and do not enter the library.**

### 3. Scoring

**The scoring unit is one candidate** (the whole of phenomenon + mechanism + prediction), not an individual axis. First run one targeted search and use it together with `LANDSCAPE.md` as the evidence base, then apply two judge roles, **both seeing the full claim**:

- **IMPACT**, following `/impact-check`: if this hypothesis holds, is it worth doing —— `score` 1–10 + a one-line `rationale` + `PROCEED / PROCEED WITH CAUTION / DEPRIORITIZE`
- **NOVELTY**, following `/novelty-check`: is **studying this phenomenon from this angle** new —— `score` 1–10 + `closest`, the nearest existing work + a one-line `differentiation`

> **Do not score the axes separately.** Asking «is this method new» detached from the phenomenon has almost no answer (patching itself is of course not new; what is new is aiming it at this phenomenon); asking «is this phenomenon important» detached from the mechanism throws away the decisive information of whether it can be intervened on. The direct consequence of scoring them separately is that all scores bunch up in the middle band.
>
> Two mechanisms under the same behavior may be evaluated in a single call (they share the phenomenon, which saves calls), but **each must get its own score** —— a different angle changes both how worth doing and how novel it is.

**Scores must spread across the bands.** Everything bunched into two adjacent bands = no discrimination; re-score once and force the range downward. Scores exist to rank; bunched together, the coarse filter is a no-op. The two scores are **reported separately and not combined into a single ranking**.

### 4. Coarse Filter to 12

Rank the scored candidates and add a diversity constraint: at most 2 mechanisms per behavior. When the constraint makes it impossible to fill 12, fill the remainder in score order.

**Rejects are not discarded**: mark them `status: "cut"` and put them in the library as well (they never reached the refine step, so they have no `plan`), with `status_reason` stating whether the score was too low or which diversity constraint blocked them. They are exactly the pool to draw from when backfilling in step 6.

### 5. Refine

For the 12 that made it, generate **one at a time** (one call per candidate), filling in `claim` and `plan`. `plan.ladder` is ordered as an evidence ladder:

```
M0  phenomenon-validation   Does the phenomenon actually exist (every phenomenon in this skill is conjectural, so this gate is mandatory)
M1  localization            Cheap correlational/attribution screening to locate candidate components
M2  intervention            Causal-intervention confirmation, recording sign, magnitude, dose-response
M3  specificity             Matched controls + off-target checks + confound control
```

**The M0 gate is four-valued**: `pass` / `conditional` (holds under some conditions, with the scope restricted) / `refute` / `inconclusive` (the measurement itself failed and should be fixed and re-run rather than adjudicated). Later milestones declare their dependence on M0 via `depends_on`. M0's pass criteria must cover: reproducible across paraphrases/seeds/decoding, confounds controlled, sample size clear of noise, and mundane explanations ruled out.

Thresholds are derived from the instrument sheet, with the source noted in `gate.basis`.

### 6. Final Filter + Write to Disk

Take the full claim + plan and run each candidate through the **quality checklist** below, cutting 12 down to 10 (see the «Funnel» section for the three cases).

**Quality checklist: write to it when refining, check against it when filtering.** It covers all three of the axes a candidate is worth anything on — is the idea new, would it matter, can it be settled — two to three items each.

Each item is written as a **check that can fail on a fact**, never as a quality an author can assert. «This idea is non-obvious» is satisfied by typing it; «name the three nearest works and say which of their specific findings this contradicts» is not. When adding or rewriting an item, hold it to three conditions: it names an **external referent** (a real paper, a stated prediction, a named consumer, a number with a source), it has a **stated fail condition**, and its verdict **changes the candidate** — repair it if repairable, cut it otherwise.

**The material these checks produce is working material.** It goes into the trace, and, where it is genuine content — a rival explanation, a boundary condition, the prior result an argument leans on — into `phenomenon` / `claim` / `plan` where it carries weight. It is never written back as a self-assessment of how the candidate scores.

*Is the idea new*

1. **Three nearest works, each separated at the level of a finding.** Name the three closest existing works. For each, state the specific result that work established, and what this claim asserts that contradicts it, extends it past its stated scope, or falls in a place it never looked. A separation of **topic** («they study X, we study Y») is not a separation of **finding** and does not count. Fail: fewer than three can be named, or any separator is merely topical. If genuinely nothing close exists, decide which case it is — nobody has asked the question, or nobody has a use for the answer — and record it; the second is a cut.
2. **The expert's prior is written down before the plan is.** State the direction a researcher in this area would predict for M2's key measurement without having read this claim. If it matches the claim's own predicted direction, the direction is not what is new — say what is: the magnitude, the mechanism producing it, or the setting. Then check that M2 actually measures **that**. Fail: the plan's measurement cannot distinguish the claim from the expert's prior.

*Would it matter*

3. **Both branches have a named consumer.** State who does something differently if the claim comes out true, and separately if it comes out false — a specific decision (what gets audited, what gets deployed, which assumption gets dropped), not «the community would understand this better». Fail: either branch is empty. A claim only informative when it confirms is a one-sided bet and gets cut.
4. **The stakes survive stripping the setting, and the scope has an edge.** Re-read the claim with its high-stakes setting (clinical / legal / financial / safety) swapped for a neutral one. If the contribution evaporates, the contribution was the framing — either cut it, or make the setting do real work: the mechanism must turn on something particular to that domain, not on its stakes. Then name one concrete setting where the conclusion should **break**. Fail: the contribution is carried by the setting, or no breaking case can be named — an unbounded claim is unbounded, not general.

*Can it be settled*

5. **The M0 gate is attached to the claim itself.** Assume M0 lands in `refute`: does `claim.statement` die with it? If the claim could survive by reinterpreting the outcome as a measurement problem, the gate is hung on the wrong object — re-hang it. (`inconclusive` is the branch for a failed measurement; it must not become a hiding place for the claim.)
6. **Every mundane explanation is paired with a control.** Match each account in `claim.competing_accounts` one-to-one against the `controls` in `plan.ladder`. Any account with no control either gets one, or goes into `plan.risks` as explicitly not ruled out. Listing a rival explanation and then not handling it is a fail.
7. **Thresholds and resources both trace to something.** For every `gate.pass` / `gate.refute` number, `gate.basis` says whether the figure is (a) measured in this project, (b) reported in a named paper, or (c) an estimate — estimates are allowed but must not be phrased as measurements, and a candidate whose thresholds are *all* (c) is downgraded. Every model, SAE width / layer, and data split has a matching entry in `instrument_sheet.json`, or goes into `plan.risks`; `cost` recomputes from `cost_model` and totals within 2–4 weeks of one person's work, or gets a downgrade path.

## Key Rules

- **Decoupled from `/auto`.** Do not touch `research_memory.json`, do not modify `/auto` / `/auto-claim` / `/idea-creator`, do not produce `task.md`. When decoupling conflicts with convenience, choose decoupling.
- **One file per topic**; stop and ask when crossing topics; use `— library:` to keep multiple topics separate.

## Protocols

- **[Output versioning](../shared-references/output-versioning.md)** —— both JSON files are living documents updated in place, with no timestamped versions; the raw output of each stage goes into the trace.
- **[Output manifest](../shared-references/output-manifest.md)** —— register in MANIFEST.md on first creation.
- **[Output language](../shared-references/output-language.md)** —— JSON keys, strategy / directions names, `kind`, the `gate` keys, and score / recommendation / method / date stay in English; the free text of phenomena and mechanisms follows the project language.
- **[Run tracing](../shared-references/review-tracing.md)** —— store each step under `.mechanist/traces/hypothesis-batch/<date>_run<NN>/`, with one `r<NN>/` subdirectory per round when running multiple rounds.

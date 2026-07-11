---
name: hypothesis-batch
description: "Standalone BATCH generator of research hypotheses for ONE topic — enumerates many (behavior + mechanism) candidates into a TREE library (hypothesis_library.json), each behavior scored with an IMPACT check and each mechanism with a NOVELTY check, with LLM semantic dedup. It does NOT refine, review, pilot, converge to a single idea, or build an experiment plan — but it DOES score every behavior for IMPACT and every mechanism hypothesis for NOVELTY (separate scores only — no combined ranking). Can run MANY consecutive rounds in ONE invocation via `— rounds: R` (each round adds ~N_BEHAVIORS and persists to the library before the next; later rounds rebuild their banlist from the accumulated library, so earlier behaviors are never regenerated) — e.g. `— rounds: 5, n-behaviors: 10` aims for ~50 distinct behaviors. Its only selector is BEHAVIOR_SOURCE = discover (mine new behaviors + mechanisms) | given (behavior fixed, generate mechanisms only); there is no `mode` flag. Behavior axis is enumerated from /mechanism-behavior-discovery's discovery strategies; mechanism axis from /mechanism-explore's combination strategies. Fully INDEPENDENT of /auto: it never reads or writes research_memory.json and never touches /auto, /auto-claim, or /idea-creator. Use when the user wants to mass-produce diverse, deduplicated, impact- & novelty-scored behavior+mechanism hypotheses on a topic (e.g. 'batch generate hypotheses', '批量生成假设', '多样化假设库', 'build a hypothesis library for X'). Candidates are promoted into /auto MANUALLY by the user later — this skill performs no handoff."
argument-hint: "<topic> [— behavior-source: discover | given] [— behavior: <text | Bk>] [— n-behaviors: N] [— rounds: R]"
---

# Hypothesis Batch — Tree Library Generator (novelty-scored)

Mass-produce **diverse, deduplicated, impact- & novelty-scored** `(behavior → mechanism)` hypotheses for a single topic and persist them as a **tree** in `hypothesis_library.json`. Each **behavior** carries an IMPACT score (is the phenomenon important) and each **mechanism** carries a NOVELTY score (is the method new). This is the divergent, non-converging counterpart of the `discovery` claim stage: same two generation axes, but it enumerates *many* candidates instead of committing to one, and it stops after the impact + novelty checks — no refinement, review, pilot, ranking, or experiment plan.

## What this is / is NOT

- **IS:** generate (behavior + mechanism) candidates → semantic dedup → **impact score per behavior + novelty score per mechanism** → persist to the tree library.
- **Is NOT:** `/auto-claim` or part of `/auto`. It does **not** call `/auto-claim` or `/idea-creator`, does **not** read or write `research_memory.json`, and does **not** produce `FINAL_PROPOSAL.md` / `EXPERIMENT_PLAN.md` / `task.md`. Promotion into an `/auto` round is a **manual** step the user does later.
- **Is NOT** convergent — it never ranks down to one idea, never refines, never pilots, never reviews/plans. (Impact + novelty scoring are the *only* evaluative steps it performs, and they are reported separately — never combined into a rank.)
- Domain-general — `topic` is a parameter; nothing is hard-coded to any single domain.

## Modes — `BEHAVIOR_SOURCE` (the only selector)

The single selector is **`BEHAVIOR_SOURCE = discover | given`**, set with `— behavior-source:`. There is **no `mode` flag** — this skill does not take one; if `— mode:` is passed it is ignored.

- **`BEHAVIOR_SOURCE = discover`** *(default when no `— behavior:` is given)* — **behavior is NOT specified, so generate behavior conjectures too.** Enumerate the *behavior* axis from `/mechanism-behavior-discovery`'s four discovery strategies (target `N_BEHAVIORS` new behaviors), then for each new behavior generate the *mechanism* axis (per `/mechanism-explore`'s combination strategies). Grows the tree on **both** axes.

- **`BEHAVIOR_SOURCE = given`** *(auto-selected when `— behavior:` is supplied)* — **behavior is fixed, so generate mechanism conjectures only.** The behavior axis does not grow. The `— behavior:` value is resolved two ways:
  - **existing node id** (e.g. `— behavior: B3`) → reuse that behavior node;
  - **free text** (e.g. `— behavior: "模型在多轮对话中倾向维持首轮立场"`) → create one new behavior node from it (no five-bars mining; it is taken as given), then append mechanisms under it.
  Append **only** new mechanism children; propose no new behaviors.

**Resolution & conflicts:**
- `behavior-source: given` **requires** a `— behavior:`; if absent, halt and ask for the behavior (do not silently fall back).
- `behavior-source: discover` **with** a `— behavior:` present → the explicit `behavior-source` wins (discover); report the mismatch in one line and ignore `— behavior:` for generation.
- If `— behavior-source:` is omitted, derive it: `— behavior:` present → `given`; absent → `discover`.

## Constants

- **BEHAVIOR_SOURCE = (auto)** — `discover` (default; no `— behavior:`) or `given` (a `— behavior:` is supplied). Override with `— behavior-source:`. See "Modes".
- **N_BEHAVIORS = 10** — target count of *new* behaviors to add **per round** (`discover` only). Override with `— n-behaviors: N`.
- **ROUNDS = 1** — number of consecutive generation rounds to run in this single invocation. Each round runs the full **generate → dedup → impact/novelty → persist** cycle (Phases 3–6), adding ~`N_BEHAVIORS` new behaviors (`discover`) or new mechanisms (`given`) and **writing them to `hypothesis_library.json` before the next round starts** — so the library accumulates round-by-round. Because every round **rebuilds its banlist from the just-updated library**, behaviors/mechanisms produced in earlier rounds are **never regenerated** in later rounds (they become part of the banlist). Set with `— rounds: R`. With `— rounds: 5, n-behaviors: 10`, one invocation aims for ~50 distinct behaviors across 5 accumulating passes. The round loop self-terminates early if a round adds nothing after dedup (topic saturated — report it).
- **REVIEWER_BACKEND = `llm-chat`** — external LLM via llm-chat MCP for generation, semantic dedup, and novelty scoring (model defers to `LLM_MODEL`).
- **NOVELTY_WEB = true** — when true, run one quick web/arXiv search per surviving behavior to ground **both** the impact and novelty scores (cheap: per-behavior, not per-mechanism). Set false for a pure-LLM estimate. This skill produces **lightweight triage scores** only; for a publication-grade verdict on a chosen candidate, run the standalone `/impact-check` (behavior) or `/novelty-check` (mechanism) on it separately.
- **LIBRARY_FILE = `hypothesis_library.json`** — the single canonical tree file (project root). One topic per file; created on first run. No other view file is generated.

## The Two Axes

**Behavior axis — read `/mechanism-behavior-discovery` SKILL.md, use its four discovery strategies** as lenses (`discover` only):
1. Cross-domain transfer  2. Borrow from the human sciences  3. Cross-modal transfer  4. Reuse past CS results.
Each behavior passes the five bars (Real / Non-obvious / Specific / Robust / Tractable) and is a one-sentence falsifiable phenomenon **with its triggering condition**.

**Mechanism axis — follow `/mechanism-explore`: read its SKILL.md and generate one hypothesis per combination strategy it defines** (per behavior). Do not hardcode a count here — use whatever strategy set `/mechanism-explore` currently specifies. At time of writing those are:
- **Mechanistic evidence** — Location → Causal Intervention
- **Capability / editing** — Location → Tuning & Editing
- **Complete account** — Location → Causal Intervention → Formation Tracing
- **Explaining a model** — Location → Unit Interpretation
- **Decision reliability** — Location → Unit Interpretation → Decision Auditing

Each mechanism hypothesis names **(a)** the internal object (layer / head / neuron / SAE feature / direction / circuit), **(b)** the predicted causal relation (ablate→effect, steer→dose-response, patch→localization), and **(c)** ≥1 **boring null** (memorization / surface feature / shortcut / tokenizer / position). A strategy that does not fit a behavior may be skipped with a one-line reason.

## Workflow

**Structure:** Phases 0–2 are **one-time setup**. Phases 3–6 are the **per-round body**, repeated `ROUNDS` times (Phase 6 persists the library at the end of every round, so round *k*+1's Phase 3 banlist is built from everything rounds 1..*k* produced → no re-generation of earlier ideas). Phase 7 reports the **aggregate** across all rounds. When `ROUNDS = 1` this is exactly the original single-pass behavior.

### Phase 0 — Resolve topic, behavior-source, rounds & load library
1. Parse `topic` (required; ask in one line if missing). Compute `topic_slug` (lowercase kebab-case) for record-keeping only. Read `N_BEHAVIORS` and `ROUNDS` overrides if supplied.
2. Resolve `BEHAVIOR_SOURCE` per the "Modes" resolution rules (validate the given/discover ↔ `— behavior:` consistency; halt/ask or report mismatch as specified).
3. If `hypothesis_library.json` exists: read it as the current tree. **Cross-topic guard:** if its `topic` differs semantically from this run's topic, **halt and ask** (rename/move the old file, or confirm overwrite) — never silently overwrite another topic's library. Else start an empty tree `{topic, topic_slug, created, updated, behaviors: []}`.
4. If `BEHAVIOR_SOURCE = given`, resolve the target behavior node now: existing `Bk` → reuse; free text → create one new behavior node (statement = the text; mark `source: "given"`).

### Phase 1 — (optional) ground from landscape
If `idea-stage/LANDSCAPE.md` exists, read its gaps/narrative and pass them as grounding into the brainstorm + novelty prompts. If absent, proceed purely generatively (do **not** run `/research-lit`).

### Phase 2 — Load the two axes' framing + the two scorers
Read `/mechanism-behavior-discovery` (only needed for `discover`) and `/mechanism-explore` SKILL.md in full for generation, plus `/impact-check` and `/novelty-check` for the Phase 5 scoring criteria (reference only — copy nothing into outputs). Hold in context for Phases 3–5.

> **Round loop (Phases 3–6 ×`ROUNDS`).** Run the following cycle once per round, `round = 1..ROUNDS`. At the **start of each round, re-read `hypothesis_library.json`** (it grew in the previous round's Phase 6) and rebuild the banlist from its current contents, so earlier rounds' behaviors/mechanisms are banned and never regenerated. Persist (Phase 6) at the **end of every round** before starting the next. If a round adds **0** survivors after dedup, the topic is saturated for this run — stop the loop early and note it in the Phase 7 report rather than spinning further rounds.

### Phase 3 — Brainstorm (single `llm-chat` call, per round)
One `llm-chat` call **per round**. The model is stateless, so the prompt MUST paste the **banlist** = **all** existing behavior statements currently in the library, including those added by earlier rounds of this same invocation (and, in `given`, existing mechanism `(directions + hypothesis)` for the target behavior) and require outputs that are NOT in it or close variants. Branch on `BEHAVIOR_SOURCE`:
- **`discover`:** ask for `N_BEHAVIORS` new behaviors that **span all of `/mechanism-behavior-discovery`'s discovery strategies** (cover the different lenses within this one call) and are mutually distinct; for each, name the `discovery_strategy` used **and a one-to-two-sentence `discovery_strategy_detail`** stating how the idea was reached (the concrete provenance — e.g. which cross-discipline finding/method was borrowed and mapped onto what, or which past CS result was reused in which new setting); plus one mechanism hypothesis per applicable `/mechanism-explore` combination strategy, with object + causal relation + boring null, and five-bars one-liners.
- **`given`:** do **no** behavior generation; keep the fixed behavior and ask only for new mechanism hypotheses across `/mechanism-explore`'s combination strategies not already present for it.
- **Both branches — planned `data` + `model` per mechanism.** For **every** mechanism, also propose its planned `data` (existing dataset first per `/mechanism-behavior-discovery`: `provenance` = existing/adapted/constructed, `source`, planned `used_n` / n_pairs, and a one-line `note` on how it elicits the behavior or builds the intervention pairs) and target `model` (id + size, as a list). This mirrors `/auto-claim`'s Resources framing — triage-level, not a binding plan.
Save the raw response to the run trace.

### Phase 4 — Semantic dedup (LLM, two layers)
Use `llm-chat` for semantic judgment (not string match):
1. **Behavior layer** *(`discover` only; skipped in `given`)*: flag each new behavior `new` or `duplicate-of:<Bk>`; drop duplicates (merge extra nuance into the existing node's `notes` if valuable).
2. **Mechanism layer:** within each surviving/target behavior, flag each new mechanism `new` or `duplicate-of:<Bk-Mj>`; drop duplicates.

### Phase 5 — Impact (per behavior) + Novelty (per mechanism) check & score
Score **per behavior** (one call covering that behavior and all its mechanism variants), not per leaf separately — impact attaches to the behavior, novelty to each mechanism:
1. If `NOVELTY_WEB`, run one quick web/arXiv search for the behavior + its mechanism angle to ground **both** scorers (per behavior; cheap).
2. Call `llm-chat` once per behavior with two referee roles:
   - **Impact referee on the behavior** (following `/impact-check`'s dimensions): return `score` (1–10, 10 = clearly important), a one-line `rationale` (why it matters + who would build on it), and a `recommendation` (PROCEED / PROCEED WITH CAUTION / DEPRIORITIZE).
   - **Novelty referee on each mechanism variant** (following `/novelty-check`): return `score` (1–10, 10 = clearly new), the single `closest` prior work, a one-line `differentiation`, and (optional) a one-line caveat.
   Both are lightweight triage scores, not publication-grade verdicts.
3. Write `impact` into the behavior node and `novelty` into each mechanism leaf (schema below). Stamp `method` (`llm-chat` / `llm-chat+web`) and `date` on both.
Save the impact + novelty traces.

### Phase 6 — Merge into the tree & persist (end of each round)
1. Assign ids by max-suffix+1 (never reuse): behaviors `B<n>`; mechanisms `B<n>-M<m>`.
2. Append survivors under the right behavior / discovery_strategy. Set `status: "candidate"`, stamp `batch` (date + run index + round index, e.g. `2026-06-23.run01.r03`) and `updated`.
3. Write `hypothesis_library.json` (the single canonical file) **now, before the next round** — this persisted state is what the next round reads as its banlist. Then return to Phase 3 for the next round (until `ROUNDS` is reached or a round adds 0 survivors).

### Phase 7 — Report (aggregate across all rounds)
Print: topic, `BEHAVIOR_SOURCE`, `ROUNDS` requested vs. actually run (note early stop if a round saturated), a one-line **per-round ledger** (round → behaviors/mechanisms added → running total), **total** #behaviors added / total, #mechanisms added / total, #semantic duplicates dropped (summed across rounds), impact score distribution across **all** behaviors (min/median/max) and novelty score distribution across **all** mechanisms (min/median/max, count ≥8), and file paths. Remind that promotion into `/auto` is manual (write the chosen behavior into a `task.md`, then run `/auto`).

## Library Schema (canonical JSON — nested tree, one topic per file)

```json
{
  "topic": "<topic>",
  "topic_slug": "<slug>",
  "created": "<YYYY-MM-DD>",
  "updated": "<YYYY-MM-DD>",
  "behaviors": [
    {
      "id": "B1",
      "source": "discover",
      "discovery_strategy": "Cross-domain transfer",
      "discovery_strategy_detail": "<how this idea was reached: the concrete provenance of the conjecture — e.g. which finding/method from which discipline was borrowed and mapped onto what here, or which past CS result was reused in which new setting>",
      "statement": "<one-sentence phenomenon + trigger>",
      "five_bars": {"real":"","nonobvious":"","specific":"","robust":"","tractable":""},
      "impact": {
        "score": 8,
        "rationale": "<one line: why it matters + who would build on it>",
        "recommendation": "<PROCEED | PROCEED WITH CAUTION | DEPRIORITIZE>",
        "method": "llm-chat+web",
        "date": "<YYYY-MM-DD>"
      },
      "gaps": ["<optional, e.g. G1 if grounded on LANDSCAPE.md>"],
      "notes": "<optional merged nuance>",
      "mechanisms": [
        {
          "id": "B1-M1",
          "strategy": "Mechanistic evidence",
          "directions": ["Location", "Causal Intervention"],
          "hypothesis": "<internal object + predicted causal relation>",
          "boring_null": "<>=1 boring null>",
          "data": {
            "provenance": "existing | adapted | constructed",
            "source": "<dataset name / where it comes from>",
            "used_n": "<planned size or split; for interventions e.g. n_pairs>",
            "note": "<one line: how this data elicits the behavior / how the intervention pairs are built>"
          },
          "model": ["<model id + size, e.g. Llama-3-8B>"],
          "novelty": {
            "score": 7,
            "closest": "<closest prior work>",
            "differentiation": "<one line: why this is different>",
            "caveat": "<optional>",
            "method": "llm-chat+web",
            "date": "<YYYY-MM-DD>"
          },
          "status": "candidate"
        }
      ]
    }
  ]
}
```

`source` on a behavior is `discover` (mined) or `given` (supplied via `— behavior:`). `status` lifecycle is owned by the user: `candidate` → `queued` → `explored` (flip by hand when promoted into an `/auto` round). This skill only ever writes `candidate`.

## Output Protocols

> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — `hypothesis_library.json` is a living document updated in place (not timestamped); save raw llm-chat passes (generation, dedup, novelty) to the run trace instead.
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log `hypothesis_library.json` to MANIFEST.md on first creation.
> - **[Output Language Protocol](../shared-references/output-language.md)** — machine fields (ids, strategy/direction names, source, status, data.provenance, data.source, model ids, impact.score/recommendation/method/date, novelty.score/method/date) stay English; free-text behavior/mechanism/discovery_strategy_detail/data.note/rationale/differentiation follows the project language.

## Review Tracing

After each `mcp__llm-chat__chat` call (generation, dedup, impact + novelty scoring), save the trace per `shared-references/review-tracing.md` to `.mechanist/traces/hypothesis-batch/<date>_run<NN>/`. With `ROUNDS > 1`, put each round's traces in a `r<NN>/` subfolder (e.g. `.mechanist/traces/hypothesis-batch/<date>_run<NN>/r03/`) so every round's passes are kept separately.

## Key Rules

- **The only selector is `behavior-source: discover | given`.** There is no `mode` flag; `— mode:` is ignored if passed.
- **Stay decoupled from `/auto`.** Never read/write `research_memory.json`; never edit `/auto`, `/auto-claim`, or `/idea-creator`; never emit `task.md` / `FINAL_PROPOSAL.md` / `EXPERIMENT_PLAN.md`. If decoupling and convenience conflict, choose decoupling.
- **Generation + impact/novelty scoring only.** No refinement, review, pilot, or ranking-to-one. Diversity, dedup, an impact score per behavior, and a novelty score per mechanism are the whole job — impact and novelty are reported separately, never combined into a rank.
- **Score everything.** No behavior is persisted without an `impact` field; no mechanism leaf without a `novelty` field, nor without planned `data` + `model`.
- **Semantic dedup, not string match** — reworded duplicates must be caught by the LLM judgment pass.
- **Never reuse ids**; append-only growth so the tree is a stable, citable backlog.
- **Rounds accumulate, never repeat.** With `— rounds: R`, persist the library at the end of every round and rebuild the next round's banlist from it, so behaviors/mechanisms from earlier rounds are banned (not regenerated). A round that adds 0 survivors after dedup means the topic is saturated — stop early and say so; never pad with near-duplicates to fill the round.
- **One topic per file**; cross-topic invocation halts and asks rather than overwriting.
- **Large file handling**: if Write fails on size, retry via Bash heredoc silently.

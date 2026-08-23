# `hypothesis-batch` — Pipeline Reference

A compact map of what this skill actually runs: the phases, **the model behind each one** (§2), and what crosses the boundary between them. **`SKILL.md` in this directory is the normative spec** — where the two disagree, `SKILL.md` governs. This file is for orienting quickly and for checking a run against what it was supposed to do.

> **A rewrite exists.** `skills/hypothesis-batch-new/` is the rewritten pipeline — parameterized, behavior-first, one `claim.json` per claim, and with an explicit `WRITER` / `REVIEWER_BACKEND` split. §10 lists what it changed and why. The two are **not** interchangeable: this one produces three files per claim and reads its pool from Markdown.

---

## 1. Parameters

**There are none.** This version has no `## Constants` section: the batch shape is hardcoded **30 in, 10 out**, and there is no way to widen the pool, change the cut, or pick a model from the invocation. The only input is the positional argument.

```
/hypothesis-batch "<research direction>"
```

`$ARGUMENTS` is passed straight through to `/research-lit` and to each `/idea-creator` round. There is no intention/topic distinction, no option list, and no argument parsing to speak of.

Two counts are fixed by sub-skills rather than by choice: `/idea-creator` emits 8–12 ideas per invocation (fixed inside its own prompt template, not a parameter), which is why Phase 2 has to call it **three times** to reach ~30.

---

## 2. Model routing

No model constant is declared anywhere in `SKILL.md`, and the invocation has no way to pick one. **Every sub-skill carries its own `REVIEWER_BACKEND = llm-chat` default**, and they all resolve to the same `LLM_MODEL` — so in practice the run is external-model-heavy without ever having said so.

### The three roles

| Role | Model | Owns |
|---|---|---|
| **External LLM** | `LLM_MODEL` via `mcp__llm-chat__chat` (e.g. `gpt-5.6-luna`) | retrieval synthesis (P1), idea generation + devil's advocate (P2), novelty (P3), impact (P3.5), review (P4), method refinement + experiment roadmap (P4.5) |
| **Orchestrator** | the current Claude session | phase chaining, file I/O, merge + dedup of the three idea rounds, the P4.25 ranking, directory creation — **and, by omission, `claim.json` itself** |
| **No model** | — | P1.75 (strategy load — two `SKILL.md` reads into context), P4.25 (veto → rank → cut → spread check are deterministic rules over fields already written) |

Parallel fan-out (P3, P3.5, P4, P4.5) is dispatched through subagents, which run on the **session** model; the reviewer call *inside* each still goes to llm-chat. Splitting the fan-out never changes which model judges.

### Per phase

| Phase | What actually calls a model | Model |
|---|---|---|
| P1 `/research-lit` | retrieval synthesis + landscape write-up | **llm-chat**, alongside non-model sources: Zotero, Obsidian, local PDFs, WebSearch/WebFetch, the cloud `mechanic-db` SEARCH service |
| P1.75 strategy load | nothing — two `SKILL.md` files read into context | **none** |
| P2 `/idea-creator` × 3 | its Phase 2 brainstorm (8–12 ideas) and its Phase 4 devil's-advocate critique | **llm-chat** (stateless — the landscape and the banlist must be pasted into every prompt) |
| P2 merge + dedup | — | **Orchestrator** (session) |
| P3 `/novelty-check` | its Phase C cross-model verification | **llm-chat** + WebSearch/WebFetch |
| P3.5 `/impact-check` | its Phase C cross-model verification | **llm-chat** + WebSearch/WebFetch |
| P4 `/research-review` | the senior-reviewer pass (NeurIPS/ICML register) | **llm-chat** |
| P4.25 select the batch of 10 | nothing | **none** |
| P4.5 `/research-refine-pipeline` | `/research-refine`'s review–revise loop (`MAX_ROUNDS = 5`, exits at overall score ≥ 9); `/experiment-plan` declares no reviewer backend at all | **llm-chat** for the refinement half, **session** for the planning half |
| P4.8 write `claim.json` | the deliverable itself | **unassigned → falls to the session** |

### Resolving `LLM_MODEL`

`/research-review` states the order and hard-fails if nothing resolves; every other sub-skill inherits the same environment:

1. project `${PROJECT_ROOT}/.mcp.json` → `mcpServers["llm-chat"].env.{LLM_MODEL,LLM_BASE_URL,LLM_API_KEY}`
2. user `~/.claude/settings.json`, same field
3. shell environment — `$LLM_MODEL`, `$LLM_BASE_URL`, `$LLM_API_KEY`

`mcp-servers/llm-chat/server.py` defaults to `gpt-5.6-luna` when `LLM_MODEL` is unset, and swaps to `LLM_FALLBACK_MODEL` on a 504 timeout. **Never hardcode a reviewer model, and never read one from `task.md` or a project README** — model names listed there usually belong to LLM-as-judge code inside experiments, not to this reviewer.

**As configured in this checkout:** there is no project `.mcp.json` and no `llm-chat` entry in `~/.claude.json`, so resolution falls through to the shell environment — `LLM_MODEL=gpt-5.4` at `LLM_BASE_URL=http://47.88.93.22:10001`. Worth checking before a run: if the `llm-chat` MCP server is not actually registered in the session, every llm-chat step degrades to the session model and the whole pipeline becomes one model agreeing with itself.

**Authorship is split by accident.** Phase 4.8 says *"Write one `claim.json` per directory"* and names no model, so the deliverable falls to whoever is orchestrating. The result is a three-way split no one chose:

| artifact | authored by |
|---|---|
| the ideas (`IDEA_REPORT.md`) | llm-chat, via `/idea-creator` |
| `FINAL_PROPOSAL.md`, `EXPERIMENT_PLAN.md` | llm-chat, via `/research-refine-pipeline` |
| **`claim.json`** | **unassigned → the session model** |

So the model that conceived a phenomenon is not the model that writes it up, and the reviewer-facing file is a second reader's re-derivation of someone else's idea. This is the specific defect the rewrite's `WRITER` constant exists to close.

---

## 3. Flow

```
/research-lit → /idea-creator → /novelty-check → /impact-check → /research-review → /research-refine-pipeline
  (survey)       (brainstorm)    (verify novel)   (verify it       (critical feedback)  (refine method + plan)
                                                   matters)
```

### Who runs what

```
P1    /research-lit ──────────────────────────────────────── llm-chat ★      → LANDSCAPE.md
P1.75 load behavior strategy + mechanism strategy ────────── no model        → (context only)
P2    /idea-creator × 3 rounds ────────────────────────────── llm-chat ★      → IDEA_REPORT.md (~30)
                                                              ├─ brainstorm 8–12 ······· llm-chat ★
                                                              ├─ devil's advocate ······ llm-chat ★
                                                              └─ merge + dedup ········· Orchestrator
P3    /novelty-check per idea, parallel ───────────────────── llm-chat ★ + web → hard gate, eliminations
P3.5  /impact-check per survivor, parallel ────────────────── llm-chat ★ + web → Impact: X/10, no cut
P4    /research-review per survivor, parallel ─────────────── llm-chat ★      → score + flaw classification
P4.25 veto → rank → take 10 → spread check ───────────────── no model        → the batch, rank-ordered
P4.5  /research-refine-pipeline × 10, parallel ────────────── llm-chat ★ → session
                                                              ├─ /research-refine, ≤5 rounds ·· llm-chat ★
                                                              └─ /experiment-plan ············ session
                                                                              → FINAL_PROPOSAL.md + EXPERIMENT_PLAN.md
P4.8  write claim.json × 10 ───────────────────────────────── unassigned → session → claim.json
```

★ = `REVIEWER_BACKEND` (`llm-chat` → `LLM_MODEL`, e.g. `gpt-5.6-luna`; `gpt-5.4` as this checkout resolves it). Everything not marked ★ runs on the current Claude session, including the subagents the parallel phases fan out into.

Phases 3, 3.5, 4 are read-only parallel fan-out. **Phase 4.5 is also parallel** — all ten claims are refined at once. No phase re-judges what an earlier one decided, and **no phase before P4.8 is authored by the model that writes the deliverable** (§2).

---

## 4. Phase table

| # | Phase | Model | In | Out |
|---|---|---|---|---|
| 1 | Literature survey (`/research-lit`) | llm-chat + Zotero/Obsidian/PDF/web/mechanic-db | `$ARGUMENTS` | `idea-stage/RESEARCH_LIT.md` (audit-only), `idea-stage/LANDSCAPE.md` |
| 1.75 | Strategy load — **both** strategies at once | **none** — context read only | `/mechanism-behavior-discovery` + `/mechanism-explore` `SKILL.md` | **no file**; behavior strategy shapes P2's framing, mechanism strategy shapes P2's hypothesis direction *and* P4.5's ladder |
| 2 | Produce candidates (`/idea-creator` × 3) | llm-chat (generate + critique); session merges/dedups | `$ARGUMENTS` + angle assignment + earlier rounds' titles as exclusions + `LANDSCAPE.md` | `idea-stage/IDEA_REPORT.md`, ~30 ranked ideas |
| 3 | Novelty gate (`/novelty-check`, parallel) | llm-chat + web | one idea description | eliminations + three nearest works per survivor, into `IDEA_REPORT.md` |
| 3.5 | Impact check (`/impact-check`, parallel) | llm-chat + web | idea's behavior/problem + hypothesis | `Impact: X/10` + recommendation, into `IDEA_REPORT.md`. **No cut** |
| 4 | Critical review (`/research-review`, parallel) | llm-chat | idea + hypothesis + evidence | score + weaknesses, classified fatal vs ordinary |
| 4.25 | Select the batch of 10 | **none** — orchestrator, deterministic | the scored pool | top 10 ranked, rest to `## Eliminated Ideas` |
| 4.5 | Refinement + planning (`/research-refine-pipeline` × 10, parallel) | llm-chat (`/research-refine`, ≤ 5 rounds, score ≥ 9) → session (`/experiment-plan`) | idea + description + evidence + P4 reviewer feedback | `claims/<NN>_<name>/FINAL_PROPOSAL.md`, `EXPERIMENT_PLAN.md` |
| 4.8 | Write `claim.json` | **unassigned → session** (§2) | everything above | `claims/<NN>_<name>/claim.json` |

---

## 5. Phase 2 — three rounds, then merge

`/idea-creator` cannot produce 30 in one call, so:

```
/idea-creator "$ARGUMENTS — angle: <round assignment>; do not regenerate or closely vary: <titles from earlier rounds>"
```

| Round | Assignment |
|---|---|
| 1 | each structural gap `LANDSCAPE.md` names, one idea apiece |
| 2 | the `/mechanism-explore` directions round 1 did not use (Location / Causal Intervention / Tuning & Editing / Formation Tracing / Unit Interpretation / Decision Auditing) |
| 3 | the phenomena classes underrepresented after rounds 1–2 — derived by reading the merged pool, not guessed |

Each round internally (llm-chat for the two model steps, session for the rest): read `LANDSCAPE.md` from disk → brainstorm 8–12 via llm-chat → filter on feasibility and compute cost → quick novelty search → deep-validate the leaders (full novelty check + devil's advocate) → rank by empirical signal.

**Merge.** Concatenate into one `## Ranked Ideas` section, then dedup — two ideas are the same when they share a **phenomenon *and* an internal object**, whatever the titles say. Target ~30; 24–36 is fine; below ~20 means the rounds collapsed and a fourth round is owed.

**Exclusion is by title.** Later rounds are steered by pasting earlier rounds' titles as a do-not-repeat list. There is no persisted banlist and no cross-invocation memory: re-running the skill on the same direction regenerates the same pool from scratch.

---

## 6. Selection (Phase 4.25)

**No model runs here.** All four steps are deterministic rules the orchestrator executes over scores already written by P3/P3.5/P4; nothing is re-judged and no llm-chat call is made.

1. **Veto** — every fatal design flaw from P4, regardless of impact.
2. **Rank** — impact → reviewer score → novelty.
3. **Take the top 10** — this fixes the P4.5 directory numbering; nothing downstream re-orders it.
4. **Spread check** — swap lowest-ranked duplicates for distinct phenomena.

Short of 10: **one** top-up round back through P2 → P4.25, then ship what survived and state the shortfall in `IDEA_REPORT.md`.

---

## 7. Phase 4.5 — the executor-facing plan

Ten `/research-refine-pipeline` invocations, in parallel, each writing into its own `claims/<NN>_<name>/`. The two halves run on **different models**: `/research-refine` drives its review–revise loop against **llm-chat**, then `/experiment-plan` — which declares no reviewer backend — builds the roadmap on the **session**.

- freeze a **Problem Anchor** to prevent scope drift
- refine method / testing approach against external LLM review, up to 5 rounds, until score ≥ 9
- emit a claim-driven experiment roadmap with ablations, budgets, run order

`EXPERIMENT_PLAN.md` carries **machine markers** that the executor reads:

| marker | meaning |
|---|---|
| `kind: phenomenon-validation` | identifies the **M0 gate** by field rather than by title; exactly one per plan |
| `depends_on: [M0, …]` | this milestone waits for the listed upstream milestones; every mechanism milestone declares `depends_on: [M0]` |
| `grid: {param: [v, …], …}` | Cartesian expansion; `cmd:` becomes a template with `${param}` substitution |
| `method_sensitive: [field, …]` | fields whose value depends on a mechanism submethod not yet chosen (`n_pairs`, `sites`, `metric`, `gpu_hours`) and must be re-bound before the run |
| `mechanism_strategy:` | top-level metadata naming the strategic direction |

**M0's four-state verdict** governs everything after it: `established` → run the mechanism milestones; `conditional` → scope them to where the phenomenon holds and tag the claim; `not-established` → stop and report a negative result; `inconclusive` → the gate itself is broken, fix and re-run. Never run mechanism work on an untested phenomenon.

**Failure isolation.** A failed refinement is recorded in that directory and in `IDEA_REPORT.md`; the other nine continue.

---

## 8. Phase 4.8 — `claim.json`

**Model: unassigned.** `SKILL.md` says *"Write one `claim.json` per directory"* and names no backend, so the reviewer-facing deliverable is written by whoever is orchestrating — the session — from artifacts llm-chat authored. See §2; this is the defect the rewrite's `WRITER` constant closes.

Seven keys, exactly these names, exactly this order, plain prose strings, `\n\n` for paragraph breaks:

```json
{ "Name", "Title", "Short Hypothesis", "Related Work", "Abstract", "Experiments", "Risk Factors and Limitations" }
```

**Write order: `Experiments` first**, then `Short Hypothesis`, `Related Work`, `Abstract`, `Risk Factors and Limitations`, then `Title` and `Name`. The rationale is that the ladder forces concreteness early — a claim that cannot be laddered is not ready to be written up.

**`Experiments`** is labelled paragraphs: Models → Benchmark/data → Conditions → Measurements → Experiment 1…k → Ablations and controls → Metrics.

**The ladder** — 1 the phenomenon happens at all, 2 correlational screening, 3 intervention moves the behavior, 4 matched controls and confound checks, 5 (optional) how far it holds. Experiment 1 is the M0 gate rewritten as prose, with the same four outcomes.

**Rung names and machine markers never surface.** «Phenomenon-validation», «localization», «M0», `kind:`, `method_sensitive` are scaffolding a reviewer cannot decode. Each experiment is headed by the hypothesis it tests.

**Numerical consistency is cross-file.** The same quantity must hold one value and one unit across `claim.json`, `EXPERIMENT_PLAN.md`, and `FINAL_PROPOSAL.md` — checklist item 8 is a three-file comparison. A `method_sensitive` field is one number awaiting re-binding, not a different number per file.

**Nothing points at a file the reviewer does not have** — no «see `EXPERIMENT_PLAN.md`», no «idea #3 in the batch», no reference to the other nine claims. `claim.json` is always English.

**Quality checklist** — 8 items across three groups: *is the idea new* (1 three nearest works separated at the level of a finding, 2 the expert's prior written down first), *would it matter* (3 a named consumer on both branches, 4 stakes survive stripping the setting + a breaking case), *can it be settled* (5 Experiment 1 can kill the claim, 6 every mundane explanation paired with a control, 7 every hypothesis has its undecidable band, 8 every number agrees across the three files).

Two restarts on the same idea → mark it `blocked` in `IDEA_REPORT.md` and promote the highest-ranked eliminated idea into the slot.

---

## 9. Artifacts

```
idea-stage/
  RESEARCH_LIT.md          # raw retrieval dump, audit-only
  LANDSCAPE.md             # synthesized landscape
  IDEA_REPORT.md           # all ~30 ideas, ranked, with eliminations — the batch index
claims/
  01_<name>/
    FINAL_PROPOSAL.md      # executor-facing: the refined method
    EXPERIMENT_PLAN.md     # executor-facing: milestones, grids, machine markers
    claim.json             # ⭐ the file a human reviewer reads
  02_<name>/
    …
  10_<name>/
```

Three files per claim, at two levels of detail and in two registers. `claim.json` is the product; the other two are the plan it was written from, and they must stay numerically in sync with it.

`IDEA_REPORT.md` is a Markdown index, not structured data: scores, ranks, and eliminations live in prose sections (`## Ranked Ideas`, `## Eliminated Ideas`) and are re-parsed by reading.

**Ends at `claim.json`.** Once all ten directories hold their three files, stop — do not implement, launch, or queue an experiment, and do not chain into another skill.

---

## 10. What the rewrite changed

Read alongside `skills/hypothesis-batch-new/pipeline.md`.

| | this version | current version |
|---|---|---|
| **Parameters** | none — hardcoded 30 → 10 | `ROUNDS` / `N_BEHAVIORS` / `TOP_N` / `COLD_N` / `WRITER` / `IMPACT_WEB` |
| **Input** | a research direction | the user's whole `INTENTION`, carried verbatim into every round and the final tiebreak |
| **What is mined** | "ideas" — phenomenon and mechanism fused at generation time | **behaviors only**; mechanism attaches in P6, to the `TOP_N` alone |
| **Generation** | 3 × `/idea-creator`, all taxonomy-primed | every round generates **twice** — cold (taxonomy withheld) then guided |
| **Round memory** | earlier titles pasted as exclusions; nothing persists | library written to disk each round, banlist rebuilt from it, accumulates across invocations |
| **Pool store** | `IDEA_REPORT.md` (Markdown prose) | `hypothesis_library.json` (structured, append-only, nodes never deleted) |
| **Novelty delta** | not a field | `innovation.beyond_transfer` / `method`, enforced by a delta filter that drops `transfer-only` before persisting |
| **Dedup** | on merge, by phenomenon + internal object | semantic, over both passes and the whole library, and **template collapse counts as duplication** |
| **Impact timing** | P3.5, a separate stage after novelty, always searched | inside the round loop, before persisting; `IMPACT_WEB = false` by default |
| **Authorship** | split three ways; `claim.json` unassigned | one `WRITER` (default `session`) authors both deliverables, never split across phases |
| **Evaluation** | each sub-skill's own default | `REVIEWER_BACKEND` = `llm-chat` explicitly, for every evaluation step, deliberately decoupled from `WRITER` |
| **Step 3 concurrency** | 10 claims refined in parallel | **serial** — claim `01` closes before `02` opens |
| **Per claim** | 3 files, machine markers in the plan | **`claim.json` only**; `EXPERIMENT_PLAN.md` / `FINAL_PROPOSAL.md` / `refine-logs/` forbidden, and so are the markers |
| **Numerical consistency** | across three files | **within one file** — strictly checkable |
| **Write order** | `Experiments` first | `Short Hypothesis` first, `Experiments` last, numbers originating upstream |

The through-line: **one design, written once.** This version maintains the same study at two levels of detail for two audiences, and spends checklist item 8 keeping them in sync. The rewrite ships only the reviewer's version, which is what removes the second copy, the machine markers, and the cross-file reconciliation in one move.

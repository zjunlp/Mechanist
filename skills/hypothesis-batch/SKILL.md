---
name: hypothesis-batch
description: "Batch pipeline for research hypotheses. The positional argument is the user's whole INPUT INTENTION. P1 generates candidates into `claim_0.json` in two serial passes by running two packaged ideation scripts: first the no-guide script, then the with-guide script. P2 rewrites each candidate's `Experiments` field in its own call, into `claim_1.json`. P3 assesses every candidate in `claim_1.json` with three built-in external-reviewer prompts for novelty, impact, and research quality, then reranks. P4 improves every candidate from its assessment, one file per iteration (`claim_2.json` … `claim_<REFLECTIONS+1>.json`). P5 is the Orchestrator's own rerank of the improved pool on impact first and novelty second — no scores, no model call — and ships the `TOP_N` to `claim.json`."
argument-hint: "<intention — what you want out of this topic> [— n-behaviors: N] [— primed-multiplier: M] [— top-n: K|all] [— writer: session|llm-chat]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__llm-chat__chat, mcp__mechanic-db__search_papers
---

# Workflow: Generate → Assess → Improve → Ship

Orchestrate the hypothesis stage for: **$ARGUMENTS**.

## Setup (once per machine)

P1 shells out to two Python scripts, so they need an interpreter with their
dependencies. If that conda env already exists, just activate it and use it —
otherwise build it once from `scripts/requirements.txt`:

```bash
conda create -n mechanist-ideation python=3.11 -y
conda activate mechanist-ideation
pip install -r "${MECHANIST_SCRIPTS_DIR:-$CLAUDE_PLUGIN_ROOT/scripts}/requirements.txt"
```

## Overview

Five phases, run non-interactively end to end. The candidate pool lives in one JSON array that is versioned by filename: `claim_0.json` is what P1 generated, P2 rewrites it into `claim_1.json`, which is what P3 scored, each P4 iteration writes the next `claim_<r+1>.json`, and P5 ships the survivors to `claim.json`.

```
P1  generation via packaged scripts ─────────────── IDEATION_MODEL ★★ → claim_0.json
    ├─ P1.1  run `perform_ideation_temp_free_mechanic_s2_noguide.py` ·······  N_BEHAVIORS candidates
    └─ P1.2  run `perform_ideation_temp_free_mechanic_s2_with_guide.py` ····  PRIMED_MULTIPLIER × N_BEHAVIORS candidates

P2  improve the experiments (one candidate/call) ──── WRITER        → claim_1.json

P3  assess + rerank ───────────────────────────────── llm-chat ★    → claim_1.json (in place)
    ├─ P3.1  novelty / impact / review prompts per idea + revision notes
    └─ P3.2  rerank, write `rank` back

P4  improve from the assessment ───────────────────── WRITER        → claim_2.json … claim_<REFLECTIONS+1>.json
    (one file per iteration)
    └─ the outer loop repeats P3 → P4, REFLECTIONS times; P1 never repeats

P5  rerank on impact ▸ novelty, then cut to TOP_N ──── Orchestrator → claim.json
```

★ = the external LLM reviewer via llm-chat MCP. ★★ = `IDEATION_MODEL`, the model the packaged scripts run on — deliberately **not** `WRITER`, because P1 is the scripts' job and P2/P4 are the writer's. Everything marked `WRITER` is authored by the `WRITER` model; everything else the Orchestrator does is file I/O, ranking arithmetic, and the final cut.

**Deliverables.**

```
topic.md          # P1's input — the INTENTION, verbatim
claim_0.json      # P1's pool — every generated candidate, seven fields each
claim_1.json      # P2's experiment rewrite + P3's assessment and rank
claim_2.json      # P4 iteration 1
…
claim_<R+1>.json  # P4 iteration REFLECTIONS, reranked by P5
claim.json        # ⭐ the TOP_N, rank-ordered, seven fields each
p1_logs/          # P1 run logs — the only record of the Semantic Scholar hits
search_cache/     # P1 mechanic-db responses, one timestamped archive per search
```

## Constants

| Constant | Default | Meaning | Override |
|---|---|---|---|
| `INTENTION` | positional arg, verbatim | the whole user intention — direction + angle + constraint + wanted result | required; no flag |
| `TOPIC` / `topic_slug` | distilled from `INTENTION` | library identity only — the cross-topic guard when a run is filed alongside others | not passable |
| `N_BEHAVIORS` | 10 | seed candidates in P1.1 | `— n-behaviors: N` |
| `PRIMED_MULTIPLIER` | 3 | P1.2 candidate-count multiplier; P1.2 generates `PRIMED_MULTIPLIER × N_BEHAVIORS` | `— primed-multiplier: M` |
| `GEN_REFLECTIONS` | 1 | **inner reflection** — reflection turns allowed on one candidate *after* its first generation turn, inside the P1 scripts' loop; total turns per candidate = `1 + GEN_REFLECTIONS` | not passable |
| `REFLECTIONS` | 1 | **outer reflection** — maximum number of P4 improvement iterations over the whole pool | not passable |
| `TOP_N` | 10 | ranked behaviors that get into `claim.json`; fixes `01`…`NN` ordering | `— top-n: K` or `all` |
| `WRITER` | **session** | authors the improvements in P2 and P4 — **not** the candidates | `— writer: session\|llm-chat` |
| `IDEATION_MODEL` | `claude-opus-4-8` | the model the P1 scripts run on | `export IDEATION_MODEL` |
| `MAX_SUBAGENTS` | `max(3, ⌊(PRIMED_MULTIPLIER + 1) × N_BEHAVIORS / 10⌋)` — **4** at the defaults | ceiling on how many subagents any single phase from P2 on may open | derived; not passable |
| `OUTPUT_DIR` | `.` | where `topic.md`, every `claim_*.json`, `p1_logs/`, and `search_cache/` land | — |

Argument shape: `"<intention>" — <key>: <value>, <key>: <value>`. Only a ` — ` immediately followed by `key: value` opens the option list; an em dash followed by prose belongs to the intention.

Total candidates generated by P1 = `N_BEHAVIORS` (P1.1) + `PRIMED_MULTIPLIER × N_BEHAVIORS` (P1.2) — 40 at the defaults. Nothing is eliminated before P5; the pool only gets scored, reranked, and rewritten.

**Two reflection levels, not one.** Both count *iterations after the thing they iterate on*, never the first pass:

- `GEN_REFLECTIONS` is **inner** — how many times one candidate is reflected on after it has been generated, inside P1. At the default `1`: turn 1 generates, turn 2 reflects and commits. Total turns per candidate = `1 + GEN_REFLECTIONS`; `0` means generate and finalize in one turn, with no search.
- `REFLECTIONS` is **outer** — how many times the whole pool is re-improved in P4 after P1 produced it. At the default `1`: `claim_1.json` is improved once into `claim_2.json`.

They are independent, and neither is derived from the other. Neither counts the pass it iterates on, so a constant of `N` always means `N` extra passes, never `N` total.

**Example**

```
/hypothesis-batch "how LLMs handle retracted information in multi-turn dialogue — I want claims I can test on 7B open models"
/hypothesis-batch "sycophancy vs. factual competence" — n-behaviors: 6, primed-multiplier: 3, top-n: 5
```

## The idea record

Every element of every `claim_*.json` carries **these seven fields, exactly these names, exactly this order** — this is the idea schema, and it is stable across every phase and every file:

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

- **`Name`** — A short descriptor of the idea. Lowercase, no spaces, underscores allowed.
- **`Title`** — A catchy and informative title for the proposal.
- **`Short Hypothesis`** — A concise statement of the main hypothesis or research question. Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.
- **`Related Work`** — A brief discussion of the most relevant related work and how the proposal clearly distinguishes from it, and is not a trivial extension.
- **`Abstract`** — An abstract that summarizes the proposal in conference format (approximately 250 words).
- **`Experiments`** — A list of experiments that would be conducted to validate the proposal. Ensure these are simple and feasible. Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.
- **`Risk Factors and Limitations`** — A list of potential risks and limitations of the proposal.

Working files (`claim_0.json` … `claim_<R+1>.json`) carry bookkeeping **after** the seven fields, never renaming or reordering them. There is no id: **a candidate's identity is its position in the array.** Every phase rewrites the pool as a whole and preserves order, so position `k` is the same idea in every file; only P3.2 and P5 reorder, and they reorder the entire array at once. Which script produced a candidate is likewise positional — the first `N_BEHAVIORS` records are P1.1's, the rest are P1.2's.

| field | written by | contents |
|---|---|---|
| `novelty` | P3.1 | `{score, reasoning}` from the novelty prompt |
| `impact` | P3.1 | `{score, reasoning}` from the impact prompt |
| `review` | P3.1 | `{score, reasoning}` from the research-quality prompt |
| `revision_notes` | P3.1 | merged, deduplicated field-level edits synthesized from the three reviewer prompts — P4's input |
| `rank` | P3.2 / P5 | 1-based position in the current ranking |

`claim.json` (P5) carries **only the seven fields**, in rank order.

**Writing is atomic and incremental.** Write `<file>.tmp` and `os.replace` it onto the target, and flush after **every** finalized idea rather than at the end of a phase — a run that is interrupted keeps everything it had finished. JSON is written with `indent=4`.

## P1: Generation

P1 is script-driven. The Orchestrator prepares the inputs, then runs two packaged ideation scripts in series. Both read `topic.md` and both write `claim_0.json`, the seed pass first and the guided pass appending after it.

Use these packaged scripts, which ship with this plugin under its own `scripts/` directory:

- `$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_noguide.py`
- `$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_with_guide.py`

Everything they import is vendored beside them in `$SCRIPTS_DIR/ai_scientist/` — the two base ideation modules, `llm.py`, the three search tools, and the `mechanic_db_search.py` the retrieval shells out to. No file outside `$SCRIPTS_DIR` is read at run time. What still comes from outside is the *Python environment*: `anthropic`, `openai`, `backoff`, `httpx`, `requests`, and `tiktoken` — the `scripts/requirements.txt` conda env from Setup, which is what `$PY` resolves to.

Read the script you are about to run before invoking it. Do not re-implement its search loop in the skill. Let the script handle generation, literature retrieval, de-duplication, and append/flush behavior.

**These two scripts are reference implementations, and their logic is frozen.** You may adapt them, or the environment around them, on exactly these axes: output and cache paths, working directory, environment variables, model name and API endpoint, timeouts, retry limits, and logging. You may **not** touch what makes them these scripts: the generation/reflection loop, the system prompt and the idea-generation prompt, the tool set and the 15 + 5 retrieval quota, the `FinalizeIdea` parsing, or the append/flush semantics. A "repair" that changes any of those is not a repair — stop and report instead.

### Shared script behavior

- Each script performs the candidate-level literature search itself.
- Each candidate uses mechanic-db plus Semantic Scholar, with the script's own de-duplication before the prompt is fed back to the model.
- mechanic-db contributes up to 15 papers; Semantic Scholar contributes up to 5 more papers.
- The scripts append incrementally and atomically to `claim_0.json` — one `.tmp` write plus `os.replace` per finalized idea.
- Pass `--num-reflections` as `1 + GEN_REFLECTIONS`, because the scripts count total turns while this skill's constant counts only extra reflection turns after the first generation turn.
- **The scripts write the seven fields and nothing else.** The pool carries no bookkeeping at all; P3 is the first phase to add any.
- **`--max-num-generations` counts *new* ideas, not total.** Each script loads `claim_0.json` first and stops when it has added that many on top of what was already there. This is what makes P1.2 append rather than overwrite — and it is also why a relaunch must be given the *shortfall*, never the original number.
- P1 is fully serial: run P1.1 to completion first, then P1.2 once against the same `topic.md`, so the guided pass can diverge from the no-guide candidates already on disk.

### Preparation

1. Write `topic.md` in `OUTPUT_DIR` with the full `INTENTION` as its contents — this is P1's only input. The output name is set explicitly with `--output-file`, so the input's name has no bearing on it.
2. `mkdir -p "$OUTPUT_DIR/p1_logs" "$OUTPUT_DIR/search_cache"`.
3. Source the environment. `p1_env.sh` ships in `scripts/`, so nothing is generated per run — but a fresh shell inherits none of it, so **every shell that launches or inspects a pass opens with this preamble**:

```bash
export OUTPUT_DIR="<the run directory>"
source "${MECHANIST_SCRIPTS_DIR:-$CLAUDE_PLUGIN_ROOT/scripts}/p1_env.sh"
```

It leaves `$PY`, `$SCRIPTS_DIR`, and `$IDEATION_MODEL` set, plus every API and proxy variable the scripts read.

**The settings live in `scripts/ideation_config.json`** — model, gateway key and base URL, the Semantic Scholar key, the mechanic-db key / URL / quotas, the retry multiplier, and the proxy. The keys ship as `<YOUR_...>` placeholders and must be filled in once before the first run; the interpreter is not a setting — `p1_env.sh` locates the conda env from Setup by name, so **a pass runs correctly whether or not that env is active in the calling shell**; `export IDEATION_CONDA_ENV=<env name>` aims it at a differently named env, and `export IDEATION_PYTHON=<absolute interpreter path>` bypasses the search entirely. `p1_env.sh` exports each of them **only if the shell has not already set it**, so change a setting with `export VAR=...` rather than by editing the file; `export IDEATION_CONFIG=<path>` swaps the whole set for another JSON. The file is plain text in the repo — treat the keys in it accordingly, and never commit them back.

`MECHANIC_DB_API_KEY` and `MECHANIC_DB_BASE_URL` reach the search service three hops down — the packaged `mechanic_db_semantic_scholar.py` builds `MechanicDBSearchTool`, which subprocesses `ai_scientist/mechanic_db_search.py`, which reads both from the environment. The environment is inherited the whole way, so an `export` here is what the service actually sees.

### P1.1: Seed pass — unprimed

Read `$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_noguide.py`, then launch it **in the background** — never in the foreground; see the timing note under Monitoring:

```bash
export OUTPUT_DIR="<the run directory>"; source "${MECHANIST_SCRIPTS_DIR:-$CLAUDE_PLUGIN_ROOT/scripts}/p1_env.sh"
nohup "$PY" "$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_noguide.py" \
  --workshop-file "$OUTPUT_DIR/topic.md" \
  --output-file "$OUTPUT_DIR/claim_0.json" \
  --model "$IDEATION_MODEL" \
  --max-num-generations "$N_BEHAVIORS" \
  --num-reflections "$((1 + GEN_REFLECTIONS))" \
  >> "$OUTPUT_DIR/p1_logs/p1.1_noguide.log" 2>&1 &
```

This is the no-guide pass; it writes `N_BEHAVIORS` candidates into `claim_0.json`. Monitor it to completion.

If the pool is smaller than `N_BEHAVIORS`, top up: relaunch the identical command with `--max-num-generations` set to what is still missing. At most two top-up attempts, then log the shortfall and go on with the smaller pool.

When P1.1 is done, read the pool size once — everything in `claim_0.json` at this moment is P1.1's, everything P1.2 appends after it is P1.2's, and that position is the only provenance the pipeline keeps or needs:

```bash
"$PY" -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$OUTPUT_DIR/claim_0.json"
```

### P1.2: Primed pass

Read `$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_with_guide.py`, then launch it the same way:

```bash
export OUTPUT_DIR="<the run directory>"; source "${MECHANIST_SCRIPTS_DIR:-$CLAUDE_PLUGIN_ROOT/scripts}/p1_env.sh"
nohup "$PY" "$SCRIPTS_DIR/perform_ideation_temp_free_mechanic_s2_with_guide.py" \
  --workshop-file "$OUTPUT_DIR/topic.md" \
  --output-file "$OUTPUT_DIR/claim_0.json" \
  --model "$IDEATION_MODEL" \
  --max-num-generations "$((PRIMED_MULTIPLIER * N_BEHAVIORS))" \
  --num-reflections "$((1 + GEN_REFLECTIONS))" \
  >> "$OUTPUT_DIR/p1_logs/p1.2_with_guide.log" 2>&1 &
```

This is the with-guide pass — it embeds the behavior-discovery and mechanism-discovery guides in its own first-turn prompt. It must run **after** P1.1 and appends onto the existing `claim_0.json`, so the guided pass diverges from the no-guide candidates already written.

Its target is `PRIMED_MULTIPLIER × N_BEHAVIORS` **new** candidates on top of what P1.1 left, so its target total is the size you read at the end of P1.1 plus that number. Top up on the shortfall against that total, at most twice.

### Monitoring: every 15 minutes

A full P1 runs for hours, so launch each pass detached and never wait on one in the foreground. Check in every 15 minutes: how many candidates are in the pool, and what the tail of that pass's log says. It is healthy as long as the count is growing, or the count is flat while the log keeps moving — a long search and a rate-limit backoff both look like that.

Act only when both are frozen across two checks in a row, or the process has died early. Then read the log tail and fix whatever it names — a credential or model-name problem, the mechanic-db service being down, a rate limit that will not clear — and relaunch. Repairs are always to the environment, never to the script's logic. Relaunching is safe because the scripts reload the pool first, but pass the **shortfall** rather than the original number, since `--max-num-generations` counts new ideas; and never lower a target just to make a pass finish.

### What P1 leaves on disk

```
$OUTPUT_DIR/
  topic.md                            # input: the INTENTION, verbatim
  claim_0.json                        # output: the pool, seven fields per candidate
  p1_logs/
    p1.1_noguide.log                  # full stdout: every query, every paper returned,
    p1.2_with_guide.log               #   every ACTION/ARGUMENTS, every failure trace
  search_cache/                       # = $MECHANIC_DB_CACHE_DIR
    mechanic_db_result.json           # the most recent search — overwritten every call
    <YYYYmmdd_HHMMSS>_result.json     # one timestamped archive per search — the durable
                                      #   record of what mechanic-db returned
```

Two things to know about the search record:

- **The mechanic-db side is archived, the Semantic Scholar side is not.** S2 hits reach the prompt but are never written to a file; the pass log is their only record. That is why the logs are a deliverable and not scratch.
- **`search_cache/` only lands in `OUTPUT_DIR` because `p1_env.sh` sets `MECHANIC_DB_CACHE_DIR`.** Left unset, the tool defaults to `$(pwd)/mechanic_db_cache` and the archives scatter into whatever directory the pass happened to be launched from.

## P2: Improve Experiment

`WRITER` rewrites each candidate's `Experiments` field in its own call, reading `claim_0.json`
and writing `claim_1.json`, after generation and before the first assessment. P1 commits `Experiments` as one
of seven fields in a single turn, where it competes for attention with the hypothesis, the
abstract, and the related work; a call that does nothing else, against an idea already written
down, is what makes the experiments specific enough for P3 to judge.

One call per candidate, carrying that candidate's current seven fields:

```
Experiments.

Rewrite `Experiments`. Touch `Short Hypothesis` and `Risk Factors and Limitations` only where a
number has to stay consistent with it; leave the other four fields exactly as they are.

The experiments test the hypothesis as written; they do not enlarge it. Do not argue here
for anything `Short Hypothesis` does not claim, and do not quietly widen the claim's scope to
make the experiment set look complete.

Every assertion in `Short Hypothesis` needs an experiment that establishes it. An assertion with
no experiment behind it either gains one or does not belong in the hypothesis.

Every experiment states what it tests; the data it uses — an existing set used as is, an existing
set adapted, or one built from scratch, with its source, how many items exist, how many you will
use, and why if fewer; the model it runs on — family and parameter scale, what is frozen and what
is trainable, the key hyperparameters and the seeds; the systems compared; the decisive metric
first; the result that would count as convincing; and what a negative result would mean. Give each
threshold the band where the measurement cannot decide, in that threshold's own units, and say
what follows for the hypothesis when a result lands there — before the data, not after.

Plan evidence; never write a result as though it were already measured. Stay inside what an
academic lab can afford, and state the scale plainly enough that a reviewer can check it.

The reviewer reads this JSON and nothing else, so it has to stand on its own: head each
experiment by the hypothesis it tests — `Experiment 1 (H1 — <name>):` — and use no term or
pointer they would have to look up somewhere else.

Respond with ACTION: FinalizeIdea and the complete idea JSON.
```

- **Runs once per invocation**, outside the P3 → P4 loop.
- **Writes the next file, never in place** — `claim_0.json` stays exactly as P1 left it, and `claim_1.json` keeps its candidates in the same order.

Flush each candidate as it finalizes.

## P3: Assess and rerank

Runs on **llm-chat** using three built-in reviewer prompts. Nothing is eliminated here.

### P3.1: Three reviewer prompts per idea

Read `claim_1.json` and, for **every** candidate, call the same external reviewer three times, once per prompt.

**Prompt A: novelty**

Carry `Title`, `Short Hypothesis`, `Related Work`, and `Experiments`.

Before the reviewer call, use `WebSearch` as needed based on the candidate's contents to gather information that helps judge novelty, especially the closest overlapping work, baseline families, and the likely delta. Pass a short search brief into the reviewer prompt together with the proposal text.

```
You are reviewing a research idea for novelty. Judge from the proposal text alone.

If a search summary is provided, use it as additional context when identifying the closest prior work and the actual delta.

First extract the 3-5 core technical claims that would need to be novel:
- What problem does it solve?
- What is the proposed mechanism or explanation?
- What makes it different from obvious baselines?
- Is the novelty in the finding, the mechanism, the setting, the dataset, or the problem definition?

Then judge the proposal against the novelty standard used in research triage:
1. Does it propose a genuinely new theory, task, explanation, mechanism, finding, setting, dataset, or problem definition?
2. If it studies an existing idea in a new setting, is that setting meaningfully different enough that the result itself could be novel?
3. Relative to the proposal's own related work, is the core claim non-trivial rather than an obvious next step?
4. What is the closest prior work family or baseline, and what is the actual delta?

Return strict JSON:
{
  "novelty": {
  "score": <integer 1-10>,
    "reasoning": "<brief justification>"
  },
  "revision_notes": [
    "<field-level edit 1>",
    "<field-level edit 2>"
  ]
}
```

**Prompt B: impact**

Carry `Title`, `Short Hypothesis`, and a one-line description of the behavior/problem being studied.

Before the reviewer call, use `WebSearch` as needed based on the candidate's contents to gather information that helps judge impact, especially who cares about the problem, where it matters, and whether the result would likely influence follow-up research or practice. Pass a short search brief into the reviewer prompt together with the proposal text.

```
You are reviewing a research idea for impact. Judge from the proposal text alone.

If a search summary is provided, use it as additional context when judging importance, reach, and the strongest "so what?" objection.

First identify the impact-bearing claims:
- What behavior, phenomenon, or problem is actually under study? Focus on the problem, not the method.
- Who would have this problem or care about the result?
- What downstream research, applications, or practices would change if the result holds?
- Is the reach narrow, field-wide, real-world, or cross-disciplinary?
- What is the single strongest one-line case for why this matters?

Then assess the idea along these five impact dimensions:
1. Important problem — is this a real need or mostly a niche curiosity?
2. Uptake / citation — would follow-up work build on, use, or cite this?
3. Direction-shifting — could it change how people think about or approach an area?
4. Real-world reach — does it matter for applications, industry, society, or cross-disciplinary use?
5. Phenomenon value — even if the method is simple, does it reveal an important phenomenon?

Apply the "so what?" test explicitly: if the result came out either way, would serious researchers or practitioners change what they do?

Return strict JSON:
{
  "impact": {
    "score": <integer 1-10>,
    "reasoning": "<brief justification>"
  },
  "revision_notes": [
    "<field-level edit 1>",
    "<field-level edit 2>"
  ]
}
```

**Prompt C: research quality**

Carry the full seven fields.

```
You are reviewing a research proposal for technical quality and testability. Judge from the proposal text alone.

Act like a strict senior ML reviewer. Evaluate:
1. Logical gaps or unjustified claims.
2. Whether the core hypothesis is precise, falsifiable, and appropriately scoped.
3. Whether the related work is specific enough to position the contribution.
4. Whether the experiments are specific, feasible, properly controlled, and actually capable of testing the stated claim.
5. What key experiments, ablations, controls, or analysis are missing.
6. Narrative weaknesses: where the story is underspecified, overclaimed, or hard to defend.
7. Whether the contribution seems strong enough for a serious ML venue if executed well.
8. What the minimum viable edits are to make the proposal fundable or submission-ready.

Return strict JSON:
{
  "review": {
    "score": <integer 1-10>,
    "reasoning": "<brief justification>"
  },
  "revision_notes": [
    "<field-level edit 1>",
    "<field-level edit 2>"
  ]
}
```

Write back into that candidate's record:

- `novelty` — the novelty prompt's `score` and `reasoning`.
- `impact` — the impact prompt's `score` and `reasoning`.
- `review` — the research-quality prompt's `score` and `reasoning`.
- `revision_notes` — merge the three prompts' `revision_notes`, deduplicate them, and keep them as a concrete field-level edit list. This is the only field P4 is required to act on, so it must be actionable rather than evaluative.

Flush after each candidate is scored.

### P3.2: Rerank

Order the pool by **impact first, reviewer score second, novelty last** — impact dominates because a less-novel idea on an important problem outranks a novel idea nobody needs; the research-quality score breaks impact ties; novelty is the final tiebreak. Write the 1-based position into each record's `rank` and rewrite `claim_1.json` in rank order.

## P4: Improve

This is the **outer** reflection level. `WRITER` rewrites every candidate from its own assessment. Iteration `r` reads `claim_<r>.json` and writes `claim_<r+1>.json`, for `r = 1 … REFLECTIONS`; the suffix increments with every iteration and no earlier file is ever overwritten. At the default `REFLECTIONS = 1` the phase runs once, reading `claim_1.json` and producing `claim_2.json`.

**What the outer loop repeats is the pair `assess → improve`, never generation.** P1 runs once per invocation; from there:

```
for r = 1 … REFLECTIONS:
    assessment on claim_<r>.json      # P3's procedure: P3.1 three reviewer prompts + P3.2 rerank
    improve into claim_<r+1>.json     # this phase
then P5: rerank claim_<REFLECTIONS+1>.json, then cut to TOP_N → claim.json
```

Iteration 1's assessment is the P3 pass that already ran on `claim_1.json` — it is not re-run. Every later iteration needs its own pass, because `revision_notes` written against `claim_<r-1>.json` describe edits the writer has already made. So a run performs `REFLECTIONS` assessment passes in total: P3, plus one before each iteration after the first. At the defaults that is one — P3. P5 is not an assessment pass; it only ranks.

One call per candidate, carrying that candidate's current seven fields and its `revision_notes`:

```
Round {r}/{REFLECTIONS}.

In your thoughts, first carefully consider the quality, novelty, and feasibility of the proposal you just created.
Include any other factors that you think are important in evaluating the proposal.
Ensure the proposal is clear and concise, and the JSON is in the correct format.
Do not make things overly complicated.
In the next attempt, try to refine and improve your proposal.
Stick to the spirit of the original idea unless there are glaring issues.

If you have new information from tools, such as literature search results, incorporate them into your reflection and refine your proposal accordingly.

Results from your last action (if any):

{revision_notes from the latest assessment}
```

- **Iteration 1** works from P3's assessment of `claim_1.json`. **Later iterations** work from the assessment pass run on `claim_<r>.json` at the top of that iteration, and additionally carry a verbatim summary of what the previous iteration changed, so the writer does not re-litigate an edit it already made.
- **The final iteration** (`r == REFLECTIONS`) appends the forcing sentence: *"This is the FINAL round for this proposal. You MUST now finalize: respond with ACTION: FinalizeIdea and the complete idea JSON in ARGUMENTS."*
- **P4 issues no searches.** The input for this phase is the latest assessment material already condensed into `revision_notes`. That is what fills the `Results from your last action` slot.
- **Stick to the spirit of the original idea.** An improvement that replaces the phenomenon is a new candidate, not a repair — position `k` must still hold the idea it started as.
- `novelty` / `impact` / `review` / `revision_notes` / `rank` are dropped from the new file and rewritten by the next assessment; order is preserved so position still identifies the candidate. The final iteration's file gets no new assessment — it carries the seven fields only, and P5 adds `rank`.

Flush each rewritten candidate as it finalizes.

## P5: Rerank and ship

**No re-assessment.** No reviewer prompts, no scores, no llm-chat. The Orchestrator reads `claim_<REFLECTIONS+1>.json` and ranks it itself.

1. **Rerank on two criteria, in priority order — `impact` first, `novelty` second. Nothing else.** Impact dominates: a less-novel idea on an important problem outranks a novel idea nobody needs. Novelty only separates candidates whose impact is comparable. Read every candidate's seven fields as they now stand and order the whole pool best first. Write the 1-based position into each record's `rank` and rewrite `claim_<REFLECTIONS+1>.json` in rank order.

   **Rank from the content of `claim_<REFLECTIONS+1>.json`, never from an earlier file's scores.** The `novelty` / `impact` / `review` numbers in `claim_1.json` judged the draft P4 has since rewritten.
2. **Cut to `TOP_N`.** Take the top `TOP_N` records in rank order (`— top-n: all` takes every record; a pool smaller than `TOP_N` simply yields fewer).
3. **Write `claim.json`.** A JSON array of the selected records in rank order, each stripped to **the seven fields only**, `indent=4`, written atomically.

Log one line per shipped claim: `[claim] <NN> — "<Title>"`.

**This is the end of the workflow.** Once `claim.json` is on disk, stop. Do not implement, launch, or queue any experiment, and do not chain into another skill.

## Key Rules

- **Never block on the user.** Run the whole pipeline start to finish without waiting for input.
- **The seven fields are a contract.** Same names, same order, plain prose strings, in every file. Bookkeeping is appended after them, never mixed into them, and never present in `claim.json`.
- **One candidate per call, from a fresh context**, in P2 and P4. P1 needs no such rule — the packaged scripts are serial by construction, one candidate loop at a time. Batching is what makes a pool of near-duplicates.
- **`WRITER` never splits across P2 and P4.** Those two phases must run on the same model; if they did not, the improvements have more than one author. P1 is exempt by design — the packaged scripts run on `IDEATION_MODEL`, and that is not a defect to repair.
- **The packaged scripts' logic is frozen.** Paths, environment, model, endpoint, timeouts, retries, and logging are adjustable; the generation loop, the prompts, the tool set, the retrieval quota, and the append/flush semantics are not. See P1.
- **Every phase from P2 on has a subagent budget.** No phase may open more than `MAX_SUBAGENTS` subagents — `max(3, ⌊(PRIMED_MULTIPLIER + 1) × N_BEHAVIORS / 10⌋)`, 4 at the defaults. Split the pool into at most that many slices, one subagent per slice, each working its slice **one candidate at a time**; the per-candidate rules above hold inside a slice, so a slice is a queue, never a batch. The budget is per phase, not per run — P3 spends its own, P4 spends its own. P1 spends none: it runs two scripts.
- **Assessment is never routed through `WRITER`.** P3 runs on llm-chat so that the model scoring did not write what it scores. P5 is exempt — it assigns no scores, only an ordering.
- **Flush after every finalized idea**, atomically. An interrupted run keeps its finished work.
- **Nothing is eliminated before P5.** P3 scores and reranks; P4 repairs; only the `TOP_N` cut removes anything, and it removes it from `claim.json`, not from the working files.
- **A long pass is monitored, never waited on.** P1's two passes run detached and get checked every 15 minutes; a repair fixes the environment and relaunches on the shortfall, and never lowers a target to declare a pass finished.
- **File suffixes are the version history.** `claim_0.json` is generation, `claim_1.json` is the experiment rewrite, `claim_<r+1>.json` is improvement iteration `r`, `claim.json` is the deliverable. Never overwrite an earlier iteration.

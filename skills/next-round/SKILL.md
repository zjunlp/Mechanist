---
name: next-round
description: "Between-round transition helper for multi-round /auto exploration. Archives the just-finished round's outputs into rounds/round_<N>/ and drafts the next round's task.md with recommended behavior-source/mechanism params, by reading the orchestrator-owned Global Exploration Memory (research_memory.json). Use after a /auto round completes and you want to start a new round — either exploring a NEW behavior (new-behavior) or a NEW mechanism for an already-found behavior (new-mechanism). Reads memory, never writes it."
argument-hint: "[new-behavior | new-mechanism <behavior-id>]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Next Round — Archive + Draft the Next `task.md`

You help the user move from one `/auto` round to the next in a multi-round research program. **The user decides what to do; you only assist.** You do exactly three things:

1. **Archive** this round's outputs into `rounds/round_<N>/`.
2. **Draft** the next round's `task.md` (a starting point the user edits), with recommended `BEHAVIOR_SOURCE` / `MECHANISM` params.
3. **Report** what you did and what the user should run next.

You **read** the Global Exploration Memory (`research_memory.json`) for context and recommendations, but you **never write it** — that file is owned solely by `/auto` (see `skills/auto/SKILL.md` → "Global Exploration Memory"). You archive the just-finished round into `rounds/round_<N>/` where `<N>` is the round number resolved in Step 1.

## The two re-run intents

The user's next round is one of (read `$ARGUMENTS`; if absent, recommend then confirm via `AskUserQuestion`):

| Intent | Means | Recommend running |
|---|---|---|
| **`new-behavior`** | explore a brand-new phenomenon | `/auto — behavior-source: discovery, mechanism: discovery` |
| **`new-mechanism <behavior-id>`** | keep an already-found behavior, try a different mechanism direction | `/auto — behavior-source: given, mechanism: discovery` (behavior written into the new `task.md`) |

The actual "don't redo concluded work" enforcement happens inside `/auto` (the claim agent reads `research_memory.json` by default). Your drafted `task.md` only needs to carry the direction, the recommended `behavior-source` / `mechanism`, and a human-readable summary of what's been explored.

## Workflow

### Step 0 — Preconditions

```bash
# This round's outputs must be present at the project root (not yet archived).
ls -d idea-stage refine-logs verify review-stage 2>/dev/null
[ -s CLAIMS_LEDGER.md ] && echo "ledger present" || echo "no ledger"
[ -s research_memory.json ] && echo "memory present" || echo "no memory"
[ -s task.md ] && echo "task.md present" || echo "no task.md"
```

- If **no round outputs** are present (`refine-logs/` etc. all absent), there is nothing to transition from — tell the user to run `/auto` first and stop.
- If **`research_memory.json` is absent** but round outputs exist, `/auto` did not reach its final memory hook (crashed, or the reproduction combo `given`+`given`). You can still archive and draft, but warn that memory-based recommendations and avoid-repeat will be unavailable this transition.

### Step 1 — Determine the round number and read memory

```bash
# Round number = highest existing archive slot + 1. Parse the numeric SUFFIX of
# rounds/round_<k>, not a count — a count recycles a slot when a middle archive was deleted
# (round_1, round_3 present, round_2 gone → count=2 → 3 collides with round_3). The
# multi-round guard guarantees prior rounds are archived before a fresh /auto, so max-suffix+1
# is the round whose outputs now sit at root — collision-free and INDEPENDENT of whether
# memory was written (not-established given-validation/discovery rounds record no mechanisms[] entry;
# reproduction-combo (given+given) rounds skip the memory write entirely).
MAXARCH=$(ls -d rounds/round_* 2>/dev/null | sed 's#.*/round_##' | grep -E '^[0-9]+$' | sort -n | tail -1)
[ -z "$MAXARCH" ] && MAXARCH=0
N=$(( MAXARCH + 1 ))
# Defensive cross-check: if memory records a higher round, trust it (a gap is safer than a clobber).
if [ -s research_memory.json ]; then
  MEM=$(jq '[ (.behaviors[].mechanisms[].round // empty), (.behaviors[].decided_in_round // empty) ] | max // 0' research_memory.json 2>/dev/null)
  [ -n "$MEM" ] && [ "$MEM" -gt "$N" ] 2>/dev/null && N=$MEM
fi
echo "round to archive: $N"
```

Read `research_memory.json` (when present) for: the overarching `direction`, the list of explored `behaviors[]` (`statement` + `status` + prose `behavior_conclusion` + `impact.assessment` / `recommendation`), and per behavior the tried mechanisms (each entry's `direction` + `family` + `headline` + per-claim `statement` / `method` / `conclusion`), plus `untried_mechanism_directions` per behavior and the root `untried_behavior_directions`. Judge whether a mechanism attempt is stably positive, stably negative, or still open (deferred / integrity-broken / mixed / under-power) from that entry's `headline` + every `claims[].conclusion` — the schema records prose findings, and that is where settlement lives.

Only rounds that produced a scientific outcome are recorded here — `/auto` writes nothing for `ended-needs-decision` exits. If the just-finished round happens to be one of those, memory reflects only the state up to the *previous* recorded round; the operational stop is documented in the archived round's `CLAIMS_LEDGER.md.round_end` for the user to inspect, but this skill does not consult it. Users who ran into a fixable stop are expected to apply the named `remedy` (in `task.md` or in the plan files) before invoking `/next-round`.

### Step 2 — Resolve the intent (+ recommend)

Parse `$ARGUMENTS`:
- `new-behavior` → intent = new-behavior.
- `new-mechanism <behavior-id>` → intent = new-mechanism for that behavior. If the id is omitted, default to the **most recent** behavior in memory.
- **Empty** → derive a recommendation from the just-finished round's outcome, then confirm with `AskUserQuestion` (skip the prompt only if the user clearly pre-stated intent elsewhere):

| Just-finished behavior's `status` (from memory) | Recommend |
|---|---|
| `not-established` | **new-behavior** — the phenomenon was refuted; don't keep mining mechanisms on it |
| `inconclusive` | **re-validate same behavior** — the test failed to decide (not a refutation); re-run the same behavior via `behavior-source: given-validation` (which re-opens the plan with a fixed/stronger M0 — more data, better contrast, correct model). Do *not* recommend `new-mechanism` (phenomenon unconfirmed) or `new-behavior` (not refuted). Only after repeated honest attempts stay inconclusive → park it in `untried_behavior_directions` and move on |
| `established` / `conditional` AND a fresh mechanism direction remains — either untried, or previously attempted but the prose reading of its `headline` + `claims[].conclusion` is still open (deferred, integrity-broken, mixed / partial, under-power) | **new-mechanism** (same behavior) — go deeper with a fresh or unresolved direction |
| `established` / `conditional` AND every attempted `(direction, family)` reads as stably positive or stably negative in prose, with no untried directions left | **new-behavior** — move on to a new phenomenon |

Present the recommendation as the first option; the user always decides. Once resolved, set `INTENT` to either `new-behavior` or `new-mechanism` (and remember the chosen `<behavior-id>` for new-mechanism) — Step 3 reads `INTENT` to decide whether `data/` + `cache/` are kept or archived, and Step 4 reads it to shape the draft. **A "re-validate" recommendation (last round's behavior was `inconclusive`) resolves mechanically to `INTENT=new-mechanism`** — it keeps the same behavior (and its `data/`/`cache/`), but Step 4's draft focuses on strengthening the M0 phenomenon test rather than choosing a new mechanism direction.

### Step 3 — Archive this round

Use a **keep-list, not an allowlist**: enumerate what must *stay*, and archive everything else at the project root into `rounds/round_<N>/`. An allowlist of "things to move" silently goes stale every time the pipeline gains a new output type (it has already missed `experiments/`, `results/`, `logs/`, `cache/`, `.mechanist/`); a keep-list is immune to that.

**Keep-list (never archived):**
- Config / tooling: `.claude/`, `.mcp.json`, `.git/`, `.gitignore`
- Cross-round memory (orchestrator-owned): `research_memory.json`
- The archive root itself: `rounds/`
- Notification archive (cross-round, append-only): `notification/` — the `/notify` skill's briefing log stays at root across rounds, never moved into `rounds/round_<N>/`
- `task.md` — a *copy* goes into the archive, but the live file stays (Step 4 replaces it)

**Always archived (per-round provenance):**
- Paper-search cache: `mechanic_db_cache/` — moved into `rounds/round_<N>/` every round. Each round's literature search reflects that round's direction/behavior, so the cache is round-specific evidence to preserve, not a cross-round resource to reuse. (It falls into the "everything else" sweep below automatically now that it is off the keep-list; called out here so the policy is explicit.)

**Intent-dependent keep (stimuli / activation caches):**
- **`new-mechanism`** (same behavior next round) → **also keep** `data/` and `cache/` so the next round reuses the same stimuli/activations instead of regenerating them.
- **`new-behavior`** → **archive** `data/` and `cache/` (a new phenomenon needs new data).

**Everything else at the project root is archived** — including `idea-stage/ refine-logs/ verify/ review-stage/ runs/ figures/ experiments/ results/ logs/ experiment_queue/ .mechanist/ mechanic_db_cache/ CLAIMS_LEDGER.md claims_ledger.json` and any future output type.

```bash
# Refuse to clobber an already-archived round. With the slot-based round number this is a
# safety net that should never fire on the normal path; if it does, the project state is
# ambiguous — HARD STOP. Do NOT mkdir, do NOT archive, do NOT continue to Step 4.
if [ -n "$(ls -A "rounds/round_${N}" 2>/dev/null)" ]; then
  echo "[next-round] ERROR: rounds/round_${N}/ already populated — refusing to clobber."
  echo "[next-round] NOT archiving and NOT drafting task.md. Resolve manually:"
  echo "[next-round]   • if round ${N} is genuinely already archived, there is nothing to do;"
  echo "[next-round]   • otherwise inspect rounds/ for a gap or mismatch before re-running."
  exit 3
fi
mkdir -p "rounds/round_${N}"

# Keep-list (config / memory / archive-root). mechanic_db_cache is NOT kept — it is
# archived per round (round-specific literature evidence) via the everything-else sweep.
keep=( .claude .mcp.json .git .gitignore task.md research_memory.json rounds notification )
# new-mechanism reuses stimuli + activation cache; new-behavior archives them.
[ "$INTENT" = "new-mechanism" ] && keep+=( data cache )

# Build the archive plan (everything at root not in keep-list), PRINT it, then move.
echo "[next-round] will archive → rounds/round_${N}/:"; move=()
for p in * .[!.]*; do
  [ -e "$p" ] || continue
  skip=0; for k in "${keep[@]}"; do [ "$p" = "$k" ] && skip=1 && break; done
  [ "$skip" = 1 ] && continue
  move+=( "$p" ); echo "    $p"
done
echo "[next-round] keeping at root: ${keep[*]}"
for p in "${move[@]}"; do mv "$p" "rounds/round_${N}/"; done
# Snapshot the round's task.md alongside its outputs (the live task.md is replaced in Step 4).
[ -e task.md ] && cp task.md "rounds/round_${N}/task.md"
echo "archived round ${N} → rounds/round_${N}/"
```

If a path is large and `mv` fails (e.g. cross-device), retry with `rsync -a --remove-source-files` — do not ask permission. Print the plan before moving so the user can eyeball it; if the user pre-flagged a path to keep/move differently, honor that over the defaults.

**If the clobber guard fired (`exit 3`): terminate the entire skill immediately — do not enter Step 4, do not overwrite `task.md`, do not report success.** Relay the error verbatim to the user and stop. Aborting here leaves the root outputs un-archived as-is (the next `/auto`'s multi-round guard will halt on them again, as intended), which avoids the deadlock of a draft-overwritten `task.md` sitting next to stranded prior-round outputs.

### Step 4 — Draft the next `task.md`

**Run this step only if Step 3 archived successfully (the clobber guard did not abort).**

Overwrite `task.md` at the project root with a **DRAFT** the user will edit. Keep it short; the avoid-repeat enforcement is `/auto`'s job, so this file just orients the user. Follow `task.md`'s existing language.

Template (fill from memory + the archived `task.md`):

```markdown
<!-- DRAFT for round <N+1> — generated by /next-round. EDIT before running /auto. -->
<!-- Recommended: /auto — behavior-source: <discovery | given | given-validation>, mechanism: discovery -->

# Research direction
<carry over the overarching direction from the previous task.md / memory `direction`>

<!-- new-mechanism only: state the behavior to keep, so behavior-source: given picks it up -->
## Behavior to investigate (this round)
<the chosen behavior's one-sentence statement — only for new-mechanism>

## Already explored (for reference — /auto will avoid re-doing these)
- Behavior B1 "<statement>" — status: <established|...>
  - Conclusion: <behavior_conclusion — what is now known about the phenomenon>
  - Impact: <impact.assessment — one-line case>; recommendation: <impact.recommendation>
  - Mechanisms tried: <direction> (<family>) — <headline (the actual finding + key number)>
    - Claims:
      - C1 — <statement> — <conclusion>
      - C2 — <statement> — <conclusion>
- Behavior B2 "<statement>" — status: ...; conclusion: ...
<!-- Pull behavior_conclusion / impact.assessment / mechanism headline / per-claim statement + conclusion from research_memory.json — show the substantive findings and paper-style conclusions (not PASS/FAIL labels, not raw ids), so the human (and the next /auto run) can build on them. Skip mechanisms whose (direction, family) has already been read as stably positive or stably negative — they add noise for the reader; keep the ones the user could realistically retry (deferred / integrity-broken / mixed / under-power). -->
<!-- new-mechanism: also list this behavior's untried_mechanism_directions as suggestions, and briefly note (from the tried mechanisms' conclusion prose) what has and hasn't been settled so the new direction is complementary. -->
<!-- new-behavior: this list is the set to avoid; consider untried_behavior_directions: <...> -->

## Notes
<one line: what this round should push on, per the recommendation>
```

- **new-behavior**: leave the "Behavior to investigate" section out; fill "Already explored" with all behaviors so the user (and `/auto`) avoid them; surface `untried_behavior_directions` as candidate starting points.
- **new-mechanism**: fill "Behavior to investigate" with the chosen behavior verbatim (this is what `behavior-source: given` reads), and list as suggestions its `untried_mechanism_directions` **plus any direction left `inconclusive`** (unresolved, so still a valid retry target).
- **re-validate (behavior `inconclusive`)**: fill "Behavior to investigate" with the same behavior; in Notes, point to the M0 weakness from `behavior_conclusion` and what to strengthen (data / contrast / model) so the re-run can resolve it. Recommended param is `behavior-source: given-validation` (it re-opens the plan with the M0 gate). Note: this keeps the prior `data/`/`cache/` (it maps to `INTENT=new-mechanism`), so if strengthening M0 needs new/stronger data, tell the user to delete `data/` (and `cache/`) before running `/auto` — otherwise the kept stimuli are reused.

### Step 5 — Report

Print a concise summary:

```
[next-round] archived round <N> → rounds/round_<N>/
[next-round] intent: <new-behavior | new-mechanism <behavior-id>>
[next-round] drafted task.md for round <N+1> (recommended: /auto — behavior-source: <...>, mechanism: <...>)
Next: edit task.md, then run /auto.
```

## Key Rules

- **You read memory, never write it.** `research_memory.json` is owned by `/auto`. Do not edit it, do not move it.
- **The user decides.** When intent is ambiguous, recommend (first option) and confirm with `AskUserQuestion`; never silently pick.
- **Archive is non-destructive.** Move outputs into `rounds/round_<N>/`; keep a copy of the round's `task.md`; never overwrite an existing `rounds/round_<N>/`. If the target already has contents, this is a **hard failure (exit 3)**, not a silent skip: abort the entire skill and never go on to overwrite `task.md` while this round's outputs remain un-archived at root.
- **The drafted `task.md` is a starting point, not the source of truth.** Avoid-repeat is enforced by `/auto` reading memory; the draft just orients the human.

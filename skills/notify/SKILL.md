---
name: notify
description: "Draft a research-progress briefing and dispatch it through whatever notification service the user has already configured. Channel-agnostic — this skill only drafts the briefing text and scans for a configured service; it does not hard-code or recommend any particular channel or tool. Opt-in: it does nothing unless task.md asks for notifications (e.g. email reminders). Every briefing is saved to notification/ (never overwritten). Called by /auto on an hourly cadence and at progress / done / halted / approval-needed events, or manually via /notify."
argument-hint: "[event: hourly|progress|done|halted|approval-needed] [free-form reason ...]"
allowed-tools: Bash, Read, Write, Glob, Grep
---

# Notify — Draft + Dispatch a Progress Briefing

Draft a briefing for: **$ARGUMENTS** (event type + optional reason; defaults to `hourly` when omitted).

## Overview

This skill is the pipeline's notification utility. It does **two** things and nothing else:

1. **Drafts** a human-readable progress briefing (fixed content spec below) from the workspace artifacts.
2. **Dispatches** it through whatever notification service the user has already configured — it is **channel-agnostic**, so it never assumes, recommends, or hard-codes a specific channel or tool; it scans for whatever is configured (e.g. an email account, a webhook) and uses it.

**Opt-in + zero-impact guarantee.** This skill is a **silent no-op** unless `task.md` opts into notifications. When it is not opted in — or no notification service is configured — the pipeline behaves exactly as if this skill did not exist. It **never blocks** a workflow and **never fails loudly**: any dispatch error is logged and swallowed.

## Step 1 — Opt-in gate (task.md)

Read `task.md` at the project root. Proceed only if the user opted into notifications — any of:

- an explicit marker line: `notify:`, `notification:`, `email-notify:`, `notify: email` (value naming a channel or just `true`);
- natural-language intent to be notified, in any language — e.g. "email me when …", "notify me by email", or the equivalent in the task.md's own language.

If **no** opt-in signal is present → log `[notify] not opted in (no task.md notification directive) — skipping` and **return immediately**. Do not draft, do not write files.

> The task.md opt-in is the user's **standing authorization** for these auto-generated pipeline notifications — see Step 5's send note.

## Step 2 — Detect a configured notification service

Scan for whatever notification service the user has already set up, and use it. Do **not** assume, install, configure, or recommend any particular tool — detection is read-only, and configuration is the user's job. A briefing may go to more than one configured service.

- **Email** — if an authorized email account / sending tool is present in the environment (whatever the user set up), email is available. Determine the recipient and the send interface from that tool's own configuration.
- **Any other service the user configured** — a webhook URL, a chat integration, or a token file the project documents. Use each per its own contract.
- **Do not attempt to authenticate or log in here.** If a service is present but not authorized, treat it as not configured.

If **no** service is configured → still draft and **save** the briefing to `notification/` (Step 4), then log `[notify] briefing saved to notification/ — no dispatch channel configured` and return. The saved file is the durable record even when nothing is sent.

## Step 3 — Gather material (read-only)

Pull the current state from whatever exists (skip missing files silently):

- `CLAIMS_LEDGER.md` / `claims_ledger.json` — per-claim statement, main-experiment headline, verify verdict, `final_status`, `pipeline_status`, `open_items[]`.
- `refine-logs/EXPERIMENT_PLAN.md` — milestones, chosen mechanism, models + datasets.
- `refine-logs/EXPERIMENT_TRACKER.md` — per-run Status (`pending`/`running`/`done`/`failed`).
- `refine-logs/EXPERIMENT_RESULTS.md` — key metrics, `phenomenon_status`.
- `review-stage/REVIEW_STATE.json` — `iterations_consumed`, `last_score`, `last_verdict`, `status`.
- `experiment_queue/queue_state.json` (if present) — queued/running/stuck runs.
- `runs/` + `runs/iteration_round_*/` — recent run dirs and `cost.json` (GPU-hours).
- The caller's `reason` argument and event type.

## Step 4 — Write the briefing (a real update, not a form)

The briefing is an **email to a busy collaborator** — write it the way a sharp research assistant updates their PI, not by filling a template. Lead with what matters, interpret the numbers instead of dumping them, and make any action item impossible to miss. **Adapt length and shape to how much actually happened** since the last briefing: a quiet hour is three honest sentences; a milestone landing or a blocker is a full update. Never emit empty skeleton sections, and never pad — a short true update beats a long hollow one.

Follow the output-language rule (`skills/shared-references/output-language.md`): detect language from `task.md` and write the whole briefing in that language (keep code / paths / ids / metric names in English).

**Voice & shape**

- Open with a **one-line TL;DR** (this doubles as the email subject) and then a **2–4 sentence plain-language summary** of where the research stands right now and what changed since last time.
- Use **prose for state and interpretation**, **tables/bullets for numbers and lists** — mix freely, whatever reads fastest on a phone.
- **Always compute the delta since the last briefing.** Read the newest existing `notification/*.md` and say what moved: which runs finished, which verdicts flipped, GPU-hours burned since then. "3 of 8 runs finished since the last update — C1 is now a verified PASS" beats a static snapshot every time.
- **Interpret, don't just report.** Say whether a result is good / bad / expected, whether training looks healthy, whether a negative is a real finding or a suspected under-power artifact, whether momentum is normal or stalling.
- Close with **What's next**, and — when anything needs a human — a prominent **⚠ Needs you** line naming the single concrete action.

**Material to weave in** (include what is real for this run; drop what is empty — do not print "N/A" rows):

- **Headline** — one sentence a phone-glance absorbs.
- **Where things stand** — current stage, overall health, momentum vs the last briefing.
- **Progress** — per claim: the claim in plain words → main-experiment verdict → verify verdict, with *the* key number and what it means. Plus runs done / running / failed and GPU-hours (total, and since last briefing).
- **Plan & context** — current milestone(s) and success criterion, chosen mechanism / models / datasets — only as much as a fresh reader needs to follow along.
- **In flight** — what is running now, on which GPU(s), elapsed / rough ETA; queue depth and any stuck jobs.
- **What's next** — the next milestone or stage, and any upcoming decision point.
- **Needs you** — halts, Round-End Decisions, or anything requiring a human-only action (sudo, credentials, disk/quota, an external approval the pipeline cannot perform). State the one concrete thing to do; lead with it for `halted` / `approval-needed`.

**Worked example** (an `hourly` briefing mid-run — this is the *level of care and richness* to aim for, not a fixed layout to copy):

```
Subject: mechanist · hourly — C1 verified PASS, 2 runs left

Hi — quick hour-mark update on the first-person-belief study.

Where things stand. We're in the verify stage and it's going well. Since the last
briefing an hour ago, the C1 main effect held under both the dataset-swap and the
model-swap variants, so C1 is now a verified PASS (robustness 0.83). The two
remaining C2 ablation runs are still going; no crashes, GPU use within the 4-card cap.

Progress
- C1 — "the model rates first-person 'I believe X' as less true than the matched
  third-person assertion." Main experiment supported (Δ=0.21, p<0.01); verify PASS,
  2/2 eligible variants agree. This one looks solid.
- C2 — steering along the belief direction shifts refusal rate. Main experiment
  positive; the layer-sweep ablation is finishing now (below).
- Runs: 6/8 done, 2 running, 0 failed · ~11.3 GPU-h total (+2.1 since last update).

In flight
- C2_layer_sweep on GPUs 4,5 — ~35 min in, ETA ~20 min.

What's next. Once the two ablations land, verify closes and the pipeline moves into
the review/iteration loop. Nothing needed from you right now — I'll ping you when
verify finishes or if anything gets stuck.

Full per-claim detail any time in CLAIMS_LEDGER.md.
```

Two more shapes, to show the range:

- **Quiet hour** — don't manufacture content: *"Still on the C2 layer-sweep, ~40 min to go, everything nominal — nothing new since the last update. Next ping when it finishes."*
- **Needs-you (`approval-needed`)** — lead with the ask: *"⚠ Blocked: the run needs to install a system CUDA library and can't sudo on its own. Action: run `sudo apt-get install libaio-dev` on the box, then reply and I'll resume. Everything else is paused and safe."* Prefix the subject with **[ACTION NEEDED]**.

**Event → what to emphasize** (the writing adapts; these are the leads):

| event | typical trigger | lead with |
|---|---|---|
| `hourly` | ~1h cadence during a long run | where things stand + the delta since last time |
| `progress` | a milestone / run finished with a real result | the new result and what it means |
| `done` | pipeline reached a terminal state | the final verdict per claim + where deliverables live |
| `halted` | fail-loudly halt / Round-End Decision | what stopped, why, and the remedy |
| `approval-needed` | blocked on a human-only action | the ⚠ ask, first line; subject **[ACTION NEEDED]** |

## Step 5 — Save to `notification/` (durable, never overwritten)

Always write the drafted briefing to `notification/` at the project root, timestamped so it never collides and **never overwrites** a prior briefing:

```bash
mkdir -p notification
# filename: <UTC-timestamp>_<event>.md  (e.g. 20260709T014233Z_hourly.md)
```

`notification/` is the append-only archive of everything this skill produced. It is **kept at the project root across rounds** — `/next-round` never moves it into `rounds/round_<N>/` (see `skills/next-round/SKILL.md` keep-list).

## Step 6 — Dispatch through the configured channel

If a service was found in Step 2, send the briefing through that service's own send interface. The dispatch mechanics belong to whatever tool the user configured — this skill supplies the content and these conventions:

- **Subject / title = the briefing's one-line TL;DR** (Step 4), prefixed with the project tag — e.g. `mechanist · hourly — C1 verified PASS, 2 runs left`. A specific line the user can triage from the lock screen; never a generic "progress briefing".
- **Body = the saved briefing** (`notification/<file>.md`). Send it as-is; if the channel prefers formatted content, a light HTML rendering of the same text is fine — the content is identical either way.
- **Recipient / destination** comes from the configured service (the user's own address / channel) unless `task.md` names a different one.
- For `approval-needed` / `halted`, prefix the subject with `[ACTION NEEDED]`.
- **Standing-authorization for autonomous send (scoped to pipeline briefings only).** If the configured channel requires an interactive confirmation before sending, treat the `task.md` opt-in as the user's explicit standing authorization for these auto-generated notifications and self-confirm in the same flow rather than blocking for a reply. This applies **strictly** to briefings this skill drafted — never to user-directed messages.

On any send error (non-zero exit, auth expired, rate-limit): log it, keep the saved `notification/` file, and return without blocking. Never let a notification failure stop or delay the pipeline.

## Key Rules

- **Write it like a person, not a form.** Lead with the point, interpret the numbers, adapt length to what happened, and always report the delta since the last briefing. A terse skeleton with placeholder bullets is a failure of this skill even when every field is technically filled.
- **Opt-in only.** No `task.md` notification directive → pure no-op, zero side effects.
- **Never block, never fail loudly.** A dispatch failure is logged and swallowed; the pipeline proceeds unchanged.
- **Channel-agnostic.** This skill drafts text and hands it to a configured service; it does not own or hard-code a channel. If none is configured, it still saves to `notification/`.
- **`notification/` is append-only and root-persistent.** Timestamped filenames — never overwrite; never archived by `/next-round`.
- **No secrets in a briefing.** Never include API keys, tokens, passwords, or raw credentials.
- **Always surface a genuine blocker.** If the run needs a human-only action (sudo, credentials, quota, external approval), the Blocked section must name it and the one action required — this is the case a notification exists for.

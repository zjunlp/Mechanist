---
name: monitor-experiment
description: Monitor running experiments, check progress, collect results. Use when user says "check results", "is it done", "monitor", or wants experiment output.
argument-hint: [server-alias or screen-name]
allowed-tools: Bash(ssh *), Bash(echo *), Read, Write, Edit
---

# Monitor Experiment Results

Monitor: $ARGUMENTS

## Workflow

### Step 1: Check What's Running

> **Queue-batch context (when invoked as part of an `/experiment-queue` batch).** If the caller invokes this skill with a job-ID that belongs to an active `/experiment-queue` batch, the batch's `queue_state.json` (under `$REMOTE_RUN_DIR/queue_state.json` on the SSH host) is the authoritative source for that job's `status`, `started`, and `completed` timestamps — the queue scheduler has already verified `expected_output` exists. Phase 3.6 below still runs (it's how `cost.json` gets finalized), but Step 1 / 2 / 3 may use `queue_state.json` to skip the `screen -ls` + log-parsing path for jobs the scheduler has already marked terminal. For standalone use (no active queue), Step 1's `screen -ls` is the canonical check.

**SSH server:**
```bash
ssh <server> "screen -ls"
```

**Vast.ai instance** (read `ssh_host`, `ssh_port` from `vast-instances.json`):
```bash
ssh -p <PORT> root@<HOST> "screen -ls"
```

Also check vast.ai instance status:
```bash
vastai show instances
```

**Modal** (when `gpu: modal` in CLAUDE.md):
```bash
modal app list         # List running/recent apps
modal app logs <app>   # Stream logs from a running app
```
Modal apps auto-terminate when done — if it's not in the list, it already finished. Check results via `modal volume ls <volume>` or local output.

### Step 2: Collect Output from Each Screen
For each screen session, capture the last N lines:
```bash
ssh <server> "screen -S <name> -X hardcopy /tmp/screen_<name>.txt && tail -50 /tmp/screen_<name>.txt"
```

If hardcopy fails, check for log files or tee output.

### Step 3: Check for JSON Result Files
```bash
ssh <server> "ls -lt <results_dir>/*.json 2>/dev/null | head -20"
```

If JSON results exist, fetch and parse them:
```bash
ssh <server> "cat <results_dir>/<latest>.json"
```

### Step 3.5: Pull W&B Metrics (when `wandb: true` in CLAUDE.md)

**Skip this step entirely if `wandb` is not set or is `false` in CLAUDE.md.**

Pull training curves and metrics from Weights & Biases via Python API:

```bash
# List recent runs in the project
ssh <server> "python3 -c \"
import wandb
api = wandb.Api()
runs = api.runs('<entity>/<project>', per_page=10)
for r in runs:
    print(f'{r.id}  {r.state}  {r.name}  {r.summary.get(\"eval/loss\", \"N/A\")}')
\""

# Pull specific metrics from a run (last 50 steps)
ssh <server> "python3 -c \"
import wandb, json
api = wandb.Api()
run = api.run('<entity>/<project>/<run_id>')
history = list(run.scan_history(keys=['train/loss', 'eval/loss', 'eval/ppl', 'train/lr'], page_size=50))
print(json.dumps(history[-10:], indent=2))
\""

# Pull run summary (final metrics)
ssh <server> "python3 -c \"
import wandb, json
api = wandb.Api()
run = api.run('<entity>/<project>/<run_id>')
print(json.dumps(dict(run.summary), indent=2, default=str))
\""
```

**What to extract:**
- **Training loss curve** — is it converging? diverging? plateauing?
- **Eval metrics** — loss, PPL, accuracy at latest checkpoint
- **Learning rate** — is the schedule behaving as expected?
- **GPU memory** — any OOM risk?
- **Run status** — running / finished / crashed?

**W&B dashboard link** (include in summary for user):
```
https://wandb.ai/<entity>/<project>/runs/<run_id>
```

> This gives the auto-review-loop richer signal than just screen output — training dynamics, loss curves, and metric trends over time.

### Step 3.6: Finalize cost manifest (mandatory whenever a run completes)

For every run detected as completed (or failed) in Step 1, finalize its `runs/<run-id>/cost.json` (`/run-experiment` Step 5.5 wrote the initial stub with `status: running`):

1. Compute or fetch:
   - `ended_at` — UTC ISO 8601 timestamp at which the run terminated (from screen log timestamps, modal API, or the result JSON's writeback time).
   - `wall_clock_seconds` — `ended_at - started_at` in seconds (from the cost.json's `started_at` field). Round to 1 decimal.
   - `gpu_seconds` — for `gpu_provider` in `{remote, local, vast}`: `wall_clock_seconds * len(gpu_ids)`. For `modal`: read from the Modal API's billing record (authoritative) — fall back to `wall_clock_seconds * <tier_count>` only if the API call fails.
   - `gpu_hours` — `gpu_seconds / 3600`, rounded to 2 decimals.
   - `status` — `completed` on clean exit, `failed` if the screen log shows a non-zero exit or the result file is missing.
2. Rewrite `runs/<run-id>/cost.json` with all fields populated (keep the `started_at` / `gpu_ids` / `gpu_provider` from the initial stub — do not invent new values).
3. Log `[cost] run=<run-id> wall=<H>h gpu=<H>h status=<status>`.

This file is the **canonical** record consumed by `/auto-experiment` Phase 5, `/auto-iteration-loop` Phase C bookkeeping (incrementing `runs_total` / `gpu_hours_total`), and `/auto-verify` budget tracking. Do not let downstream consumers parse free-form deploy logs — they read this file.

If `cost.json` is missing entirely (legacy run launched before this contract was active), write a best-effort version: derive `gpu_hours` from screen log start/end timestamps and label the file with `"legacy": true` so consumers can choose to trust it loosely.

### Step 4: Summarize Results

Present results in a comparison table:
```
| Experiment | Metric | Delta vs Baseline | Status |
|-----------|--------|-------------------|--------|
| Baseline  | X.XX   | —                 | done   |
| Method A  | X.XX   | +Y.Y              | done   |
```

### Step 5: Interpret
- Compare against known baselines
- Flag unexpected results (negative delta, NaN, divergence)
- Suggest next steps based on findings

## Key Rules
- Always show raw numbers before interpretation
- Compare against the correct baseline (same config)
- Note if experiments are still running (check progress bars, iteration counts)
- If results look wrong, check training logs for errors before concluding
- **Vast.ai cost awareness**: When monitoring vast.ai instances, report the running cost (hours * $/hr from `vast-instances.json`). If all experiments on an instance are done, remind the user to run `/vast-gpu destroy <instance_id>` to stop billing
- **Modal cost awareness**: Modal auto-scales to zero — no idle billing. When reporting results from Modal runs, note the actual execution time and estimated cost (time * $/hr from the GPU tier used). No cleanup action needed

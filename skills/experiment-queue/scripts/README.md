# experiment-queue Scripts

Scheduler and manifest builder for `/experiment-queue` skill.

## Files

- `build_manifest.py` — Expands grid spec (YAML/JSON) into explicit job manifest
- `queue_manager.py` — Scheduler that runs on the remote host; polls, launches, retries, cleans

## Install on Remote

The `/experiment-queue` skill auto-installs these on the SSH host under `~/.mechanist_queue/` per invocation (idempotent). The skill resolves the local helpers from its own `${CLAUDE_SKILL_DIR}/scripts/` directory first, then falls back to legacy locations for older project layouts.

For manual install (run from anywhere; `$MECHANIST_REPO` points at the cloned MECHANICA repo root):

```bash
ssh <server> 'mkdir -p ~/.mechanist_queue'
scp "$MECHANIST_REPO/skills/experiment-queue/scripts/queue_manager.py" \
    "$MECHANIST_REPO/skills/experiment-queue/scripts/build_manifest.py" \
    <server>:~/.mechanist_queue/
```

## Example

### 1. Write grid spec (on local or remote)

`grid_spec.yaml`:
```yaml
project: my_grid_experiment
cwd: /home/user/your_project
conda: my_env
gpus: [0, 1, 2, 3, 4, 5, 6, 7]
max_parallel: 8
oom_retry: {delay: 120, max_attempts: 3}

phases:
  - name: distill
    grid:
      N: [64, 128, 256]
      seed: [42, 200, 201]
      n_train_subset: [50000, 150000, 500000, 652000]
    template:
      id: "s${seed}_N${N}_n${n_train_subset}"
      cmd: >
        python run_distill.py --backbone softmax --lam 0.5
        --t_max_distill 0 --K 500 --L 96 --W 16 --n_steps 30000
        --batch_size 128 --lr 1e-4 --seed ${seed} --subset_seed 2024
        --n_hidden ${N} --n_train_subset ${n_train_subset}
      expected_output: "figures/distill_sw_N${N}_*_seed${seed}.json"
```

### 2. Build manifest

```bash
python3 build_manifest.py --config grid_spec.yaml --output manifest.json
```

### 3. Launch scheduler

Use a per-run directory under `~/.mechanist_queue/runs/` so concurrent queues don't collide and crash-resume is reproducible. Note that `scp` runs in SFTP mode in modern OpenSSH and does NOT reliably expand `$HOME` in destination paths — use remote-relative paths for `scp` destinations and `$HOME`-prefixed paths only inside `ssh` command strings (where remote bash expands them):

```bash
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)
REMOTE_RUN_REL=".mechanist_queue/runs/$RUN_TS"     # for scp (relative to remote home)
REMOTE_RUN_DIR="\$HOME/$REMOTE_RUN_REL"            # for ssh commands (expanded remotely)

ssh <server> "mkdir -p \"$REMOTE_RUN_DIR/logs\" \"\$HOME/.mechanist_queue\""
scp manifest.json <server>:"$REMOTE_RUN_REL/manifest.json"

ssh <server> "nohup python3 \"\$HOME/.mechanist_queue/queue_manager.py\" \\
    --manifest \"$REMOTE_RUN_DIR/manifest.json\" \\
    --state    \"$REMOTE_RUN_DIR/queue_state.json\" \\
    --log-dir  \"$REMOTE_RUN_DIR/logs\" \\
    > \"$REMOTE_RUN_DIR/queue_mgr.log\" 2>&1 &"
```

> Note: `--log-dir` is the per-job log directory the scheduler reads for OOM detection. The flag `--log` is declared by argparse but unused; do not pass it.

### 4. Monitor

```bash
ssh <server> "jq '.jobs | group_by(.status) | map({(.[0].status): length}) | add' \"$REMOTE_RUN_DIR/queue_state.json\""
```

Returns:
```json
{"completed": 30, "running": 6, "pending": 0}
```

## State Machine

```
pending → running → completed
                  ↘ failed_oom → pending (after delay, up to max_attempts)
                               ↘ stuck (after max_attempts)
                  ↘ failed_other → stuck
```

## Conda hook override

If conda is installed at a non-standard path on the remote, set one of:

1. `conda_hook:` field in the manifest YAML — full hook command string (e.g. `eval "$(/custom/path/conda shell.bash hook)"`) or a bare conda binary path (auto-wrapped).
2. `MECHANIST_CONDA_HOOK` env var on the remote — same format as the manifest field.

If neither is set, the scheduler auto-detects from common install locations (anaconda3, miniconda3, miniforge3 under `~/`, `/opt/`, `/usr/local/`, `/opt/homebrew/`) and finally falls back to `command -v conda`.

## Dependencies

- Python 3.8+
- `nvidia-smi` on remote
- `screen` on remote
- Optional: `pyyaml` (only if using YAML grid specs)

## Invariants

- **No GPU overlap**: scheduler only assigns GPU with `memory.used < 500 MiB`
- **State is source of truth**: `queue_state.json` is written atomically every step
- **Idempotent**: safe to kill and restart the scheduler; picks up from state
- **Output-based completion**: completion is verified by `expected_output` existing, not just by screen/process exit

## Not Yet Supported

- Mid-run GPU reshuffling (if GPU becomes unavailable mid-job)
- Automatic GPU-per-job count (all jobs assumed single-GPU)
- Distributed multi-node queues
- Auto-sync results back to local
- Per-job `cost.json` finalization — `/monitor-experiment` Step 3.6 still writes the per-run cost manifest; `queue_state.json` carries the batch-level state in parallel

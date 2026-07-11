# Output Manifest Protocol

After writing any output file, append an entry to `MANIFEST.md` in the project root.

## Format

If `MANIFEST.md` does not exist, create it with this header:

```markdown
# Research Output Manifest

> Auto-maintained by MECHANIST skills. Tracks all generated artifacts across the research lifecycle.

| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
```

**The table has exactly these 5 columns — `Timestamp | Skill | File | Stage | Description`, in this order. Do not drop, rename, merge, or add columns** (e.g., do not collapse to a 4-column `Date | Skill | Output | Description` form), and use the literal header `# Research Output Manifest`. If an existing `MANIFEST.md` is found in a different shape, migrate it to these 5 columns before appending.

Then append one row per output file written:

```
| 2025-06-15 14:30 | /idea-creator | idea-stage/IDEA_REPORT_20250615_143022.md | claim | 12 ideas generated from "LLM reasoning" direction |
| 2025-06-15 14:30 | /idea-creator | idea-stage/IDEA_REPORT.md | claim | latest copy |
```

## Stage Values

Aligned with `/auto`'s pipeline (`claim → experiment → verify → iteration`).

| Stage | Skills |
|-------|--------|
| `claim`      | /research-lit, /idea-creator, /auto-claim, /novelty-check, /research-review, /research-refine, /research-refine-pipeline, /experiment-plan |
| `experiment` | /auto-experiment, /run-experiment, /mechanism-skills |
| `verify`     | /auto-verify, /verify-pick-alternatives, /result-to-claim |
| `iteration`  | /auto-iteration-loop |

## Pre-flight Check

Before writing output, if the skill depends on a prerequisite file from a previous stage:
1. Check if the prerequisite file exists at its expected stage-scoped path (e.g., `idea-stage/IDEA_REPORT.md`, `review-stage/AUTO_REVIEW.md`)
2. If not found at the stage-scoped path, check the legacy root-level path (e.g., `./IDEA_REPORT.md`, `./AUTO_REVIEW.md`) — see [Path Fallback Rule](output-versioning.md#path-fallback-rule-backward-compatibility)
3. If not found at either path, warn: "⚠️ Expected {file} (from {skill}) but not found. Run {skill} first?"
4. Do not block — the user may have the file elsewhere or want to proceed anyway

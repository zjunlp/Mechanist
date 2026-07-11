---
name: paper-figure
description: "Generate publication-quality figures and tables from experiment results. Use when user says \"画图\", \"作图\", \"generate figures\", \"paper figures\", or needs plots for a paper. Also invoked by `/auto`'s Ledger Figures hook to produce per-claim figures embedded into `CLAIMS_LEDGER.md`."
argument-hint: [figure-plan-or-data-path | mode:auto-ledger ...]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__llm-chat__chat
---

# Paper Figure: Publication-Quality Plots from Experiment Data

Generate all figures and tables for a paper based on: **$ARGUMENTS**

This skill has two calling modes, sharing the same plotting machinery:

- **Standalone paper mode** (default): driven by `PAPER_PLAN.md` from `/paper-plan`. Produces vector PDFs in `figures/` plus `latex_includes.tex` for paper-write.
- **Auto-ledger mode** (`mode: auto-ledger`): driven by an inline plan supplied by `/auto`'s Ledger Figures hook. Image figures produce PDF (vector, for later paper use) **and** PNG (raster, for Markdown embed); table figures produce `.md` (inline-renderable for the ledger) **and** `.tex` (publication-grade) — all under `figures/<claim_id>/`, plus a machine-readable `INDEX.json` per claim. Tables are first-class artifacts in this mode, on equal footing with charts. See "Auto-ledger invocation contract" below.

## Scope: What This Skill Can and Cannot Do

| Category | Can auto-generate? | Examples |
|----------|-------------------|----------|
| **Data-driven plots** | ✅ Yes | Line plots (training curves), bar charts (method comparison), scatter plots, heatmaps, box/violin plots |
| **Comparison tables** | ✅ Yes | LaTeX tables comparing prior bounds, method features, ablation results |
| **Multi-panel figures** | ✅ Yes | Subfigure grids combining multiple plots (e.g., 3×3 dataset × method) |
| **Architecture/pipeline diagrams** | ❌ No — manual | Model architecture, data flow diagrams, system overviews. At best can generate a rough TikZ skeleton, but **expect to draw these yourself** using tools like draw.io, Figma, or TikZ |
| **Generated image grids** | ❌ No — manual | Grids of generated samples (e.g., GAN/diffusion outputs). These come from running your model, not from this skill |
| **Photographs / screenshots** | ❌ No — manual | Real-world images, UI screenshots, qualitative examples |

**In practice:** For a typical ML paper, this skill handles ~60% of figures (all data plots + tables). The remaining ~40% (hero figure, architecture diagram, qualitative results) need to be created manually and placed in `figures/` before running `/paper-write`. The skill will detect these as "existing figures" and preserve them.

## Constants

- **STYLE = `publication`** — Visual style preset. Options: `publication` (default, clean for print), `poster` (larger fonts), `slide` (bold colors)
- **DPI = 300** — Output resolution
- **FORMAT = `pdf`** — Output format in standalone mode. Options: `pdf` (vector, best for LaTeX), `png` (raster fallback). **In auto-ledger mode the formats are chosen per figure by `type`:** image types (line / bar / ...) write `pdf` + `png`; the `table` type writes `md` + `tex`. The caller passes the union (`formats: pdf,png,md,tex`) — each figure-script then picks the subset that matches its type.
- **COLOR_PALETTE = `tab10`** — Default matplotlib color cycle. Options: `tab10`, `Set2`, `colorblind` (deuteranopia-safe)
- **FONT_SIZE = 10** — Base font size (matches typical conference body text)
- **FIG_DIR = `figures/`** — Default output directory in standalone mode. **In auto-ledger mode this is overridden by the caller-supplied `output_dir` (typically `figures/<claim_id>/`).**
- **REVIEWER_MODEL = `gpt-5.4`** — Model used via Codex MCP for figure quality review. Skipped when `review: false` is passed (default in auto-ledger mode to keep ledger renders cheap).

## Inputs

1. **PAPER_PLAN.md** — figure plan table (from `/paper-plan`). Used in standalone mode.
2. **`plan_inline`** — an inline figure plan passed via `$ARGUMENTS` (auto-ledger mode). Replaces PAPER_PLAN.md when present; same schema as the PAPER_PLAN.md figure table.
3. **Experiment data** — JSON files, CSV files, or screen logs in `figures/`, `runs/<run-id>/`, `verify/`, or project root.
4. **Existing figures** — any manually created figures to preserve.

Resolution order at Step 1: `plan_inline` > `PAPER_PLAN.md` > scan-and-ask. The third branch is **unreachable in auto-ledger mode** — if neither inline plan nor PAPER_PLAN.md is present, return `status: no-plan` instead of prompting (the caller decides what to do).

## Auto-ledger invocation contract

When `/auto`'s Ledger Figures hook calls this skill, the orchestrator passes a YAML-shaped payload in `$ARGUMENTS`:

```yaml
mode: auto-ledger
project_root: <abs path>          # cwd for all relative paths
claims:                            # one or more claims, batched in a single call
  - claim_id: C1
    claim_title: "<short statement>"
    output_dir: figures/C1/
    plan_inline:
      - id: c1_robustness          # filename stem; image types produce <id>.pdf + <id>.png
        type: bar                  # one of {line, bar, grouped_bar, scatter, heatmap, box, violin, multi_panel, table}
        data: verify/C1_<short>/ROBUSTNESS.md
        caption: "Robustness of C1 across method/dataset/model swaps."
        x: variant
        y: metric_value
        group: axis                # optional; for grouped_bar
      - id: c1_training_curves
        type: line
        data: runs/<run-id>/metrics.json
        caption: "Training dynamics for C1's main-experiment run."
        x: step
        y: [train_loss, val_loss]
      - id: c1_k_sensitivity       # table types produce <id>.md + <id>.tex (no pdf/png)
        type: table
        data: runs/<run-id>/k_sweep.json
        caption: "K-sensitivity of top-K ablation accuracy."
        columns: [K, overall_acc, joy, sadness, anger, fear, surprise, disgust]
formats: pdf,png,md,tex            # union; each figure picks the subset matching its type
review: false                      # skip Step 7 GPT-5.4 review
style: publication
```

**Per-claim outputs (auto-ledger mode):**

```
figures/<claim_id>/
├── paper_plot_style.py            # shared style config (one copy per claim dir is fine; small file)
├── gen_<id>.py                    # per-figure generator script (image OR table)
├── <id>.pdf                       # image figures: vector for paper-write
├── <id>.png                       # image figures: raster for Markdown embed
├── <id>.md                        # table figures: inline-renderable for the ledger
├── <id>.tex                       # table figures: publication-grade LaTeX
└── INDEX.json                     # machine-readable summary (see schema below)
```

Image types write `.pdf` + `.png` and skip `.md` / `.tex`; the `table` type writes `.md` + `.tex` and skips `.pdf` / `.png`. The per-figure generator script chooses the format pair based on `type`.

**`INDEX.json` schema:**

```json
{
  "claim_id": "C1",
  "claim_title": "<short>",
  "generated_at": "<iso-8601>",
  "figures": [
    {
      "id": "c1_robustness",
      "type": "bar",
      "caption": "Robustness of C1 across method/dataset/model swaps.",
      "png": "figures/C1/c1_robustness.png",
      "pdf": "figures/C1/c1_robustness.pdf",
      "md":  null,
      "tex": null,
      "source_data": "verify/C1_<short>/ROBUSTNESS.md",
      "status": "ok"
    },
    {
      "id": "c1_k_sensitivity",
      "type": "table",
      "caption": "K-sensitivity of top-K ablation accuracy.",
      "png": null,
      "pdf": null,
      "md":  "figures/C1/c1_k_sensitivity.md",
      "tex": "figures/C1/c1_k_sensitivity.tex",
      "source_data": "runs/<run-id>/k_sweep.json",
      "status": "ok"
    }
  ],
  "skipped": [
    {"id": "c1_grid", "reason": "source_data missing: runs/<run-id>/grid.json"}
  ]
}
```

Every figure entry carries all four artifact slots — `png`, `pdf`, `md`, `tex` — with the unused pair set to `null`. `status` is `ok` on successful render or `error` with an `error_detail` field if the figure-generator script raised. Skipped entries (data file missing, plan entry of unsupported type, etc.) live in the `skipped` array — the script never raises for skip cases. `INDEX.json` is the **only** contract the caller relies on; the orchestrator parses it to populate `claims_ledger.json[claim].figures[]`.

**Return value (auto-ledger mode):** a one-line summary per claim — `"C1: 2/3 figures generated, 1 skipped (data missing)"` — plus the absolute path of each `INDEX.json` written. No LaTeX include snippets are produced in this mode.

## Workflow

### Step 1: Read Figure Plan

Resolve the plan source in this order:

1. **Auto-ledger mode** (`mode: auto-ledger` in `$ARGUMENTS`): use the inline `plan_inline` from each claim entry. PAPER_PLAN.md is ignored even if it exists.
2. **Standalone mode, PAPER_PLAN.md present**: parse the Figure Plan table:

   ```markdown
   | ID | Type | Description | Data Source | Priority |
   |----|------|-------------|-------------|----------|
   | Fig 1 | Architecture | ... | manual | HIGH |
   | Fig 2 | Line plot | ... | figures/exp.json | HIGH |
   ```

3. **Standalone mode, no PAPER_PLAN.md**: scan for data files in `figures/`, `runs/`, project root, and ask the user which figures to generate.
4. **Auto-ledger mode with neither**: return `status: no-plan` (do not prompt — the orchestrator is non-interactive).

For each entry, classify:

- Auto-generatable from data
- Needs manual creation (architecture diagrams, etc.) — flagged `[MANUAL]`, skipped here
- Comparison table — generated as LaTeX in standalone mode; as both Markdown (`.md`, for inline ledger embed) and LaTeX (`.tex`, for paper-write) in auto-ledger mode. Treated the same as any other figure type in both modes — no opt-in required.

### Step 2: Set Up Plotting Environment

Create a shared style configuration script in the active output dir (project root `figures/` for standalone, `figures/<claim_id>/` for auto-ledger):

```python
# paper_plot_style.py — shared across all figure scripts in this dir
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({
    'font.size': FONT_SIZE,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'axes.labelsize': FONT_SIZE,
    'axes.titlesize': FONT_SIZE + 1,
    'xtick.labelsize': FONT_SIZE - 1,
    'ytick.labelsize': FONT_SIZE - 1,
    'legend.fontsize': FONT_SIZE - 1,
    'figure.dpi': DPI,
    'savefig.dpi': DPI,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'text.usetex': False,  # set True if LaTeX is available
    'mathtext.fontset': 'stix',
})

# Color palette
COLORS = plt.cm.tab10.colors  # or Set2, or colorblind-safe

def save_fig(fig, name, formats=('pdf',), out_dir=FIG_DIR):
    """Save figure under out_dir for every format in `formats`."""
    paths = []
    for fmt in formats:
        path = f'{out_dir}/{name}.{fmt}'
        fig.savefig(path)
        paths.append(path)
        print(f'Saved: {path}')
    return paths
```

In auto-ledger mode `formats=('pdf', 'png')` so each call writes both files; the PNG is what the ledger Markdown will reference.

### Step 3: Auto-Select Figure Type

Use this decision tree for data-driven figures (inspired by Imbad0202/academic-research-skills):

| Data Pattern | Recommended Type | Size |
|-------------|-----------------|------|
| X=time/steps, Y=metric | Line plot | 0.48\textwidth |
| Methods × 1 metric | Bar chart | 0.48\textwidth |
| Methods × multiple metrics | Grouped bar / radar | 0.95\textwidth |
| Two continuous variables | Scatter plot | 0.48\textwidth |
| Matrix / grid values | Heatmap | 0.48\textwidth |
| Distribution comparison | Box/violin plot | 0.48\textwidth |
| Multi-dataset results | Multi-panel (subfigure) | 0.95\textwidth |
| Prior work comparison | LaTeX table | — |

When the plan entry's `type` is already set (always the case in auto-ledger mode), use it directly without re-classifying.

### Step 4: Generate Each Figure

For each figure in the plan, create a standalone Python script:

**Line plots** (training curves, scaling):
```python
# gen_fig2_training_curves.py
from paper_plot_style import *
import json

with open('figures/exp_results.json') as f:
    data = json.load(f)

fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
ax.plot(data['steps'], data['fac_loss'], label='Factorized', color=COLORS[0])
ax.plot(data['steps'], data['crf_loss'], label='CRF-LR', color=COLORS[1])
ax.set_xlabel('Training Steps')
ax.set_ylabel('Cross-Entropy Loss')
ax.legend(frameon=False)
save_fig(fig, 'fig2_training_curves', formats=FORMATS, out_dir=OUT_DIR)
```

**Bar charts** (comparison, ablation):
```python
fig, ax = plt.subplots(1, 1, figsize=(5, 3))
methods = ['Baseline', 'Method A', 'Method B', 'Ours']
values = [82.3, 85.1, 86.7, 89.2]
bars = ax.bar(methods, values, color=[COLORS[i] for i in range(len(methods))])
ax.set_ylabel('Accuracy (%)')
# Add value labels on bars
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val:.1f}', ha='center', va='bottom', fontsize=FONT_SIZE-1)
save_fig(fig, 'fig3_comparison', formats=FORMATS, out_dir=OUT_DIR)
```

**Comparison tables** (standalone — LaTeX only):
```latex
\begin{table}[t]
\centering
\caption{Comparison of estimation error bounds. $n$: sample size, $D$: ambient dim, $d$: latent dim, $K$: subspaces, $n_k$: modes.}
\label{tab:bounds}
\begin{tabular}{lccc}
\toprule
Method & Rate & Depends on $D$? & Multi-modal? \\
\midrule
\citet{MinimaxOkoAS23} & $n^{-s'/D}$ & Yes (curse) & No \\
\citet{ScoreMatchingdistributionrecovery} & $n^{-2/d}$ & No & No \\
\textbf{Ours} & $\sqrt{\sum n_k d_k / n}$ & No & Yes \\
\bottomrule
\end{tabular}
\end{table}
```

**Comparison tables** (auto-ledger — both `.md` and `.tex`):

```python
# gen_c1_k_sensitivity.py
import json, os
from textwrap import dedent

with open('runs/<run-id>/k_sweep.json') as f:
    rows = json.load(f)['sweep']  # {K: {overall_acc, per_emotion: {...}}}

cols = ['K', 'overall', 'joy', 'sad', 'ang', 'fear', 'surp', 'dis']

# Markdown
md_rows = [
    f"| {k} | {v['overall_accuracy']*100:.1f}% | " + " | ".join(
        f"{v['per_emotion'][e]['acc']*100:.1f}%" for e in
        ['joy','sadness','anger','fear','surprise','disgust']) + " |"
    for k, v in rows.items()
]
md = "| " + " | ".join(cols) + " |\n" + "|" + "|".join(["---"]*len(cols)) + "|\n" + "\n".join(md_rows) + "\n"
with open(f'{OUT_DIR}/c1_k_sensitivity.md', 'w') as f: f.write(md)

# LaTeX (mirror)
tex = dedent(r"""
\begin{table}[t]
\centering
\caption{K-sensitivity of top-K ablation accuracy.}
\label{tab:c1_k_sensitivity}
\begin{tabular}{l""" + "c"*(len(cols)-1) + r"""}
\toprule
""" + " & ".join(cols) + r""" \\
\midrule
""") + "\n".join(
    f"{k} & {v['overall_accuracy']*100:.1f}\\% & " + " & ".join(
        f"{v['per_emotion'][e]['acc']*100:.1f}\\%" for e in
        ['joy','sadness','anger','fear','surprise','disgust']) + r" \\"
    for k, v in rows.items()
) + "\n" + r"""\bottomrule
\end{tabular}
\end{table}
"""
with open(f'{OUT_DIR}/c1_k_sensitivity.tex', 'w') as f: f.write(tex)
```

The `.md` and `.tex` carry the same numbers in their native formats — the orchestrator embeds the `.md` inline into `CLAIMS_LEDGER.md`, and paper-write later picks up the `.tex` verbatim. Keep cell formatting consistent across both (same significant figures, same percent signs) so the two render identically.

**Architecture/pipeline diagrams** (MANUAL — outside this skill's scope):
- These require manual creation using draw.io, Figma, Keynote, or TikZ
- This skill can generate a rough TikZ skeleton as a starting point, but **do not expect publication-quality results**
- If the figure already exists in `figures/`, preserve it and generate only the LaTeX `\includegraphics` snippet
- Flag as `[MANUAL]` in the figure plan and `latex_includes.tex`

**Auto-ledger mode error containment.** Wrap each per-figure script invocation in a try-block: a script that raises must NOT abort the batch. Record the failure in `INDEX.json.figures[].status = "error"` with `error_detail`, and continue to the next figure. A missing data file is a `skipped` entry (not an error). This keeps the Ledger Figures hook fail-soft, as required by `/auto`.

### Step 5: Run All Scripts

```bash
# Run all figure generation scripts
for script in gen_fig*.py; do
    python "$script"
done
```

Verify all output files exist and are non-empty. In auto-ledger mode, after all scripts finish, write `INDEX.json` summarizing every plan entry's terminal state (`ok` / `error` / `skipped`).

### Step 6: Generate LaTeX Include Snippets

**Standalone mode only.** For each figure, output the LaTeX code to include it:

```latex
% === Fig 2: Training Curves ===
\begin{figure}[t]
    \centering
    \includegraphics[width=0.48\textwidth]{figures/fig2_training_curves.pdf}
    \caption{Training curves comparing factorized and CRF-LR denoising.}
    \label{fig:training_curves}
\end{figure}
```

Save all snippets to `figures/latex_includes.tex` for easy copy-paste into the paper.

Skipped in auto-ledger mode — the ledger Markdown embed is the only consumer, and the orchestrator constructs the image-link Markdown itself from `INDEX.json`.

### Step 7: Figure Quality Review with REVIEWER_MODEL

**Skipped when `review: false`** (auto-ledger mode default). Otherwise, send figure descriptions and captions to GPT-5.4 for review:

```
mcp__llm-chat__chat:
  model: gpt-5.4
  prompt: |
    Review these figure/table plans for a [VENUE] submission.

    For each figure:
    1. Is the caption informative and self-contained?
    2. Does the figure type match the data being shown?
    3. Is the comparison fair and clear?
    4. Any missing baselines or ablations?
    5. Would a different visualization be more effective?

    [list all figures with captions and descriptions]
```

### Step 8: Quality Checklist

Before finishing, verify each figure (from pedrohcgs/claude-code-my-workflow):

- [ ] Font size readable at printed paper size (not too small)
- [ ] Colors distinguishable in grayscale (print-friendly)
- [ ] **No title inside figures** — titles go only in LaTeX `\caption{}` (from pedrohcgs)
- [ ] Legend does not overlap data
- [ ] Axis labels have units where applicable
- [ ] Axis labels are publication-quality (not variable names like `emp_rate`)
- [ ] Figure width fits single column (0.48\textwidth) or full width (0.95\textwidth)
- [ ] PDF output is vector (not rasterized text)
- [ ] No matplotlib default title (remove `plt.title` for publications)
- [ ] Serif font matches paper body text (Times / Computer Modern)
- [ ] Colorblind-accessible (if using colorblind palette)

## Output

**Standalone mode:**

```
figures/
├── paper_plot_style.py          # shared style config
├── gen_fig1_architecture.py     # per-figure scripts
├── gen_fig2_training_curves.py
├── gen_fig3_comparison.py
├── fig1_architecture.pdf        # generated figures
├── fig2_training_curves.pdf
├── fig3_comparison.pdf
├── latex_includes.tex           # LaTeX snippets for all figures
└── TABLE_*.tex                  # standalone table LaTeX files
```

**Auto-ledger mode** (one tree per claim under the project root):

```
figures/
├── C1/
│   ├── paper_plot_style.py
│   ├── gen_c1_robustness.py
│   ├── gen_c1_training_curves.py
│   ├── c1_robustness.pdf
│   ├── c1_robustness.png
│   ├── c1_training_curves.pdf
│   ├── c1_training_curves.png
│   └── INDEX.json
├── C2/
│   └── ...
└── INDEX.md                     # (written by the /auto orchestrator, not this skill)
```

`figures/INDEX.md` is the orchestrator's global index — this skill only writes the per-claim subtrees and their `INDEX.json` files.

## Key Rules

- **Every figure must be reproducible** — save the generation script alongside the output
- **Do NOT hardcode data** — always read from JSON/CSV files
- **Use vector format (PDF)** for all plots — PNG only as fallback (or as the Markdown-embed companion in auto-ledger mode)
- **No decorative elements** — no background colors, no 3D effects, no chart junk
- **Consistent style across all figures** — same fonts, colors, line widths
- **Colorblind-safe** — verify with https://davidmathlogic.com/colorblind/ if needed
- **One script per figure** — easy to re-run individual figures when data changes
- **No titles inside figures** — captions are in LaTeX (standalone) or Markdown `![caption](path)` alt-text (auto-ledger) only
- **Comparison tables count as figures** — first-class artifacts in every mode. Standalone mode writes a `.tex` file; auto-ledger mode writes both a `.md` (for inline ledger embed) and a `.tex` (for paper-write), exactly parallel to how image types write both `.png` and `.pdf`.
- **Auto-ledger mode is fail-soft** — a script error degrades to a single `INDEX.json` entry with `status: error`; never raise out of the batch

## Figure Type Reference

| Type | When to Use | Typical Size |
|------|------------|--------------|
| Line plot | Training curves, scaling trends | 0.48\textwidth |
| Bar chart | Method comparison, ablation | 0.48\textwidth |
| Grouped bar | Multi-metric comparison | 0.95\textwidth |
| Scatter plot | Correlation analysis | 0.48\textwidth |
| Heatmap | Attention, confusion matrix | 0.48\textwidth |
| Box/violin | Distribution comparison | 0.48\textwidth |
| Architecture | System overview | 0.95\textwidth |
| Multi-panel | Combined results (subfigures) | 0.95\textwidth |
| Comparison table | Prior bounds vs. ours (theory) | full width |

## Acknowledgements

Design pattern (type × style matrix) inspired by [baoyu-skills](https://github.com/jimliu/baoyu-skills). Publication style defaults and figure rules from [pedrohcgs/claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow). Visualization decision tree from [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills).

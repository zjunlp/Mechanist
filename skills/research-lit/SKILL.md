---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent, AskUserQuestion, mcp__zotero__*, mcp__obsidian-vault__*, mcp__mechanic-db__search_papers, mcp__llm-chat__chat
---

# Research Literature Review

Research topic: $ARGUMENTS

## Constants


- **REVIEWER_BACKEND = `llm-chat`** — Default: llm-chat MCP (defer to `LLM_MODEL` env). Override with `— reviewer: oracle-pro` for GPT-5.4 Pro via Oracle MCP.
- **PAPER_LIBRARY** — Local PDF collection, organized as **two channels** that are both globbed at retrieval time (Step 0c):
  1. **`literature/`** — *user-curated channel*. PDFs the user manually places here (reading list, must-cite references, annotated copies). **Read-only** to the pipeline — never auto-written or deleted, so anything dropped here is safe and always considered.
  2. **`papers/`** — *machine-managed channel*. The pipeline auto-downloads arXiv PDFs here (only when `ARXIV_DOWNLOAD = true`, or when `REF_PAPER` is an arXiv URL — see Phase 0.5 of `/auto-claim`). Regenerable scratch — safe to delete and re-fetch.
  3. Optionally, a custom path the user sets in `CLAUDE.md` under `## Paper Library`.

  **Precedence**: when the same paper appears in both channels (matched by normalized title), the `literature/` copy wins.
- **MAX_LOCAL_PAPERS = 20** — Maximum number of local PDFs to scan (read first 3 pages each). If more are found, prioritize by filename relevance to the topic.
- **ARXIV_DOWNLOAD = false** — When `true`, download top 3-5 most relevant arXiv PDFs to PAPER_LIBRARY after search. When `false` (default), only fetch metadata (title, abstract, authors) via arXiv API — no files are downloaded.
- **ARXIV_MAX_DOWNLOAD = 5** — Maximum number of PDFs to download when `ARXIV_DOWNLOAD = true`.
- **OUTPUT_DIR = `idea-stage/`** — Where to write the two files in Step 5. Defaults to `idea-stage/` (created if missing) regardless of caller; override with `— output-dir: <path>`. Step 5 writes **two files unconditionally** at the end of every run:
  1. `<OUTPUT_DIR>/RESEARCH_LIT.md` — raw retrieval dump (per-paper abstracts/intros + provenance). **Pure audit artifact** — never read back by any downstream skill, only for human inspection of what was retrieved before synthesis. Not a resume gate.
  2. `<OUTPUT_DIR>/LANDSCAPE.md` — synthesized landscape (structured paper table + 3-5 paragraph narrative + structural gaps). **Read by `/idea-creator` Phase 1 from disk**, then pasted into its Phase 2 llm-chat brainstorm prompt — this is the canonical inter-phase data carrier when `/research-lit → /idea-creator` are chained (e.g. via `/auto-claim`). Standalone `/idea-creator` calls (no prior `/research-lit`) run their own fallback survey and write `LANDSCAPE.md` themselves using this same template. Still **not a resume gate** — upstream skills (`/auto-claim`) key resume on the downstream deliverable `IDEA_REPORT.md`, not on `LANDSCAPE.md`.

> 💡 Overrides:
> - `/research-lit "topic" — paper library: ~/my_papers/` — custom local PDF path
> - `/research-lit "topic" — extra: semantic-scholar` — also run Semantic Scholar API (published venue papers)
> - `/research-lit "topic" — extra: deepxiv` — also run DeepXiv progressive retrieval
> - `/research-lit "topic" — extra: exa` — also run Exa broad web search
> - `/research-lit "topic" — extra: semantic-scholar, deepxiv` — combine multiple extras
> - `/research-lit "topic" — arxiv download: true` — download top relevant arXiv PDFs
> - `/research-lit "topic" — arxiv download: true, max download: 10` — download up to 10 PDFs

## Data Sources

This skill has a **fixed base source set** that runs on every invocation, plus three **opt-in extras** toggled by `— extra:`.

### Base sources (always run all, anyone not skipable)

`zotero` + `obsidian` + `local` + `web` + `arxiv` + `mechanic-db`.

If any of Zotero / Obsidian / local PDFs isn't configured or present, that one is skipped silently — but the rest of the base set still runs. `web` and `arxiv` (via the `/arxiv` skill) are always available and always invoked.

### Opt-in extras (via `— extra:`)

These three are NOT part of the base set because each one is a costly external API or CLI that should only run when the upstream task explicitly calls for it. Toggle with `— extra: <name>` (comma-separated for multiple):

- `semantic-scholar` — Semantic Scholar API for published venue papers (IEEE/ACM/Springer) with citation counts and TLDR
- `deepxiv` — DeepXiv CLI progressive retrieval (search → brief → head → section)
- `exa` — Exa AI-powered broad web search with content extraction

If `— extra:` is absent, none of these run.

### Source Table

| Priority | Source | ID | How to detect | What it provides |
|----------|--------|----|---------------|-----------------|
| 1 | **Zotero** (via MCP) | `zotero` | Try calling any `mcp__zotero__*` tool — if unavailable, skip | Collections, tags, annotations, PDF highlights, BibTeX, semantic search |
| 2 | **Obsidian** (via MCP) | `obsidian` | Try calling any `mcp__obsidian-vault__*` tool — if unavailable, skip | Research notes, paper summaries, tagged references, wikilinks |
| 3 | **Local PDFs** | `local` | `Glob: papers/**/*.pdf, literature/**/*.pdf` | Raw PDF content (first 3 pages) |
| 4 | **mechanic-db SEARCH (cloud)** | `mechanic-db` | Always available (via SKILL `/mechanic-db-search`) | ~14k AI-interpretability papers and ~157M cross-disciplinary papers (e.g., from neuroscience, cognitive science, physics, biology, and the humanities), all organized as a knowledge graph. |
| 5 | **Web search** | `web` | Always available | arXiv, Semantic Scholar, Google Scholar |
| 6 | **arXiv API** | `arxiv` | Always available (via SKILL `/arxiv`) |
| 7 | **Semantic Scholar API** | `semantic-scholar` | `scripts/semantic_scholar_fetch.py` exists | Published venue papers (IEEE, ACM, Springer) with structured metadata: citation counts, venue info, TLDR. **Opt-in via `— extra: semantic-scholar`** |
| 8 | **DeepXiv CLI** | `deepxiv` | `scripts/deepxiv_fetch.py` and installed `deepxiv` CLI | Progressive paper retrieval: search, brief, head, section, trending, web search. **Opt-in via `— extra: deepxiv`** |
| 9 | **Exa Search** | `exa` | `scripts/exa_search.py` and installed `exa-py` SDK | AI-powered broad web search with content extraction (highlights, text, summaries). Covers blogs, docs, news, companies, and research papers beyond arXiv/S2. **Opt-in via `— extra: exa`** |

## Workflow

> **Execution order is strict.** Run steps in numbered order: 0 → 0a → 0b → 0c → 0d → 1 → 2 → 3 → 4 → 5. Each step must produce its result block (or an explicit "skipped: <reason>" note) before the next step begins. **The one and only place parallelism is allowed is *inside* Step 1**, where the mechanic-db SEARCH lane and the external-search lane run concurrently (see Step 1). Every other step transition is strictly sequential — do not reorder, do not parallelize *across* steps, and do not skip ahead to a later step because it feels more "important" or "costly". In particular: **the mechanic-db SEARCH (Step 1, Lane A) is very important and DO NOT omit** unless the cloud service is unavailable.

### Step 0: Load Prior Banlist (if available)

**Skip this step entirely if `research-wiki/` does not exist.** This is the *reader* counterpart to Step 6 (which *writes* the wiki). It seeds the search with prior context and — critically — carries the failed-idea **banlist** forward into `LANDSCAPE.md` (Step 5.2), so `/idea-creator`'s generation step can avoid repeating dead ends.

```
if research-wiki/query_pack.md exists AND is less than 7 days old:
    Read query_pack.md and use it as follows:
    - Treat listed gaps as priority search seeds for Step 1 (both lanes)
    - Treat top papers as known prior work (do not re-search them)
    - Extract the "Failed Ideas (avoid repeating)" section verbatim and carry it
      forward — it becomes the Banlist in LANDSCAPE.md Step 5.2 (do NOT discard it)
else if research-wiki/ exists but query_pack.md is stale or missing:
    python3 tools/research_wiki.py rebuild_query_pack research-wiki/
    Then read query_pack.md as above
else:
    skip — no wiki, banlist is empty
```

### Step 0a: Search Zotero Library (if available)

**Skip this step entirely if Zotero MCP is not configured.**

Try calling a Zotero MCP tool (e.g., search). If it succeeds:

1. **Search by topic**: Use the Zotero search tool to find papers matching the research topic
2. **Read collections**: Check if the user has a relevant collection/folder for this topic
3. **Extract annotations**: For highly relevant papers, pull PDF highlights and notes — these represent what the user found important
4. **Export BibTeX**: Get citation data for relevant papers (useful for `/paper-write` later)
5. **Compile results**: For each relevant Zotero entry, extract:
   - Title, authors, year, venue
   - User's annotations/highlights (if any)
   - Tags the user assigned
   - Which collection it belongs to

> 📚 Zotero annotations are gold — they show what the user personally highlighted as important, which is far more valuable than generic summaries.

### Step 0b: Search Obsidian Vault (if available)

**Skip this step entirely if Obsidian MCP is not configured.**

Try calling an Obsidian MCP tool (e.g., search). If it succeeds:

1. **Search vault**: Search for notes related to the research topic
2. **Check tags**: Look for notes tagged with relevant topics (e.g., `#diffusion-models`, `#paper-review`)
3. **Read research notes**: For relevant notes, extract the user's own summaries and insights
4. **Follow links**: If notes link to other relevant notes (wikilinks), follow them for additional context
5. **Compile results**: For each relevant note:
   - Note title and path
   - User's summary/insights
   - Links to other notes (research graph)
   - Any frontmatter metadata (paper URL, status, rating)

> 📝 Obsidian notes represent the user's **processed understanding** — more valuable than raw paper content for understanding their perspective.

### Step 0c: Scan Local Paper Library

Before searching online, check if the user already has relevant papers locally:

1. **Locate library**: Check PAPER_LIBRARY paths for PDF files
   ```
   Glob: papers/**/*.pdf, literature/**/*.pdf
   ```

2. **De-duplicate against Zotero**: If Step 0a found papers, skip any local PDFs already covered by Zotero results (match by filename or title).

3. **Filter by relevance**: Match filenames and first-page content against the research topic. Skip clearly unrelated papers.

4. **Summarize relevant papers**: For each relevant local PDF (up to MAX_LOCAL_PAPERS):
   - Read first 3 pages (title, abstract, intro)
   - Extract: title, authors, year, core contribution, relevance to topic
   - Flag papers that are directly related vs tangentially related

5. **Build local knowledge base**: Compile summaries into a "papers you already have" section. This becomes the starting point — external search fills the gaps.

> 📚 If no local papers are found, skip to Step 1. If the user has a comprehensive local collection, the external search can be more targeted (focus on what's missing).

### Step 0d: Clarify an ambiguous topic (ask before the expensive search)

A survey aimed at the wrong reading of the topic wastes the slow cloud call and produces an off-target `LANDSCAPE.md`. Before Step 1, judge whether `$ARGUMENTS` is **genuinely ambiguous** — two or more plausible interpretations that would send the search (and the downstream ideas) in materially different directions. Typical triggers: an acronym/term with multiple field meanings; underspecified scope (method vs. phenomenon vs. application vs. survey, unclear time window, unclear model/domain); a cross-domain phrase that could be AI-interpretability *or* a human-science field; a named entity that resolves several ways.

> **Worked example — `"LLM belief"`.** Genuinely ambiguous; readers emphasize different things. Plausible readings to offer: (a) **belief representation / probing** — does the model linearly encode a truth/belief direction in its activations; (b) **belief revision & consistency** — how stated beliefs update under evidence or contradict across a conversation; (c) **epistemic calibration** — confidence/uncertainty vs. correctness; (d) **theory-of-mind / belief attribution** — modeling *other agents'* beliefs (false-belief tasks). Each routes to different keywords, `db`, enums, and competitive sets.

**Decision:**
- **First, try to disambiguate from context** (R10): if `task.md`, the upstream research goal, prior turns, the Step 0 `query_pack.md`, or a caller-passed scope already pin the reading, use that — no need to ask.
- **Else, if clearly ambiguous and you can ask → use the `AskUserQuestion` tool** to present 2–4 candidate interpretations as an options box, most-likely first and labelled `(recommended)`, each with a one-line note on what the survey would then cover. Keep it to one focused question (two at most). Search according to the user's choice.
- **Else (unambiguous, or non-interactive)** → proceed with the single most likely interpretation and **record it** in `LANDSCAPE.md`'s Scope line ("Interpreted as: …"). Never manufacture ambiguity for a clear topic — a needless prompt is worse than a sensible default.

### Step 1: Search (mechanic-db ‖ external — two lanes, run concurrently)

**Precondition:** Steps 0, 0a, 0b, 0c, 0d have each produced their result block (or an explicit "skipped: <reason>" note). Do not start this step until then.

> **Parallelism — the only place it is allowed.** This step has two lanes:
> - **Lane A — mechanic-db cloud SEARCH** (slow, ~3-10 min per call)
> - **Lane B — external search** (WebSearch + arXiv + opt-in extras)
>
> **Launch Lane A first** — it is the slow cloud call — then, *without waiting for it to return*, run Lane B in parallel while Lane A is in flight. Both lanes must complete (or be marked "skipped: <reason>") before Step 2 begins. This concurrency is confined to Step 1; no other steps overlap. De-duplicate Lane A results against Lane B by normalized title once both lanes return.

#### Lane A: SEARCH (mechanic-db) — launch first

This lane runs on every invocation **unless the cloud SEARCH service is unavailable** — in which case the skill silently records "mechanic-db skipped" in the "Sources scanned" line of `RESEARCH_LIT.md` and moves on. It is the integration point for the cloud `mechanic_database` SEARCH service (interp_db + sciatlas_db).

1. **Build the decomposed query** using the Agent's full context. The Agent sees `task.md`, the upstream research goal, prior search results and analysis — use that context to route the query into **at most one sub-query per database** (interp_db / sciatlas_db), packing any cross-domain breadth into the relevant database's single sub-query. The JSON schema, routing rules, and closed enums are documented in `/mechanic-db-search`.

2. **Invoke** `/mechanic-db-search` with the crafted query. The skill then calls the `mechanic-db` MCP server's `search_papers` tool.

3. **Read** the result JSON. If `"skipped": true`, this source is unavailable for this run — note it in `RESEARCH_LIT.md` and move on. Otherwise, merge the returned `papers[]` into the downstream paper pool. De-duplicate against other sources by normalized title.

4. **Multi-round refinement**. When after Step 3 the merged corpus has clear gaps (sub-area entirely missing, off-topic flood, recency mismatch), refine the decomposition (sharpen `semantic_query` / `keywords` / `hyde_text`, fix the interp enums, flip `temporal_mode`, or set `year_min` / `recent_alpha`) and call `/mechanic-db-search` again. Cap at 3 rounds. Each round produces a fresh result JSON in `./mechanic_db_cache/`.

#### Lane B: External search (web + arXiv + Semantic Scholar + DeepXiv + Exa)

- Use WebSearch to find recent papers on the topic — **use 5+ different query formulations** (the distinct queries you ran are recorded in `RESEARCH_LIT.md`'s "Query formulations used" line)
- Check arXiv, Semantic Scholar, Google Scholar
- Focus on papers from last 2 years unless studying foundational work; for the frontier, also pull arXiv preprints from the **last 6 months**
- Read the abstracts and introductions of the **top 15-20 papers, ranked by relevance to the research task**
- **De-duplicate**: Skip papers already found in Zotero, Obsidian, or local library

**arXiv API search** (always runs, no download by default):

Locate the fetch script and search arXiv directly:
```bash
# Resolve arxiv_fetch.py from the sibling /arxiv skill.
SCRIPT="${CLAUDE_SKILL_DIR}/../arxiv/scripts/arxiv_fetch.py"
[ -f "$SCRIPT" ] || SCRIPT=""

# Search arXiv API for structured results (title, abstract, authors, categories).
[ -n "$SCRIPT" ] && python3 "$SCRIPT" search "QUERY" --max 10
```

If `arxiv_fetch.py` is not found at the sibling skill path, use the **inline-Python arXiv-API fallback** documented in `/arxiv` (Step 2) — arXiv is a base source and must run, so do **not** silently drop to WebSearch-only.

The arXiv API returns structured metadata (title, abstract, full author list, categories, dates) — richer than WebSearch snippets. Merge these results with WebSearch findings and de-duplicate.

**Semantic Scholar API search** (only when `semantic-scholar` is in sources):

When `— extra: semantic-scholar` is specified, search for published venue papers beyond arXiv:

```bash
S2_SCRIPT="${CLAUDE_SKILL_DIR}/scripts/semantic_scholar_fetch.py"
[ -f "$S2_SCRIPT" ] || S2_SCRIPT=""

# Search for published CS/Engineering papers with quality filters
[ -n "$S2_SCRIPT" ] && python3 "$S2_SCRIPT" search "QUERY" --max 10 \
    --fields-of-study "Computer Science,Engineering" \
    --publication-types "JournalArticle,Conference"
```

If `semantic_scholar_fetch.py` is not found, skip silently.

**Why use Semantic Scholar?** Many IEEE/ACM journal papers are NOT on arXiv. S2 fills the gap for published venue-only papers with citation counts and venue metadata.

**De-duplication between arXiv and S2**: Match by arXiv ID (S2 returns `externalIds.ArXiv`):
- If a paper appears in both: check S2's `venue`/`publicationVenue` — if it has been published in a journal/conference (e.g. IEEE TWC, JSAC), use S2's metadata (venue, citationCount, DOI) as the authoritative version, since the published version supersedes the preprint. Keep the arXiv PDF link for download.
- If the S2 match has no venue (still just a preprint indexed by S2): keep the arXiv version as-is.
- S2 results without `externalIds.ArXiv` are **venue-only papers** not on arXiv — these are the unique value of this source.

**DeepXiv search** (only when `deepxiv` is in sources):

When `— extra: deepxiv` is specified, use the DeepXiv adapter for progressive retrieval:

```bash
# Resolve deepxiv_fetch.py from this skill's bundled scripts.
DEEPXIV_SCRIPT="${CLAUDE_SKILL_DIR}/scripts/deepxiv_fetch.py"
[ -f "$DEEPXIV_SCRIPT" ] || DEEPXIV_SCRIPT=""

[ -n "$DEEPXIV_SCRIPT" ] && python3 "$DEEPXIV_SCRIPT" search "QUERY" --max 10
```

Then deepen only for the most relevant papers:

```bash
[ -n "$DEEPXIV_SCRIPT" ] && python3 "$DEEPXIV_SCRIPT" paper-brief ARXIV_ID
[ -n "$DEEPXIV_SCRIPT" ] && python3 "$DEEPXIV_SCRIPT" paper-head ARXIV_ID
[ -n "$DEEPXIV_SCRIPT" ] && python3 "$DEEPXIV_SCRIPT" paper-section ARXIV_ID "Experiments"
```

If `scripts/deepxiv_fetch.py` or the `deepxiv` CLI is unavailable, skip this source gracefully and continue with the remaining requested sources.

**Why use DeepXiv?** It is useful when a broad search should be followed by staged reading rather than immediate full-paper loading. This reduces unnecessary context while still surfacing structure, TLDRs, and the most relevant sections.

**De-duplication against arXiv and S2**:
- Match by arXiv ID first, DOI second, normalized title third
- If DeepXiv and arXiv refer to the same preprint, keep one canonical paper row and record `deepxiv` as an additional source
- If DeepXiv overlaps with S2 on a published paper, prefer S2 venue/citation metadata in the final table, but keep DeepXiv-derived section notes when they add value

**Exa search** (only when `exa` is in sources):

When `— extra: exa` is specified, use the Exa tool for broad AI-powered web search with content extraction:

```bash
EXA_SCRIPT="${CLAUDE_SKILL_DIR}/scripts/exa_search.py"
[ -f "$EXA_SCRIPT" ] || EXA_SCRIPT=""

# Search for research papers with highlights
[ -n "$EXA_SCRIPT" ] && python3 "$EXA_SCRIPT" search "QUERY" --max 10 --category "research paper" --content highlights

# Search for broader web content (blogs, docs, news)
[ -n "$EXA_SCRIPT" ] && python3 "$EXA_SCRIPT" search "QUERY" --max 10 --content highlights
```

If `scripts/exa_search.py` or the `exa-py` SDK is unavailable, skip this source gracefully and continue with the remaining requested sources.

**Why use Exa?** Exa provides AI-powered search across the broader web (blogs, documentation, news, company pages) with built-in content extraction. It fills a gap between academic databases (arXiv, S2) and generic WebSearch by returning richer content with each result.

**De-duplication against arXiv, S2, and DeepXiv**:
- Match by URL first, then normalized title
- If Exa returns an arXiv paper already found by arXiv/S2, prefer the structured metadata from those sources
- Exa results from non-academic domains (blogs, docs, news) are unique value not covered by other sources

**Optional PDF download** (only when `ARXIV_DOWNLOAD = true`):

After all sources are searched and papers are ranked by relevance:
```bash
# Download top N most relevant arXiv papers
[ -n "$SCRIPT" ] && python3 "$SCRIPT" download ARXIV_ID --dir papers/
```
- Only download papers ranked in the top ARXIV_MAX_DOWNLOAD by relevance
- Skip papers already in the local library
- 1-second delay between downloads (rate limiting)
- Verify each PDF > 10 KB

### Step 2: Analyze Each Paper
For each relevant paper (from all sources), extract:
- **Problem**: What gap does it address?
- **Method**: Core technical contribution (1-2 sentences)
- **Results**: Key numbers/claims
- **Relevance**: How does it relate to our work?
- **Source**: Where we found it (Zotero/Obsidian/local/web) — helps user know what they already have vs what's new

### Step 3: Synthesize
- Group papers by approach/theme
- Identify consensus vs disagreements in the field
- Note recurring limitations mentioned in "Future Work" sections, and open problems stated by multiple papers
- **Identify structural gaps** — scan explicitly for each of these kinds (this taxonomy feeds the "Structural Gaps" section of `LANDSCAPE.md` Step 5.2):
  - Methods that work in domain A but haven't been tried in domain B
  - Contradictory findings between papers (opportunity for resolution)
  - Assumptions that everyone makes but nobody has tested
  - Scaling regimes that haven't been explored
  - Diagnostic questions that nobody has asked
- If Obsidian notes exist, incorporate the user's own insights into the synthesis

### Step 4: Output
Present as a structured literature table:

```
| Paper | Venue | Method | Key Result | Relevance to Us | Source |
|-------|-------|--------|------------|-----------------|--------|
```

Plus a narrative summary of the landscape (3-5 paragraphs).

If Zotero BibTeX was exported, include a `references.bib` snippet for direct use in paper writing.

### Step 5: Save

**5.1 — Raw retrieval dump (always, unconditional)**

Write the raw retrieved content (every paper actually fetched in Steps 1–3, before synthesis) to `<OUTPUT_DIR>/RESEARCH_LIT.md`. Default `OUTPUT_DIR` is `idea-stage/` (`mkdir -p` it if missing). This is the audit trail for **what was pulled**, not what it means — keep abstracts/intros verbatim, do not paraphrase.

Suggested file template:

```markdown
# Raw Literature Retrieval: <topic from $ARGUMENTS>

**Date**: <YYYY-MM-DD>
**Query**: <one-line from $ARGUMENTS>
**Sources scanned**: <which of mechanic-db / arXiv / S2 / Zotero / Obsidian / local / Exa / DeepXiv were actually queried; mark absent ones
**Query formulations used**:
- <query 1>
- <query 2>
- ...

---

## Retrieved Papers

### Paper 1: <Title>
- **Authors**: <author list>
- **Year**: <year>
- **Venue**: <venue or "arXiv preprint">
- **Source**: <mechanic-db / arXiv API / Semantic Scholar / Zotero / Obsidian / local PDF / WebSearch / Exa / DeepXiv>
- **Identifier**: <arXiv ID / DOI / file path>
- **URL**: <link if available>

**Abstract**:
<full abstract text, verbatim>

**Introduction / first pages** (only when available — local PDFs read first 3 pages; arXiv via WebFetch when fetched):
<intro text, verbatim>

---

### Paper 2: ...
```

Order papers by relevance to the topic (most relevant first) or by source priority (Zotero → Obsidian → local → mechanic-db results → arXiv API → WebSearch). Note papers de-duplicated across sources by listing all matched sources in the `Source` field (e.g., `Source: arXiv API + WebSearch`).

**5.2 — Synthesized landscape (always, unconditional)**

Write the Step 4 output — the structured paper table + 3-5 paragraph narrative + structural gaps — to `<OUTPUT_DIR>/LANDSCAPE.md`. This is the **digested** view: what downstream phases (idea brainstorm prompts, gap-driven idea generation) actually consume conceptually. The raw papers behind it live in `RESEARCH_LIT.md`.

Suggested file template:

```markdown
# Landscape: <topic from $ARGUMENTS>

**Date**: <YYYY-MM-DD>
**Scope**: <one-line scope, including any year cutoff; if the topic was ambiguous, lead with "Interpreted as: <disambiguated reading>" per Step 0d>
**Based on**: <N> retrieved papers — see `RESEARCH_LIT.md` for the raw retrieval dump

---

## 1. Structured Paper Table

| Paper | Venue | Method | Key Result | Relevance to Us | Source |
|-------|-------|--------|------------|-----------------|--------|

## 2. Core Landscape Narrative

<3-5 paragraphs describing the current state of the field, grouped by sub-direction / approach, with consensus and disagreements called out>

## 3. Sub-direction-Specific Work

<group by sub-direction; for each, list the most representative works with one-line takeaways and the gap it leaves>

## 4. Structural Gaps

<explicit gaps from Step 3, one per bullet, each tied to a competitive set>:
- **Gap G1** — <description> — *Competitive set*: <papers> — *Why open*: <reason>
- **Gap G2** — ...

## 5. Banlist — Failed Ideas (do not regenerate)

<paste the "Failed Ideas (avoid repeating)" entries extracted from `research-wiki/query_pack.md` in Step 0 when available, verbatim (title + why it failed). These are ideas already tried and abandoned; `/idea-creator` pastes this section into its brainstorm prompt so the generator does not re-propose them or close variants. If no prior banlist is active, write exactly: _(no prior banlist)_>
- **<failed idea title>** — <why it failed>
- ...
```

**Important — file roles differ:**

- `RESEARCH_LIT.md` is a **pure audit artifact** — never read back by any downstream skill. Only for human inspection.
- `LANDSCAPE.md` is the **canonical inter-phase data carrier**: `/idea-creator` Phase 1 reads it from disk when present, and Phase 2 pastes it into the llm-chat brainstorm prompt. Standalone `/idea-creator` calls (no prior `/research-lit`) run a fallback survey and write `LANDSCAPE.md` themselves using the Step 5.2 template.

**Neither file is a resume gate.** Overwriting on re-run is intended: both files always reflect the most recent retrieval. Resume protocols in upstream skills must continue keying off their own downstream deliverables (e.g. `IDEA_REPORT.md`), never off these files. Rationale: if `IDEA_REPORT.md` is missing, we have no proof the Phase 1 → Phase 2 chain completed; re-running Phase 1 to overwrite `LANDSCAPE.md` fresh is safer than trusting an interrupted run's leftovers.

**5.3 — Optional saves (only when explicitly requested)**

- Save downloaded paper PDFs to `papers/` (when `ARXIV_DOWNLOAD = true`)
- Update related work notes in project memory
- If Obsidian is available, optionally create a literature review note in the vault

## Key Rules
- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Be honest about limitations of each paper
- Note if a paper directly competes with or supports our approach
- **Never fail because a MCP server is not configured** — always fall back gracefully to the next data source
- Zotero/Obsidian tools may have different names depending on how the user configured the MCP server (e.g., `mcp__zotero__search` or `mcp__zotero-mcp__search_items`). Try the most common patterns and adapt.

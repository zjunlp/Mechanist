---
name: mhistory
description: "Generate a structured, publication-quality research-history markdown article for a given topic. Uses the cloud `mechanic_database` SEARCH service via skill `/mechanic-db-search` (TWO PARALLEL passes — `temporal_mode=history` for the long arc + `temporal_mode=recent` for the frontier), then supplements with WebSearch for pre-DB classics and the last 1–6 months of arXiv work. Triggers: 'research history', 'development history', 'survey of X', 'trace the evolution of …'."
---

# Research Development-History Generator

Produce a **fact-grounded, chronologically clear, classics-plus-frontier** development-history article for a given research direction.

## When to trigger

- The user asks for "a development history of X", "trace the evolution of X", "how X got to where it is today", or the Chinese equivalents (发展史 / 综述 / 来龙去脉).
- The user explicitly invokes `/mhistory <topic>`.

## Core principles

1. **Retrieval goes through the cloud SEARCH service** via the `/mechanic-db-search` skill. The Agent submits an English query per pass; the service then return a paper list.
2. **Two-track retrieval, run in parallel**: launch `/mechanic-db-search` twice **at the same time** — once with `temporal_mode=history` (5-year buckets, even coverage across eras) and once with `temporal_mode=recent` (recency-boosted, modern frontier).
3. **Web supplementation** with `WebSearch`, for two purposes:
   - **history gap-fill**: the DB may miss some foundational work.
   - **Frontier gap-fill**: DB indexing lags; arXiv work from the last 1–6 months is usually absent.
4. **Graceful degradation**: If `/mechanic-db-search` does not work properly, both DB passes silently skip (the `search_papers` tool writes `{"papers": [], "skipped": true}` to each output) — the article is then built from WebSearch + Claude's own knowledge, and the final markdown explicitly notes "mechanic-db unavailable".

## Pipeline

```
   topic (free-form text from user)
        │
        ├──┬──► [1a] /mechanic-db-search  (temporal_mode=history, top_k=100)  ┐
        │  │                                                                       ├─ launched in parallel
        │  └──► [1b] /mechanic-db-search  (temporal_mode=recent,     top_k=100)  ┘
        │        → two cached final-JSON files
        │
        ├──► [2] WebSearch × N
        │        - history gap-fill ("<topic> seminal paper", "<topic> foundational work pre-2018", …)
        │        - Last-1–6-months gap-fill ("<topic> arxiv 2026", "<topic> latest", …)
        │
        └──► [3] Claude (this session) synthesises markdown and writes it to disk
```

## Steps

### Step 0 — Parse topic, derive slug

- Extract `<topic>` from the user's request (free text, Chinese or English).
- Compute a deterministic slug from the topic (ASCII-lowercase, spaces → `_`, strip punctuation). Pure bash works:
  ```bash
  SLUG=$(echo "<topic>" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '_' | sed -E 's/_+/_/g; s/^_+|_+$//g')
  ```
- Ensure the output dirs exist: `mkdir -p mechanic_db_cache`.

### Step 1 — Two parallel mechanic-db passes

Craft one polished English query that names the topic + key sub-fields (≤80 words). The same query string is used for both passes; only `temporal_mode` differs.

Retrieval goes through the **`search_papers`** MCP tool (mechanic-db server) — see `/mechanic-db-search` for the full contract. Issue **both passes as two parallel tool calls in a single turn** (the tool blocks ~3-20 min each; running them concurrently halves the wait). Each call writes its full result JSON to an **absolute** `output` path (run `pwd` once to get `<ABS_PWD>`):

```text
# Pass 1a — history arc
search_papers:
  output:        <ABS_PWD>/mechanic_db_cache/<SLUG>__hist.json
  query:         <the polished English query>
  temporal_mode: history
  top_k:         100

# Pass 1b — recent frontier
search_papers:
  output:        <ABS_PWD>/mechanic_db_cache/<SLUG>__recent.json
  query:         <the polished English query>
  temporal_mode: recent
  top_k:         100
```


### Step 2 — WebSearch supplementation

Use the `WebSearch` tool. Fire 2–4 queries per purpose:

**history gap-fill (find canonical references, anchor the timeline)**
- `"<topic>" seminal foundational paper before 2020`
- `"<topic>" history review survey`
- For NLP/ML topics, append `site:arxiv.org` or `site:aclanthology.org`.

**Last-1–6-months gap-fill (cover the DB's indexing blind spot)**
- `"<topic>" arxiv 2026` / current year
- `"<topic>" latest 2025 2026`
- If the topic is cross-domain, run one query per sub-domain.

Assemble the returned (title / authors / year / URL / snippet) into a short markdown block in context — no need to write it to disk.

> If WebSearch fails or is unavailable, skip this step and rely on DB retrieval + Claude's own knowledge. But the final markdown must explicitly state "WebSearch unavailable".

### Step 3 — Synthesise the markdown

Write the article in this session. Material preparation:

1. Load the two cached final-JSON files. Skip any that have `"skipped": true`. Merge the surviving `papers` lists, dedupe by `paper_id`. Keep every paper's `title / year / cited_by_count / abstract / doi / authors`.
2. Organise the WebSearch results (title / authors / year / URL / snippet) into a parallel list, tagged as `[Web]`.
3. **Internalise the writing brief below — it is the core authoring instruction of this skill, not optional flavour text.**

---

> **Persona.** You are a senior research scholar writing a thorough development-history article for a research community. You combine your own broad knowledge of the literature with the curated set of supplementary papers the user has provided. Your output is rigorous, chronologically organised, and cites specific paper titles **only when supported**.
>
> **How to use the supplementary paper bundle.** The bundle (DB + Web) is **supplementary, not authoritative**:
> - It is generated by a retrieval pipeline that may have missed relevant papers. There **will** be canonical works absent from the bundle that you must add from your own knowledge.
> - It may include borderline / peripheral papers that aren't truly central. Use your judgement — cite a paper from the bundle **only when it actually deserves to be cited**.
> - The bundle gives you exact titles, authors, years, DOI / arXiv URLs you can quote verbatim. Whenever you would otherwise paraphrase a citation, prefer the bundle's exact form.
> - Treat `[Web]`-tagged entries as part of the same bundle, but track their origin in the citation list.
>
> **Required structure.** Organise the article by **chronological eras or thematic phases** (your choice; pick whichever best captures the field). Within each era / phase:
> - Trace the **evolution of ideas**: what problem was being solved, what breakthrough enabled the next phase, what limitation forced researchers to a new approach.
> - Cite **specific papers** with `title (first-author surname, year)`. When citing from the bundle, prefer the bundle's exact title.
> - Include both **classical foundations** (pre-2020 if applicable) and **2024–2026 frontier work**.
> - If the topic has multiple research lines, **cover them in parallel**; do not collapse everything into a single narrative thread.
>
> **Anti-patterns to AVOID.**
> - Listing only papers from the bundle — your own knowledge of the field must drive the narrative; the bundle just supplies citation precision.
> - Over-relying on the bundle's most-cited papers — recency and conceptual novelty matter as much as citation count.
> - **Inventing paper titles.** If you're unsure of a title, paraphrase the contribution and omit the citation.
> - Generic survey-style writing. Be specific about **what** each paper showed, not just that it exists.
>
> **Output format.**
> - Markdown. Use `#` / `##` / `###` for structure.
> - Target length **2500–4500 words**.
> - **End with a "Tensions and Open Questions" section** covering live debates and unresolved problems in this area as of 2025–2026.
> - Suggested skeleton (adapt freely as long as the above requirements hold):
>   ```
>   # <topic>
>   ## TL;DR
>   ## history arc (organised by era / thematic phase)
>   ## Contemporary landscape (2023–2025)
>   ## Frontier (last 1–6 months — mark each item as [DB] or [Web])
>   ## Tensions and Open Questions
>   ## References ([DB] and [Web] sections, with DOI / arXiv URL)
>   ```

---

4. Write the result to `development_history.md`.
5. Print a short terminal summary: # of DB papers used (or "DB unavailable" per pass), # of Web supplements, final markdown word count, output path.


## Input / output contract

**Input**: a free-text topic (Chinese or English), optional slug.

**Output files**:
- `mechanic_db_cache/<slug>__hist.json`   (cached cloud-service result for the history pass; may be `{"skipped": true}`)
- `mechanic_db_cache/<slug>__recent.json` (cached cloud-service result for the recent pass; may be `{"skipped": true}`)
- `development_history.md`   ← the deliverable
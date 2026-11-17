---
name: information-retrieval
description: "Fill gaps in your knowledge or current context by finding and obtaining external information from papers, blogs, GitHub projects, documentation, and other web pages. Use when information may be incomplete, outdated, uncertain, or needs verification against sources."
---

# Information retrieval

Your existing knowledge and current context may be incomplete or outdated. You may be missing a relevant finding, implementation, discussion, or source needed to check a claim. This skill provides additional information channels. Consider using it when an unanswered question, unfamiliar topic, uncertain recollection, or need for current evidence calls for information beyond what you already have. Judge whether the retrieved material actually closes the gap; search results themselves can be incomplete or misleading.

Find and obtain information for **$ARGUMENTS** from the sources that fit. This can include papers, blog posts, technical reports, GitHub repositories and discussions, project pages, documentation, datasets, and other web material. Choose sources according to the information gap; a request need not be framed as a literature review.

Use the host's search, browsing, file-reading, or connected-source tools when available. The bundled scripts below add particular retrieval backends; they do not limit the scope of this skill or require every request to pass through an academic database. Use the available host tools to inspect blogs, GitHub work, and ordinary pages directly. Do not claim that a missing browser, connector, or provider is available.

Follow useful leads, refine queries, and inspect the material needed to answer the actual question. A snippet or abstract can identify a candidate source but does not establish everything in the underlying page or paper. For GitHub work, distinguish repository descriptions from inspected implementations, issues, examples, and documentation; note the relevant release or commit when a technical detail depends on it.

Keep source URLs or identifiers and distinguish author claims, implementation details, reported observations, and your own synthesis. Assess authority, recency, directness, and relevance without treating citation counts, stars, or source format as proof. Compare contradictory accounts where they matter. Deduplicate by URL, repository, DOI, arXiv identifier, or content as appropriate; distinguish retrieval failure from an empty successful result. Choose whether to fetch page text, files, metadata, or PDFs, and how to organize the output, according to the task.

For a field's development history, balance foundational work with recent findings. The database's `history` and `recent` temporal modes support these different retrieval goals; the service admits one search at a time. A retrieved bundle may miss classics or overrepresent highly cited work. Explain the problems, advances, and limitations that connect ideas, keeping parallel research lines visible where relevant.

## Sources

Choose the sources that answer the current question. Each bundled source keeps its scripts and any supporting instructions together under `sources/`. These are backends of information-retrieval, not separate skills or a required sequence.

| Source | Use | Script and details |
| --- | --- | --- |
| Host search, browser, and connected sources | General web pages, blogs, GitHub repositories and discussions, project documentation, and other available external sources | Use the host's actual capabilities; no dedicated GitHub connector or general browser is bundled here |
| Mechanic DB | Interpretability and cross-disciplinary retrieval, plain or structured queries, history/frontier bias | [sources/mechanic_db/search.py](sources/mechanic_db/search.py); [usage, configuration, and query construction](sources/mechanic_db/mechanic_db.md) |
| arXiv | Paper metadata, identifier lookup, and PDF downloads | [sources/arxiv/arxiv_fetch.py](sources/arxiv/arxiv_fetch.py); [usage](sources/arxiv/arxiv.md); Python standard library |
| Semantic Scholar | Published-paper metadata, citations, and DOI/arXiv/S2 identifier lookup | [sources/semantic_scholar/semantic_scholar_fetch.py](sources/semantic_scholar/semantic_scholar_fetch.py); optional `SEMANTIC_SCHOLAR_API_KEY`; Python standard library |
| DeepXiv | Progressive search, briefs, headings, and named sections | [sources/deepxiv/deepxiv_fetch.py](sources/deepxiv/deepxiv_fetch.py); requires the installed `deepxiv` CLI |
| Exa | Broader web search, similar pages, and extracted content across research, blogs, project sites, and documentation | [sources/exa/exa_search.py](sources/exa/exa_search.py); requires `exa-py` and `EXA_API_KEY` |

Resolve script paths from this skill directory and run them with the selected Python environment. For example:

```text
python /path/to/information-retrieval/sources/mechanic_db/search.py --query "feature steering" --output /path/to/papers.json
python /path/to/information-retrieval/sources/arxiv/arxiv_fetch.py search "activation patching" --max 10
python /path/to/information-retrieval/sources/arxiv/arxiv_fetch.py download 2301.07041 --dir /path/to/papers
python /path/to/information-retrieval/sources/semantic_scholar/semantic_scholar_fetch.py paper "arxiv:2301.07041"
```

Use `--help` on the selected script for its full command options. Mechanic DB has a [dependency file](sources/mechanic_db/requirements.txt); other dependencies are listed above. Credentials come from the execution environment. Scripts return structured results or explicit errors/unavailability; missing optional sources do not prevent other retrieval. Do not install or invoke every backend to satisfy a checklist. Decide how to combine results and where to keep them for the task.

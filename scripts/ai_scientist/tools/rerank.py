"""LLM re-ranking of a retrieved paper list.

mechanic-db returns a wide candidate pool (300 papers by default, 150 per
database) ordered by the retrieval pipeline's own fusion. That order is built
from embedding/BM25 channels which know the query only as bag-of-signals, so
the top of the list is recall-oriented rather than precision-oriented. This
module runs one cheap LLM pass over the pool to reorder it against the query as
written, and hands back the top-N.

The reranker is advisory, never load-bearing: every failure path (no API key,
gateway error, unparseable reply, hallucinated indices) falls back to the
retrieval order, so a bad rerank can only cost relevance, not the search.

Environment variables:
    MECHANIC_DB_RERANK_MODEL  - model for the rerank pass (default
                                claude-sonnet-5). Deliberately NOT tied to
                                IDEATION_MODEL: reranking spends ~30k input
                                tokens per database per search, so it wants a
                                cheaper model than idea generation does.
    MECHANIC_DB_RERANK_POOL   - max candidates shown to the LLM per call
                                (default 200); anything past that keeps its
                                retrieval rank and is appended after the
                                reranked head.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_POOL = 200
# The gateway spells versions with dashes and no dots — `claude-opus-4-8`, not
# `claude-opus-4.8` (see p1_env.sh) — so sonnet 5 is `claude-sonnet-5`.
DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_MESSAGE = (
    "You are a meticulous research librarian re-ranking literature search "
    "results for an AI research scientist. You judge relevance to the query as "
    "written, never by prestige, citation count, or recency on their own."
)

PROMPT_TEMPLATE = """A literature search returned the candidate papers below, ordered by a keyword/embedding retrieval pipeline. That pipeline matches surface signals, so its order is only a rough guide.

Re-rank the candidates by how directly useful each one is for a researcher working on this query:

QUERY:
{query}

Rank on substance:
- Does the paper address the query's actual phenomenon, mechanism, or method — not merely share vocabulary with it?
- Does it supply something the researcher can build on or must cite: a result, a technique, a dataset, a contradiction?
- Prefer specific, on-target work over broad surveys or loosely adjacent work.
Citation count and year are tie-breakers only.

CANDIDATES:
{candidates}

Return the {top_n} most useful candidates, best first, as their integer ids. Reply with ONLY this JSON block and nothing else:

```json
{{"ranking": [<id>, <id>, ...]}}
```"""


def rerank_model() -> str:
    return os.getenv("MECHANIC_DB_RERANK_MODEL") or DEFAULT_MODEL


def _clip(value: Any, limit: int) -> str:
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(v) for v in value)
    text = " ".join(str(value or "").split())
    return text[:limit] + " ..." if len(text) > limit else text


def _render_candidate(index: int, paper: Dict[str, Any]) -> str:
    lines = [
        f'[{index}] {_clip(paper.get("title"), 250) or "Untitled"} '
        f'({paper.get("year", "n.d.")}, '
        f'{paper.get("cited_by_count", paper.get("citationCount", "N/A"))} citations)'
    ]
    # interp_db rows carry these distilled fields and sciatlas_db rows never do,
    # so this quietly renders each database in the richest form it has.
    for label, field, limit in (
        ("Question", "research_question", 300),
        ("Contribution", "core_contribution", 300),
        ("Findings", "key_findings", 300),
    ):
        text = _clip(paper.get(field), limit)
        if text:
            lines.append(f"    {label}: {text}")
    if len(lines) == 1:
        lines.append(f'    Abstract: {_clip(paper.get("abstract"), 600) or "(none)"}')
    return "\n".join(lines)


def _parse_ranking(text: str, valid: range) -> List[int]:
    """Pull the id list out of the reply, tolerating prose around the JSON."""
    ranking: Optional[Sequence] = None
    match = re.search(r"```json(.*?)```", text or "", re.DOTALL)
    blobs = [match.group(1)] if match else re.findall(r"\{.*?\}", text or "", re.DOTALL)
    for blob in blobs:
        try:
            parsed = json.loads(re.sub(r"[\x00-\x1F\x7F]", "", blob.strip()))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("ranking"), list):
            ranking = parsed["ranking"]
            break
    if ranking is None:
        # Last resort: a bare list of numbers somewhere in the reply.
        numbers = re.findall(r"-?\d+", text or "")
        ranking = numbers if numbers else None
    if not ranking:
        return []

    seen = set()
    ordered = []
    for item in ranking:
        try:
            i = int(item)
        except (TypeError, ValueError):
            continue
        if i in valid and i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def rerank_papers(
    query: str,
    papers: List[Dict[str, Any]],
    top_n: int,
    *,
    client: Any = None,
    model: Optional[str] = None,
    label: str = "",
) -> List[Dict[str, Any]]:
    """Return the `top_n` papers most relevant to `query`, LLM-reordered.

    Falls back to `papers[:top_n]` — the retrieval order — whenever the rerank
    cannot be completed or the reply cannot be trusted.
    """
    if not papers:
        return []
    if top_n >= len(papers):
        # Nothing to choose between - every candidate reaches the prompt anyway.
        return papers[:top_n]

    tag = f"[{label}] " if label else ""
    try:
        from ai_scientist.llm import create_client, get_response_from_llm

        model = model or rerank_model()
        if client is None:
            client, model = create_client(model)

        pool_size = max(top_n, int(os.getenv("MECHANIC_DB_RERANK_POOL", DEFAULT_POOL)))
        pool, tail = papers[:pool_size], papers[pool_size:]
        candidates = "\n".join(
            _render_candidate(i, paper) for i, paper in enumerate(pool)
        )
        prompt = PROMPT_TEMPLATE.format(
            query=query, candidates=candidates, top_n=top_n
        )

        print(f"{tag}reranking {len(pool)} papers down to {top_n} with {model}")
        text, _ = get_response_from_llm(
            prompt,
            client=client,
            model=model,
            system_message=SYSTEM_MESSAGE,
            temperature=0.0,
        )
        ranking = _parse_ranking(text, range(len(pool)))
        if not ranking:
            raise ValueError("no usable ranking in the reranker reply")

        chosen = [pool[i] for i in ranking[:top_n]]
        if len(chosen) < top_n:
            # The model returned a short (or partly invalid) list; backfill from
            # retrieval order so the caller still gets the count it asked for.
            picked = set(ranking[:top_n])
            for i, paper in enumerate(pool + tail):
                if len(chosen) >= top_n:
                    break
                if i >= len(pool) or i not in picked:
                    chosen.append(paper)
            print(f"{tag}reranker returned {len(ranking)} ids, backfilled to {len(chosen)}")
        return chosen[:top_n]
    except Exception as e:
        print(f"{tag}[WARN] rerank failed, keeping retrieval order: "
              f"{type(e).__name__}: {e}")
        return papers[:top_n]

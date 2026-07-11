#!/usr/bin/env python3
"""CLI helper for searching Semantic Scholar's Graph API.

Used by the ``research-lit`` skill when the user passes
``— sources: semantic-scholar``. Complements ``arxiv_fetch.py`` by surfacing
published venue papers (IEEE, ACM, Springer) with citation counts and
venue metadata that arXiv-only search misses.

Commands
--------
search    Search Semantic Scholar and print results as JSON.
paper     Fetch metadata for a single paper by ID (DOI, arXiv:..., S2 paper ID).

Examples
--------
python3 skills/research-lit/scripts/semantic_scholar_fetch.py search "diffusion models" --max 10
python3 skills/research-lit/scripts/semantic_scholar_fetch.py search "channel estimation" \
    --fields-of-study "Computer Science,Engineering" \
    --publication-types "JournalArticle,Conference"
python3 skills/research-lit/scripts/semantic_scholar_fetch.py paper "10.1145/3580305.3599831"

Notes
-----
Set ``SEMANTIC_SCHOLAR_API_KEY`` in the environment for higher rate limits.
Unauthenticated requests work but throttle aggressively (HTTP 429).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_API_BASE = "https://api.semanticscholar.org/graph/v1"
_USER_AGENT = (
    "research-lit-skill/1.0 "
    "(github.com/wanshuiyin/Auto-claude-code-research-in-sleep)"
)
_DEFAULT_FIELDS = ",".join(
    [
        "paperId",
        "externalIds",
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "publicationVenue",
        "publicationTypes",
        "publicationDate",
        "citationCount",
        "referenceCount",
        "influentialCitationCount",
        "openAccessPdf",
        "tldr",
        "fieldsOfStudy",
        "url",
    ]
)


def _request(url: str) -> dict:
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    req = urllib.request.Request(url, headers=headers)
    for attempt in (1, 2, 3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < 3:
                time.sleep(2 * attempt)
                continue
            raise
    raise RuntimeError(f"Failed to fetch {url} after retries")


def _normalize_paper(raw: dict) -> dict:
    ext = raw.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv")
    doi = ext.get("DOI")
    pdf_info = raw.get("openAccessPdf") or {}
    venue = raw.get("venue") or ""
    pub_venue = raw.get("publicationVenue") or {}
    if not venue and isinstance(pub_venue, dict):
        venue = pub_venue.get("name", "") or ""
    tldr = raw.get("tldr") or {}
    return {
        "id": raw.get("paperId"),
        "title": (raw.get("title") or "").strip(),
        "authors": [a.get("name", "") for a in (raw.get("authors") or [])],
        "abstract": (raw.get("abstract") or "").strip(),
        "tldr": (tldr.get("text") or "").strip() if isinstance(tldr, dict) else "",
        "year": raw.get("year"),
        "published": raw.get("publicationDate") or "",
        "venue": venue,
        "publication_types": raw.get("publicationTypes") or [],
        "fields_of_study": raw.get("fieldsOfStudy") or [],
        "citation_count": raw.get("citationCount"),
        "influential_citation_count": raw.get("influentialCitationCount"),
        "reference_count": raw.get("referenceCount"),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "pdf_url": pdf_info.get("url") if isinstance(pdf_info, dict) else None,
        "s2_url": raw.get("url"),
        "abs_url": (
            f"https://arxiv.org/abs/{arxiv_id}"
            if arxiv_id
            else (f"https://doi.org/{doi}" if doi else raw.get("url"))
        ),
        "external_ids": ext,
    }


def search(
    query: str,
    max_results: int = 10,
    offset: int = 0,
    fields_of_study: str | None = None,
    publication_types: str | None = None,
    year: str | None = None,
    venue: str | None = None,
    min_citation_count: int | None = None,
) -> list[dict]:
    params: dict[str, str | int] = {
        "query": query,
        "limit": min(max(max_results, 1), 100),
        "offset": offset,
        "fields": _DEFAULT_FIELDS,
    }
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if publication_types:
        params["publicationTypes"] = publication_types
    if year:
        params["year"] = year
    if venue:
        params["venue"] = venue
    if min_citation_count is not None:
        params["minCitationCount"] = min_citation_count

    url = f"{_API_BASE}/paper/search?{urllib.parse.urlencode(params)}"
    payload = _request(url)
    return [_normalize_paper(p) for p in (payload.get("data") or [])]


def paper(paper_id: str) -> dict:
    pid = paper_id.strip()
    # Accept "arxiv:2301.07041" style or DOI/S2 paper ID directly.
    if pid.lower().startswith("arxiv:"):
        pid = "ARXIV:" + pid.split(":", 1)[1]
    encoded = urllib.parse.quote(pid, safe=":./")
    url = f"{_API_BASE}/paper/{encoded}?fields={_DEFAULT_FIELDS}"
    return _normalize_paper(_request(url))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search Semantic Scholar for published venue papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp = subparsers.add_parser("search", help="Search Semantic Scholar")
    sp.add_argument("query", help="Free-text search query.")
    sp.add_argument("--max", type=int, default=10, metavar="N",
                    help="Maximum number of results (default: 10, max: 100).")
    sp.add_argument("--offset", type=int, default=0,
                    help="Pagination offset (default: 0).")
    sp.add_argument("--fields-of-study", default=None,
                    help='Comma-separated, e.g. "Computer Science,Engineering".')
    sp.add_argument("--publication-types", default=None,
                    help='Comma-separated, e.g. "JournalArticle,Conference".')
    sp.add_argument("--year", default=None,
                    help='Year filter, e.g. "2023" or "2020-2024".')
    sp.add_argument("--venue", default=None,
                    help="Comma-separated venue filter.")
    sp.add_argument("--min-citation-count", type=int, default=None,
                    help="Minimum citation count.")

    pp = subparsers.add_parser("paper", help="Fetch a single paper by ID")
    pp.add_argument("id", help="DOI, arXiv:<id>, or S2 paper ID.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "search":
        results = search(
            args.query,
            max_results=args.max,
            offset=args.offset,
            fields_of_study=args.fields_of_study,
            publication_types=args.publication_types,
            year=args.year,
            venue=args.venue,
            min_citation_count=args.min_citation_count,
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if args.command == "paper":
        print(json.dumps(paper(args.id), ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""CLI helper for Exa AI-powered web search with content extraction.

Used by the ``research-lit`` skill when the user passes ``— sources: exa``.
Exa fills the gap between academic databases (arXiv, S2) and generic web
search by returning ranked results with built-in highlights / text / summary
extraction across blogs, docs, news, company pages, and research papers.

Requires the ``exa-py`` SDK (``pip install exa-py``) and ``EXA_API_KEY``
in the environment. If either is missing, exit 0 with a graceful payload
so the calling skill can continue with the remaining sources.

Commands
--------
search           AI-ranked search across the web.
find-similar     Find pages similar to a given URL.
contents         Fetch contents (highlights/text/summary) for a list of URLs.

Examples
--------
python3 skills/research-lit/scripts/exa_search.py search "diffusion language models" --max 10 \
    --category "research paper" --content highlights
python3 skills/research-lit/scripts/exa_search.py search "RLHF reward hacking" --max 10 \
    --content highlights --start-published 2024-01-01
python3 skills/research-lit/scripts/exa_search.py find-similar https://arxiv.org/abs/2301.07041 --max 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _graceful_unavailable(reason: str, command: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "reason": reason,
        "results": [],
    }


def _load_client():
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        return None, "EXA_API_KEY not set in environment"
    try:
        from exa_py import Exa  # type: ignore
    except ImportError:
        return None, "exa-py SDK not installed (pip install exa-py)"
    try:
        return Exa(api_key), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to initialize Exa client: {exc}"


def _serialize_result(item) -> dict:
    """Normalize an Exa result object to a plain dict."""
    def g(name, default=None):
        return getattr(item, name, default)

    return {
        "id": g("id"),
        "title": g("title"),
        "url": g("url"),
        "author": g("author"),
        "published_date": g("published_date"),
        "score": g("score"),
        "highlights": g("highlights") or [],
        "highlight_scores": g("highlight_scores") or [],
        "summary": g("summary"),
        "text": g("text"),
        "image": g("image"),
        "favicon": g("favicon"),
    }


def _content_kwargs(content_mode: str | None) -> dict:
    """Translate `--content` flag into exa-py content-extraction kwargs."""
    if not content_mode or content_mode == "none":
        return {}
    mode = content_mode.lower()
    if mode == "highlights":
        return {"highlights": True}
    if mode == "text":
        return {"text": True}
    if mode == "summary":
        return {"summary": True}
    if mode == "all":
        return {"highlights": True, "text": True, "summary": True}
    return {"highlights": True}


def search(
    query: str,
    max_results: int = 10,
    category: str | None = None,
    content: str | None = "highlights",
    search_type: str = "auto",
    start_published: str | None = None,
    end_published: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict:
    client, err = _load_client()
    if client is None:
        return _graceful_unavailable(err or "Exa unavailable", "search")

    kwargs: dict = {
        "query": query,
        "num_results": max(1, min(max_results, 100)),
        "type": search_type,
    }
    if category:
        kwargs["category"] = category
    if start_published:
        kwargs["start_published_date"] = start_published
    if end_published:
        kwargs["end_published_date"] = end_published
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains

    content_kw = _content_kwargs(content)

    try:
        if content_kw:
            response = client.search_and_contents(**kwargs, **content_kw)
        else:
            response = client.search(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return _graceful_unavailable(f"Exa API error: {exc}", "search")

    results = [_serialize_result(r) for r in getattr(response, "results", [])]
    return {"ok": True, "command": "search", "query": query, "results": results}


def find_similar(
    url: str,
    max_results: int = 10,
    content: str | None = "highlights",
) -> dict:
    client, err = _load_client()
    if client is None:
        return _graceful_unavailable(err or "Exa unavailable", "find-similar")

    kwargs = {"url": url, "num_results": max(1, min(max_results, 100))}
    content_kw = _content_kwargs(content)

    try:
        if content_kw:
            response = client.find_similar_and_contents(**kwargs, **content_kw)
        else:
            response = client.find_similar(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return _graceful_unavailable(f"Exa API error: {exc}", "find-similar")

    results = [_serialize_result(r) for r in getattr(response, "results", [])]
    return {"ok": True, "command": "find-similar", "url": url, "results": results}


def contents(urls: list[str], content: str | None = "highlights") -> dict:
    client, err = _load_client()
    if client is None:
        return _graceful_unavailable(err or "Exa unavailable", "contents")

    content_kw = _content_kwargs(content) or {"highlights": True}
    try:
        response = client.get_contents(urls, **content_kw)
    except Exception as exc:  # noqa: BLE001
        return _graceful_unavailable(f"Exa API error: {exc}", "contents")

    results = [_serialize_result(r) for r in getattr(response, "results", [])]
    return {"ok": True, "command": "contents", "results": results}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exa AI-powered web search with content extraction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="AI-ranked web search")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=10, metavar="N")
    s.add_argument(
        "--category",
        default=None,
        help=(
            "Optional Exa category filter, e.g. 'research paper', 'news', "
            "'company', 'github', 'tweet', 'pdf'."
        ),
    )
    s.add_argument(
        "--content",
        default="highlights",
        choices=["none", "highlights", "text", "summary", "all"],
        help="Content extraction mode (default: highlights).",
    )
    s.add_argument(
        "--type",
        default="auto",
        choices=["auto", "neural", "keyword"],
        help="Exa search type (default: auto).",
    )
    s.add_argument("--start-published", default=None, help="ISO date, e.g. 2024-01-01.")
    s.add_argument("--end-published", default=None, help="ISO date, e.g. 2024-12-31.")
    s.add_argument(
        "--include-domains",
        default=None,
        help="Comma-separated list of domains to include.",
    )
    s.add_argument(
        "--exclude-domains",
        default=None,
        help="Comma-separated list of domains to exclude.",
    )

    fs = sub.add_parser("find-similar", help="Find pages similar to a URL")
    fs.add_argument("url")
    fs.add_argument("--max", type=int, default=10, metavar="N")
    fs.add_argument(
        "--content",
        default="highlights",
        choices=["none", "highlights", "text", "summary", "all"],
    )

    c = sub.add_parser("contents", help="Fetch contents for one or more URLs")
    c.add_argument("urls", nargs="+", help="One or more URLs.")
    c.add_argument(
        "--content",
        default="highlights",
        choices=["none", "highlights", "text", "summary", "all"],
    )

    return parser


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "search":
        out = search(
            args.query,
            max_results=args.max,
            category=args.category,
            content=args.content,
            search_type=args.type,
            start_published=args.start_published,
            end_published=args.end_published,
            include_domains=_split_csv(args.include_domains),
            exclude_domains=_split_csv(args.exclude_domains),
        )
    elif args.command == "find-similar":
        out = find_similar(args.url, max_results=args.max, content=args.content)
    elif args.command == "contents":
        out = contents(args.urls, content=args.content)
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

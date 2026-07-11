#!/usr/bin/env python3
"""CLI helper for the DeepXiv progressive retrieval tool.

Used by the ``research-lit`` skill when the user passes ``— sources: deepxiv``.
This script is a thin adapter around the installed ``deepxiv`` CLI: it
normalizes its output to JSON on stdout so the rest of the skill can merge
results with arXiv / S2 / Exa uniformly.

If the ``deepxiv`` CLI is not installed (or fails), the script prints a JSON
object describing the failure and exits with status 0 so the caller can fall
back gracefully (per the skill's "graceful degradation" rule).

Commands
--------
search          Broad search; returns ranked candidate papers.
paper-brief     One-paragraph TLDR for a single paper (arXiv ID).
paper-head      Title + abstract + section headers for a single paper.
paper-section   Fetch a specific named section (e.g. "Experiments").
trending        Trending recent papers on a topic (passthrough).
web             DeepXiv web-search passthrough.

Examples
--------
python3 skills/research-lit/scripts/deepxiv_fetch.py search "diffusion language models" --max 10
python3 skills/research-lit/scripts/deepxiv_fetch.py paper-brief 2301.07041
python3 skills/research-lit/scripts/deepxiv_fetch.py paper-head 2301.07041
python3 skills/research-lit/scripts/deepxiv_fetch.py paper-section 2301.07041 "Experiments"
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


_DEEPXIV_BIN = "deepxiv"
_TIMEOUT = 120


def _have_cli() -> bool:
    return shutil.which(_DEEPXIV_BIN) is not None


def _graceful_unavailable(reason: str, command: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "reason": reason,
        "results": [],
    }


def _run(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _try_parse_json(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _invoke(subcmd: str, *cli_args: str) -> dict:
    """Invoke `deepxiv <subcmd> ...` and normalize output.

    The DeepXiv CLI's exact flag surface varies by version; we pass arguments
    through verbatim and try to parse stdout as JSON first, falling back to
    raw text under a ``raw`` field. Errors do not raise — they return a
    graceful payload so the calling skill can continue with other sources.
    """
    if not _have_cli():
        return _graceful_unavailable(
            "deepxiv CLI not found on PATH", subcmd
        )

    try:
        code, out, err = _run([_DEEPXIV_BIN, subcmd, *cli_args])
    except subprocess.TimeoutExpired:
        return _graceful_unavailable(
            f"deepxiv {subcmd} timed out after {_TIMEOUT}s", subcmd
        )
    except FileNotFoundError as exc:
        return _graceful_unavailable(str(exc), subcmd)

    if code != 0:
        return {
            "ok": False,
            "command": subcmd,
            "exit_code": code,
            "stderr": err.strip(),
            "stdout": out.strip(),
            "results": [],
        }

    parsed = _try_parse_json(out)
    if parsed is not None:
        if isinstance(parsed, list):
            return {"ok": True, "command": subcmd, "results": parsed}
        if isinstance(parsed, dict):
            payload = {"ok": True, "command": subcmd}
            payload.update(parsed)
            payload.setdefault("results", parsed.get("results") or [])
            return payload

    return {
        "ok": True,
        "command": subcmd,
        "raw": out.strip(),
        "results": [],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Adapter for the DeepXiv progressive paper-retrieval CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search for papers")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=10, metavar="N")

    pb = sub.add_parser("paper-brief", help="One-paragraph TLDR for a paper")
    pb.add_argument("arxiv_id")

    ph = sub.add_parser("paper-head", help="Title + abstract + section headers")
    ph.add_argument("arxiv_id")

    ps = sub.add_parser("paper-section", help="Fetch a named section of a paper")
    ps.add_argument("arxiv_id")
    ps.add_argument("section")

    tr = sub.add_parser("trending", help="Trending recent papers on a topic")
    tr.add_argument("query")
    tr.add_argument("--max", type=int, default=10, metavar="N")

    w = sub.add_parser("web", help="DeepXiv web-search passthrough")
    w.add_argument("query")
    w.add_argument("--max", type=int, default=10, metavar="N")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "search":
        out = _invoke("search", args.query, "--max", str(args.max))
    elif args.command == "paper-brief":
        out = _invoke("paper-brief", args.arxiv_id)
    elif args.command == "paper-head":
        out = _invoke("paper-head", args.arxiv_id)
    elif args.command == "paper-section":
        out = _invoke("paper-section", args.arxiv_id, args.section)
    elif args.command == "trending":
        out = _invoke("trending", args.query, "--max", str(args.max))
    elif args.command == "web":
        out = _invoke("web", args.query, "--max", str(args.max))
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Launch one of Mechanist's MCP servers from any working directory."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path


SERVERS = {
    "llm-chat": "llm-chat",
    "mechanic-db": "mechanic-db",
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SERVERS:
        valid = ", ".join(sorted(SERVERS))
        print(f"usage: {Path(sys.argv[0]).name} <{valid}>", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    server_dir = root / SERVERS[sys.argv[1]]
    requirements = server_dir / "requirements.txt"
    server = server_dir / "server.py"

    if importlib.util.find_spec("httpx") is not None:
        command = [sys.executable, str(server)]
    else:
        uv = shutil.which("uv")
        if uv is None:
            print(
                "Mechanist MCP startup failed: Python package `httpx` is not "
                "installed and `uv` is not on PATH. Install uv from "
                "https://docs.astral.sh/uv/ and restart the host.",
                file=sys.stderr,
            )
            return 127
        command = [
            uv,
            "run",
            "--with-requirements",
            str(requirements),
            str(server),
        ]

    env = os.environ.copy()
    env.setdefault(
        "UV_CACHE_DIR", str(Path(tempfile.gettempdir()) / "mechanist-uv-cache")
    )
    os.chdir(root.parent)
    os.execvpe(command[0], command, env)
    return 127  # pragma: no cover - exec only returns on an OS-level failure


if __name__ == "__main__":
    raise SystemExit(main())

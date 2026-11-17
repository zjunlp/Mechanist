#!/usr/bin/env python3
"""
Programmatic usage example for the ICA Lens FastAPI explorer.

This script demonstrates actual Python API usage from the repository by:
1. Importing `create_app` from `server.app`
2. Building the FastAPI application object
3. Inspecting registered routes
4. Fetching the generated OpenAPI schema using FastAPI's TestClient

Run from the repository root after dependencies are installed:

    uv sync
    uv run python scripts/explorer_app_usage.py

The script does not require downloaded artifacts because it only inspects app
construction and documentation surfaces. If application startup depends on
local settings in your checkout, the raised exception will explain what is
missing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from fastapi.testclient import TestClient
except ImportError as exc:
    raise SystemExit(
        "fastapi is required to run this example. "
        "Install project dependencies with `uv sync` first."
    ) from exc


def ensure_repo_root_on_path() -> Path:
    """
    Ensure imports work when this script is executed from the repository root.

    Returns:
        The resolved repository root path.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def build_app():
    """
    Import and construct the ICA Lens FastAPI application.

    Returns:
        A FastAPI application object produced by `server.app.create_app()`.

    Raises:
        RuntimeError: If the server module cannot be imported or app creation fails.
    """
    try:
        from server.app import create_app
    except Exception as exc:
        raise RuntimeError(f"Failed to import `create_app` from `server.app`: {exc}") from exc

    try:
        return create_app()
    except Exception as exc:
        raise RuntimeError(f"Failed to create FastAPI app with `create_app()`: {exc}") from exc


def summarize_routes(app: Any) -> list[dict[str, Any]]:
    """
    Collect a compact summary of registered routes.

    Args:
        app: FastAPI application instance.

    Returns:
        A list of route summaries containing path and methods.
    """
    route_summaries: list[dict[str, Any]] = []
    for route in getattr(app, "routes", []):
        methods = sorted(getattr(route, "methods", []) or [])
        path = getattr(route, "path", "<unknown>")
        name = getattr(route, "name", "<unnamed>")
        route_summaries.append(
            {
                "name": name,
                "path": path,
                "methods": methods,
            }
        )
    return route_summaries


def fetch_openapi_schema(app: Any) -> dict[str, Any]:
    """
    Request the generated OpenAPI schema from the FastAPI app.

    Args:
        app: FastAPI application instance.

    Returns:
        Parsed OpenAPI schema as a dictionary.

    Raises:
        RuntimeError: If the OpenAPI endpoint is unavailable.
    """
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAPI endpoint returned {response.status_code}: {response.text}"
            )
        return response.json()


def main() -> int:
    """
    Run the programmatic FastAPI usage example.

    Returns:
        Exit code integer.
    """
    repo_root = ensure_repo_root_on_path()
    print(f"Repository root: {repo_root}")

    app = build_app()
    print("FastAPI app created successfully.")

    routes = summarize_routes(app)
    print(f"Registered routes: {len(routes)}")
    for route in routes[:15]:
        methods = ",".join(route["methods"])
        print(f"- {methods:20s} {route['path']} ({route['name']})")

    schema = fetch_openapi_schema(app)
    info = schema.get("info", {})
    paths = schema.get("paths", {})
    print("\nOpenAPI info:")
    print(json.dumps(info, indent=2, sort_keys=True))

    print(f"\nOpenAPI path count: {len(paths)}")
    sample_paths = list(paths.keys())[:10]
    for path in sample_paths:
        print(f"- {path}")

    print("\nExample completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

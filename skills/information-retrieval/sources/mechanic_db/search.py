#!/usr/bin/env python3
"""Retrieve domain papers from the Mechanic DB search service.

Uses MECHANIC_DB_API_KEY (optional) and MECHANIC_DB_BASE_URL. Submit and polling
share one timeout budget. Full results go to a caller-selected file; stdout
contains a small JSON summary. No background service is required.
"""

import argparse
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

TERMINAL_OK = {"succeeded", "completed", "done", "finished"}
TERMINAL_ERR = {"failed", "error", "canceled", "stopped"}


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError("Search exceeded the requested timeout.")
    return seconds


def pause(seconds, deadline):
    if seconds >= remaining(deadline):
        raise TimeoutError("Search cannot retry within the remaining timeout.")
    time.sleep(seconds)


def retry_after(response, default):
    header = response.headers.get("retry-after", "").strip()
    if header.isdigit():
        return max(1, int(header))
    try:
        value = response.json().get("detail", {}).get("retry_after_seconds")
    except (ValueError, AttributeError, TypeError):
        value = None
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return max(1, value)
    return default


def error_detail(response):
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if detail is None:
        return f"HTTP {response.status_code}"
    return f"HTTP {response.status_code}: {json.dumps(detail, ensure_ascii=True)[:500]}"


def submit(client, base_url, headers, payload, deadline):
    while True:
        response = client.post(base_url + "/search", json=payload, headers=headers,
                               timeout=min(60, remaining(deadline)))
        if response.status_code == 202:
            try:
                job_id = response.json()["job_id"]
            except (ValueError, KeyError, TypeError):
                raise RuntimeError("Search service returned no job identifier.") from None
            if not isinstance(job_id, str) or not job_id:
                raise RuntimeError("Search service returned an invalid job identifier.")
            return job_id
        if response.status_code == 401:
            raise RuntimeError("Search key was rejected. Fix MECHANIC_DB_API_KEY or unset it for anonymous access.")
        if response.status_code == 429:
            pause(retry_after(response, 30), deadline)
            continue
        raise RuntimeError("Search submission failed: " + error_detail(response))


def poll(client, base_url, headers, job_id, deadline, interval):
    while True:
        response = client.get(base_url + "/jobs/" + quote(job_id, safe=""), headers=headers,
                              timeout=min(60, remaining(deadline)))
        if response.status_code == 429:
            pause(retry_after(response, interval), deadline)
            continue
        if response.status_code != 200:
            raise RuntimeError("Search polling failed: " + error_detail(response))
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Search service returned an invalid job response.")
        status = data.get("status", "")
        if status in TERMINAL_OK:
            return data
        if status in TERMINAL_ERR:
            raise RuntimeError(f"Search job {status}: {str(data.get('error', 'no details'))[:500]}")
        pause(interval, deadline)


def search(*, query=None, decomposed=None, output, temporal_mode="default",
           top_k=300, timeout=1200, poll_interval=10,
           recent_alpha=None, recent_min_year=None):
    """Execute retrieval; return a compact summary only after writing results."""
    if (query is None) == (decomposed is None):
        raise ValueError("Provide exactly one of query and decomposed.")
    if query is not None and (not isinstance(query, str) or not query.strip()):
        raise ValueError("Query must be nonempty text.")
    if decomposed is not None and (not isinstance(decomposed, dict) or not decomposed):
        raise ValueError("Decomposed query must be a nonempty JSON object.")
    if temporal_mode not in {"default", "recent", "history"}:
        raise ValueError("Invalid temporal mode.")
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    for name, value in (("timeout", timeout), ("poll_interval", poll_interval)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite number.")
    if recent_alpha is not None and not 0 <= recent_alpha <= 1:
        raise ValueError("recent_alpha must be between zero and one.")
    if recent_min_year is not None and (type(recent_min_year) is not int or recent_min_year <= 0):
        raise ValueError("recent_min_year must be a positive integer.")
    if not output:
        raise ValueError("Choose an output file for the full retrieval result.")
    output = Path(output).resolve()
    payload = {"top_k": top_k, "temporal_mode": temporal_mode}
    if decomposed is not None:
        payload.update(decomposed=decomposed, query=decomposed.get("original_query") or "")
    else:
        payload["query"] = query
    if recent_alpha is not None:
        payload["recent_alpha"] = recent_alpha
    if recent_min_year is not None:
        payload["recent_min_year"] = recent_min_year
    key = os.environ.get("MECHANIC_DB_API_KEY", "").strip()
    base_url = (os.environ.get("MECHANIC_DB_BASE_URL") or "http://mechanist.openkg.cn").rstrip("/")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("Install this backend's requirements.txt before retrieval.") from exc
    deadline = time.monotonic() + timeout
    # Keep the service's existing direct-connection behavior independent of
    # ambient proxy variables. Its URL remains explicitly configurable.
    with httpx.Client(trust_env=False) as client:
        job_id = submit(client, base_url, headers, payload, deadline)
        result = poll(client, base_url, headers, job_id, deadline, poll_interval)
    if not result.get("papers") and isinstance(result.get("result"), dict):
        result["papers"] = result["result"].get("papers", [])
    result.setdefault("papers", [])
    if not isinstance(result["papers"], list):
        raise RuntimeError("Search response contains an invalid paper list.")
    result.update(skipped=False, tier="registered" if key else "anonymous")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"count": len(result["papers"]), "output": str(output),
            "tier": result["tier"], "skipped": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="Plain English search query.")
    mode.add_argument("--decomposed-file", help="UTF-8 JSON query object, or - for stdin.")
    parser.add_argument("--output", required=True, help="Destination for full result JSON.")
    parser.add_argument("--temporal-mode", choices=["default", "recent", "history"], default="default")
    parser.add_argument("--top-k", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--poll-interval", type=float, default=10)
    parser.add_argument("--recent-alpha", type=float)
    parser.add_argument("--recent-min-year", type=int)
    args = parser.parse_args(argv)
    try:
        decomposed = None
        if args.decomposed_file:
            raw = sys.stdin.read() if args.decomposed_file == "-" else Path(args.decomposed_file).read_text(encoding="utf-8-sig")
            decomposed = json.loads(raw)
            if not isinstance(decomposed, dict) or not decomposed:
                raise ValueError("Decomposed file must contain a nonempty JSON object.")
        result = search(query=args.query, decomposed=decomposed, output=args.output,
                        temporal_mode=args.temporal_mode, top_k=args.top_k,
                        timeout=args.timeout, poll_interval=args.poll_interval,
                        recent_alpha=args.recent_alpha, recent_min_year=args.recent_min_year)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as exc:
        error = str(exc)
        key = os.environ.get("MECHANIC_DB_API_KEY", "").strip()
        if key:
            error = error.replace(key, "[redacted]")
        print(json.dumps({"error": error}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

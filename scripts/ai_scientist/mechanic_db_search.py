#!/usr/bin/env python3
"""Standalone mechanic-db search: submit a flat (undecomposed) query.

Writes the full server response JSON to mechanic_db_result.json in the
current directory and prints a compact {count, output, skipped, tier}
summary on stdout.
"""

import argparse
import json
import os
import sys
import time

import httpx

# Transport/auth config, both from the environment. p1_env.sh exports them
# from ideation_config.json; there is no built-in key.
API_KEY = os.environ.get("MECHANIC_DB_API_KEY", "")
BASE_URL = os.environ.get("MECHANIC_DB_BASE_URL", "http://localhost:9001")

OUTPUT_PATH = os.path.abspath("mechanic_db_result.json")
TEMPORAL_MODE = "default"
TIMEOUT_S = 1200
POLL_INTERVAL_S = 10

TERMINAL_OK = {"succeeded", "completed", "done", "finished"}
TERMINAL_ERR = {"failed", "error", "canceled", "stopped"}
CONCURRENCY_BACKOFF_S = 30


def describe_error(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except Exception:
        detail = None
    if detail is None:
        detail = resp.text[:300]
    if not isinstance(detail, str):
        detail = json.dumps(detail, ensure_ascii=False)
    return f"HTTP {resp.status_code}: {detail}"


def retry_after_seconds(resp: httpx.Response, default: int) -> int:
    header = resp.headers.get("retry-after", "").strip()
    if header.isdigit():
        return max(1, int(header))
    try:
        seconds = resp.json().get("detail", {}).get("retry_after_seconds")
    except Exception:
        seconds = None
    return max(1, int(seconds)) if isinstance(seconds, (int, float)) else default


def submit(client: httpx.Client, headers: dict, payload: dict, deadline: float) -> str:
    attempt = 0
    while True:
        attempt += 1
        resp = client.post(f"{BASE_URL}/search", json=payload, headers=headers, timeout=60)

        if resp.status_code == 202:
            job_id = resp.json().get("job_id")
            if not job_id:
                raise RuntimeError(f"malformed submit response: {resp.text[:500]}")
            return job_id

        if resp.status_code == 401:
            raise RuntimeError(
                "mechanic-db rejected the API key (invalid or revoked). "
                + describe_error(resp)
            )

        if resp.status_code == 429:
            wait = retry_after_seconds(resp, CONCURRENCY_BACKOFF_S)
            if time.time() + wait >= deadline:
                raise RuntimeError(
                    f"mechanic-db kept refusing the submission until the "
                    f"call's {int(deadline - time.time())}s of remaining "
                    f"budget ran out after {attempt} attempts: "
                    f"{describe_error(resp)}"
                )
            print(
                f"submit refused (attempt {attempt}), retrying in {wait}s: "
                f"{describe_error(resp)}",
                file=sys.stderr,
            )
            time.sleep(wait)
            continue

        raise RuntimeError(f"mechanic-db submit failed: {describe_error(resp)}")


def poll(client: httpx.Client, headers: dict, job_id: str, deadline: float) -> dict:
    while time.time() < deadline:
        resp = client.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=60)

        if resp.status_code == 429:
            wait = retry_after_seconds(resp, POLL_INTERVAL_S)
            print(f"[{job_id}] poll throttled, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            raise RuntimeError(f"polling job {job_id} failed: {describe_error(resp)}")

        data = resp.json()
        status = data.get("status", "")
        print(f"[{job_id}] status={status}", file=sys.stderr)
        if status in TERMINAL_OK:
            return data
        if status in TERMINAL_ERR:
            raise RuntimeError(
                f"job {job_id} ended as {status}: {data.get('error', data)}"
            )
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"polling exceeded the call's budget for job {job_id}")


def run_search(query: str, top_k: int) -> dict:
    payload = {
        "query": query,
        "top_k": top_k,
        "temporal_mode": TEMPORAL_MODE,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    deadline = time.time() + TIMEOUT_S

    with httpx.Client(trust_env=False) as client:
        job_id = submit(client, headers, payload, deadline)
        print(f"submitted job_id={job_id}", file=sys.stderr)
        result = poll(client, headers, job_id, deadline)

    if not result.get("papers") and isinstance(result.get("result"), dict):
        result["papers"] = result["result"].get("papers", [])
    result.setdefault("papers", [])
    result["skipped"] = False
    result["tier"] = "registered"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "skipped": False,
        "tier": "registered",
        "count": len(result["papers"]),
        "output": OUTPUT_PATH,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit an undecomposed query to mechanic-db and write the result JSON."
    )
    parser.add_argument("query", help="Flat free-form English query (not decomposed).")
    parser.add_argument("--top-k", type=int, default=300, help="Top-K papers to return (default 300).")
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("query must be a non-empty string")

    try:
        summary = run_search(query=args.query, top_k=args.top_k)
    except Exception as e:
        print(f"mechanic-db search failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

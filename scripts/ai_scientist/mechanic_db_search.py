#!/usr/bin/env python3
r"""Standalone mechanic-db search: submit a flat (undecomposed) query.

Writes the full server response JSON to mechanic_db_result.json in the
current directory and prints a compact
{count, db_counts, output, skipped, tier} summary on stdout.

run_search() 参数表
===================

| 参数 | 类型 | 默认 | 含义 |
|------|------|------|------|
| `query`          | str             | 必填 | 一句话自然语言 query，英文。拆解由服务端 LLM 负责 |
| `top_k`          | int             | 300  | 检索总预算，按实际检索的库均分 |
| `target_dbs`     | list[str]\|None | 两个库 | 检索哪些库的开关，None 则由服务端 LLM 决定 |
| `top_k_interp`   | int\|None       | None | interp_db 单独的 top-K，仅在决定检索 interp_db 时生效 |
| `top_k_sciatlas` | int\|None       | None | sciatlas_db 单独的 top-K，仅在决定检索 sciatlas_db 时生效 |

`target_dbs`
----------------------------------
不传入该参数时，检索意图拆成几路、是否跨库由服务端 LLM 判断。
传入该参数时，可控制检索的库和是否跨库。传入的合法值如下表所示：

| 值 | 行为 |
|----|------|
| `None` / 省略                      | 服务端 LLM 自行决定 |
| `["interp_db", "sciatlas_db"]`     | 同时查两个库                 |
| `["interp_db"]`                    | 只查 interp_db              |
| `["sciatlas_db"]`                  | 只查 sciatlas_db            |

`top_k` `top_k_interp` `top_k_sciatlas`
----------------------------------
`top_k` 是总数，按实际检索的库均分；单库参数从中扣除，余额归另一个库：

| 传入 | interp_db | sciatlas_db |
|------|-----------|-------------|
| `top_k=300`                             | 150 | 150 |
| `top_k=300, target_dbs=["interp_db"]`   | 300 |  —  |
| `top_k=300, top_k_interp=50`            |  50 | 250 |

两个单库参数都传时 `top_k` 失效。

Per-paper database labels
=========================
The service strips per-paper provenance before returning (see
search_mixed.schema.simplify_paper server side), so the papers arrive
unlabelled. `label_papers_by_db` recovers the label and writes it back onto
every paper as `db`, which is what lets a caller take "the top N of each
database" downstream. See that function for why the recovery is exact.
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

KNOWN_DBS = ("interp_db", "sciatlas_db")
# Both databases on, which is what the ideation pipeline wants: an interp
# half and an all-discipline half, each ranked and truncated separately
# downstream. Pass --target-dbs auto to hand the routing back to the server.
DEFAULT_TARGET_DBS = list(KNOWN_DBS)

# Fields only interp_db populates. search_sciatlas.pipeline states it outright
# ("mech-interp-specific fields ... are always None on cross-domain results"),
# so a paper carrying any of them came from interp_db.
INTERP_ONLY_FIELDS = ("research_question", "core_contribution", "conclusion")


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


# ---------------------------------------------------------------------------
# Per-paper database labels
# ---------------------------------------------------------------------------
def _looks_interp(paper: dict) -> bool:
    return any(paper.get(field) for field in INTERP_ONLY_FIELDS)


def label_papers_by_db(result: dict) -> dict:
    """Write a `db` field onto every paper in `result["papers"]`.

    The response carries no provenance, so the label is reconstructed from two
    guarantees the server gives:

      1. `search_mixed.schema.fuse_stage` groups the fused list by ranker in
         `sub_queries` order, so each database's papers form ONE CONTIGUOUS RUN.
      2. sciatlas_db never populates research_question / core_contribution /
         conclusion, so a paper carrying any of them is certainly interp_db.

    (1) + (2) put the boundary between the two runs exactly at the edge of the
    distilled-field region: if interp_db came first, the run ends after the last
    paper carrying those fields; if it came second, it starts at the first one.

    Fallbacks, in order: the per-database top-K the server echoes back in
    `meta.params` (used when no paper carries the distilled fields at all), then
    the per-paper signal on its own.

    Returns the count per database, for logging.
    """
    papers = result.get("papers") or []
    block = result.get("result") if isinstance(result.get("result"), dict) else {}

    dbs: list[str] = []
    for sub_query in ((block.get("query") or {}).get("sub_queries") or []):
        db = sub_query.get("db") or "sciatlas_db"
        if db not in dbs:
            dbs.append(db)

    if len(dbs) == 1:
        for paper in papers:
            paper["db"] = dbs[0]
    elif len(dbs) == 2:
        marks = [i for i, paper in enumerate(papers) if _looks_interp(paper)]
        if marks:
            # Last mark closes an interp-first run; first mark opens an
            # interp-second run.
            boundary = marks[-1] + 1 if dbs[0] == "interp_db" else marks[0]
        else:
            params = (block.get("meta") or {}).get("params") or {}
            key = "top_k_interp" if dbs[0] == "interp_db" else "top_k_sciatlas"
            boundary = int(params.get(key) or 0)
        boundary = max(0, min(boundary, len(papers)))
        for i, paper in enumerate(papers):
            paper["db"] = dbs[0] if i < boundary else dbs[1]
    else:
        # No routing metadata to lean on — the per-paper signal is all there is.
        for paper in papers:
            paper["db"] = "interp_db" if _looks_interp(paper) else "sciatlas_db"

    counts: dict[str, int] = {}
    for paper in papers:
        counts[paper["db"]] = counts.get(paper["db"], 0) + 1
    return counts


def run_search(query: str, top_k: int, target_dbs=None,
               top_k_interp=None, top_k_sciatlas=None) -> dict:
    payload = {
        "query": query,
        "top_k": top_k,
        "temporal_mode": TEMPORAL_MODE,
    }
    # Send only what was actually asked for. An absent key means "server
    # default", which for target_dbs is "let the splitter decide".
    if target_dbs:
        payload["target_dbs"] = list(target_dbs)
    if top_k_interp is not None:
        payload["top_k_interp"] = top_k_interp
    if top_k_sciatlas is not None:
        payload["top_k_sciatlas"] = top_k_sciatlas

    headers = {"Authorization": f"Bearer {API_KEY}"}
    deadline = time.time() + TIMEOUT_S

    with httpx.Client(trust_env=False) as client:
        job_id = submit(client, headers, payload, deadline)
        print(f"submitted job_id={job_id}", file=sys.stderr)
        result = poll(client, headers, job_id, deadline)

    if not result.get("papers") and isinstance(result.get("result"), dict):
        result["papers"] = result["result"].get("papers", [])
    result.setdefault("papers", [])
    counts = label_papers_by_db(result)
    result["db_counts"] = counts
    result["skipped"] = False
    result["tier"] = "registered"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"papers per database: {counts}", file=sys.stderr)

    return {
        "skipped": False,
        "tier": "registered",
        "count": len(result["papers"]),
        "db_counts": counts,
        "output": OUTPUT_PATH,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit an undecomposed query to mechanic-db and write the result JSON."
    )
    parser.add_argument("query", help="Flat free-form English query (not decomposed).")
    parser.add_argument(
        "--top-k", type=int, default=300, metavar="N",
        help="TOTAL retrieval budget, split across the databases searched — not "
             "the number of papers returned. Default 300: 150 per database when "
             "both are searched, 300 when only one is.")
    parser.add_argument(
        "--target-dbs", nargs="+", choices=["interp_db", "sciatlas_db", "auto"],
        default=DEFAULT_TARGET_DBS, metavar="DB",
        help="Databases to search, default both (a database the splitter would "
             "have skipped gets a sub-query built from the raw query). Pass one "
             "to force a single-database search, or 'auto' to let the server's "
             "splitter decide, which is also what decides whether the search is "
             "cross-domain.")
    parser.add_argument(
        "--top-k-interp", type=int, default=None, metavar="N",
        help="Top-K for interp_db specifically. Spent from the --top-k budget, "
             "with the remainder going to the other database: --top-k 300 "
             "--top-k-interp 50 leaves sciatlas_db 250. Values above 1000 "
             "cannot be filled (the candidate pool is capped there).")
    parser.add_argument(
        "--top-k-sciatlas", type=int, default=None, metavar="N",
        help="Top-K for sciatlas_db specifically. Same budget rule as "
             "--top-k-interp.")
    args = parser.parse_args()

    if not args.query.strip():
        parser.error("query must be a non-empty string")

    target_dbs = None if "auto" in args.target_dbs else args.target_dbs

    try:
        summary = run_search(query=args.query, top_k=args.top_k,
                             target_dbs=target_dbs,
                             top_k_interp=args.top_k_interp,
                             top_k_sciatlas=args.top_k_sciatlas)
    except Exception as e:
        print(f"mechanic-db search failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

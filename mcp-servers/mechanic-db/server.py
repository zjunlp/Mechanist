#!/usr/bin/env python3
"""Mechanic-DB Search MCP Server — cloud paper-retrieval bridge.

Wraps the mechanic_database cloud SEARCH service as a single MCP tool,
`search_papers`. The configured API key reaches this process via the plugin
manifest's mcpServers env mapping (`${MECHANIC_DB_API_KEY}` read from the
environment that launched Claude Code); this is the only channel through which
a plugin-configured secret reliably arrives, so the retrieval call lives here
rather than in a Bash-invoked standalone script.

Environment Variables:
    MECHANIC_DB_API_KEY   - cloud SEARCH key (sk_...). Optional; see below.
    MECHANIC_DB_BASE_URL  - service base URL (default: http://mechanist.openkg.cn).
    MECHANIC_DB_SERVER_NAME - MCP server name (default: mechanic-db).

Contract:
  * The tool writes the FULL server response JSON to the caller-supplied
    `output` path (so 300-paper payloads stay on disk, out of the model's
    context) and returns only a compact {count, output, skipped, tier} summary.
  * The API key is OPTIONAL. Without one the service still answers, on an
    anonymous per-IP tier with much lower search limits (2/min, 20/day vs the
    registered 20/min, 1000/day). So an unset key no longer means "skip
    mechanic-db"; it means "fewer searches per day". `skipped` stays in the
    summary for callers that branch on it, and is now always false.
  * A *wrong* key is a hard 401 rather than a silent demotion, so a typo'd key
    is reported as an error instead of quietly running at 2 searches/minute.

Server-side limits this client has to live with:
  * A job is killed if it has not finished within 15 minutes of *submission*
    (queue wait + run time together). Typical runtime is 5-7 minutes.
  * One in-flight job per caller (the deployment runs one worker), so a second
    concurrent submission is refused with 429 until the first finishes.
  * Polling is metered on its own, far looser counter (120/min, 30000/day, the
    same for both tiers), so the default 10s poll interval is never the
    binding constraint — submissions are.
"""

import json
import os
import sys
import tempfile
import time

import httpx

# Force unbuffered binary stdio for the JSON-RPC framing below.
sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", buffering=0)
sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", buffering=0)

API_KEY = (os.environ.get("MECHANIC_DB_API_KEY") or "").strip()
BASE_URL = (os.environ.get("MECHANIC_DB_BASE_URL") or "http://mechanist.openkg.cn").rstrip("/")
SERVER_NAME = os.environ.get("MECHANIC_DB_SERVER_NAME", "mechanic-db")

TERMINAL_OK = {"succeeded", "completed", "done", "finished"}
# `canceled` is what the service reports when a job hit the 15-minute deadline
# while still queued; `stopped` is RQ's manual-stop state. Both are terminal,
# and leaving them out is not a cosmetic omission — an unrecognised status just
# keeps polling, so a job the server killed at 15 minutes would be polled until
# this client's own timeout expired and then be blamed on a timeout instead of
# reported with the reason the server already gave us.
TERMINAL_ERR = {"failed", "error", "canceled", "stopped"}

# A submission refused with 429 is retried rather than surfaced: on the
# anonymous tier two calls in one minute is enough to trip the search limit,
# and with a single worker any second concurrent job is refused until the
# first finishes. Both clear on their own if we wait, so the retry loop is
# bounded by the call's own `timeout` budget rather than by an attempt count —
# an attempt cap would have to be guessed against how long the job in front
# takes, and guessing low turns "wait your turn" into a spurious failure.
# Every retry sleeps at least a second and re-checks the budget, so the loop
# always terminates.
#
# Used when a 429 carries no Retry-After, which is the concurrency refusal —
# what we are waiting for there is a 5-7 minute job, so retrying faster than
# this only burns quota.
CONCURRENCY_BACKOFF_S = 30

DEBUG_LOG = os.path.join(tempfile.gettempdir(), f"{SERVER_NAME}-mcp-debug.log")


def debug_log(msg):
    try:
        import datetime
        with open(DEBUG_LOG, "a") as f:
            f.write(f"{datetime.datetime.now()}: {msg}\n")
            f.flush()
    except Exception:
        pass


debug_log(f"=== {SERVER_NAME} MCP Server Starting ===")
debug_log(f"BASE_URL: {BASE_URL}")
debug_log(f"API_KEY set: {bool(API_KEY)}")

_use_ndjson = False


def send_response(response):
    json_bytes = json.dumps(response, separators=(",", ":")).encode("utf-8")
    if _use_ndjson:
        output = json_bytes + b"\n"
    else:
        header = f"Content-Length: {len(json_bytes)}\r\n\r\n".encode("utf-8")
        output = header + json_bytes
    sys.stdout.write(output)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Core retrieval logic: build_payload + poll
# ---------------------------------------------------------------------------

def build_payload(args: dict) -> dict:
    payload = {
        "top_k": args.get("top_k", 300),
        "temporal_mode": args.get("temporal_mode", "default"),
    }
    if args.get("recent_alpha") is not None:
        payload["recent_alpha"] = args["recent_alpha"]
    if args.get("recent_min_year") is not None:
        payload["recent_min_year"] = args["recent_min_year"]

    decomposed = args.get("decomposed")
    if decomposed is not None:
        payload["decomposed"] = decomposed
        payload["query"] = decomposed.get("original_query") or args.get("query") or ""
    else:
        payload["query"] = args.get("query", "")
    return payload


def describe_error(resp: httpx.Response) -> str:
    """Human-readable one-liner for a failed response.

    The service puts a structured object in `detail` (error code, tier, the
    limits that were hit, and for anonymous callers a hint about registering).
    raise_for_status() throws all of that away and leaves the caller staring at
    "Client error '429 Too Many Requests'", which says nothing about whether to
    wait a minute or stop trying.
    """
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
    """How long the service asked us to wait, or `default` if it did not."""
    header = resp.headers.get("retry-after", "").strip()
    if header.isdigit():
        return max(1, int(header))
    try:
        seconds = resp.json().get("detail", {}).get("retry_after_seconds")
    except Exception:
        seconds = None
    return max(1, int(seconds)) if isinstance(seconds, (int, float)) else default


def log_quota(resp: httpx.Response, label: str) -> None:
    """Record the X-RateLimit-* headers, which name the counter they describe."""
    scope = resp.headers.get("x-ratelimit-scope")
    if scope:
        debug_log(f"{label} quota[{scope}]: "
                  f"{resp.headers.get('x-ratelimit-remaining-minute')}/"
                  f"{resp.headers.get('x-ratelimit-limit-minute')} per min, "
                  f"{resp.headers.get('x-ratelimit-remaining-day')}/"
                  f"{resp.headers.get('x-ratelimit-limit-day')} per day")


def submit(client: httpx.Client, headers: dict, payload: dict, deadline: float) -> str:
    """Submit a search, retrying past the two refusals that clear by waiting."""
    attempt = 0
    while True:
        attempt += 1
        resp = client.post(f"{BASE_URL}/search", json=payload, headers=headers, timeout=60)
        log_quota(resp, "submit")

        if resp.status_code == 202:
            job_id = resp.json().get("job_id")
            if not job_id:
                raise RuntimeError(f"malformed submit response: {resp.text[:500]}")
            return job_id

        if resp.status_code == 401:
            # Only a bad key can produce this now — no key at all is a valid
            # anonymous call — so say the thing that actually fixes it.
            raise RuntimeError(
                "mechanic-db rejected the API key (invalid or revoked). Fix "
                "MECHANIC_DB_API_KEY, or unset it to use the anonymous tier. "
                + describe_error(resp))

        if resp.status_code == 429:
            wait = retry_after_seconds(resp, CONCURRENCY_BACKOFF_S)
            if time.time() + wait >= deadline:
                raise RuntimeError(
                    f"mechanic-db kept refusing the submission until the "
                    f"call's {int(deadline - time.time())}s of remaining "
                    f"budget ran out after {attempt} attempts: "
                    f"{describe_error(resp)}")
            debug_log(f"submit refused (attempt {attempt}), retrying in {wait}s: "
                      f"{describe_error(resp)}")
            time.sleep(wait)
            continue

        raise RuntimeError(f"mechanic-db submit failed: {describe_error(resp)}")


def poll(client: httpx.Client, headers: dict, job_id: str, deadline: float, interval_s: int) -> dict:
    while time.time() < deadline:
        resp = client.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=60)

        if resp.status_code == 429:
            # The status counter, not the search one. Wait it out rather than
            # failing a job that is very likely still running.
            wait = retry_after_seconds(resp, interval_s)
            debug_log(f"[{job_id}] poll throttled, waiting {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            log_quota(resp, "poll")
            raise RuntimeError(f"polling job {job_id} failed: {describe_error(resp)}")

        data = resp.json()
        status = data.get("status", "")
        debug_log(f"[{job_id}] status={status}")
        if status in TERMINAL_OK:
            return data
        if status in TERMINAL_ERR:
            # `error` carries the service's own reason, including the deadline
            # message when the job was killed for exceeding 15 minutes.
            raise RuntimeError(
                f"job {job_id} ended as {status}: {data.get('error', data)}")
        time.sleep(interval_s)
    raise TimeoutError(f"polling exceeded the call's budget for job {job_id}")


def write_output(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_search(args: dict) -> dict:
    """Execute one SEARCH job. Returns a compact summary dict for the caller.

    Raises ValueError for bad arguments; returns {"error": ...} dicts for
    HTTP/polling failures so the tool layer can surface them as isError.
    """
    output = args.get("output")
    if not output:
        raise ValueError("`output` (absolute path to write the result JSON) is required.")
    if not args.get("decomposed") and not args.get("query"):
        raise ValueError("Provide either `decomposed` (object) or `query` (string).")

    # No key is no longer a reason to skip: the service answers anonymous
    # callers too, just on a much smaller daily search allowance.
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    tier = "registered" if API_KEY else "anonymous"
    if not API_KEY:
        debug_log("no API_KEY; calling the anonymous tier (2/min, 20/day)")

    timeout_s = args.get("timeout", 1200)
    interval_s = args.get("poll_interval", 10)

    # trust_env=False: ignore ambient proxy env vars (http_proxy / all_proxy).
    # The SEARCH backend is reached at the fixed BASE_URL, which should never
    # be tunneled through a personal SOCKS/HTTP proxy. Honoring a
    # `all_proxy=socks5://...` here would also force an httpx[socks]/socksio
    # dependency and crash the connect with ImportError before any request is
    # sent — the exact failure that made earlier calls hang with no response.
    # One budget for the whole call, shared by the submit retries and the
    # polling that follows: waiting out a 429 has to come out of the same
    # `timeout` the caller asked for, not extend it.
    deadline = time.time() + timeout_s
    with httpx.Client(trust_env=False) as client:
        job_id = submit(client, headers, build_payload(args), deadline)
        debug_log(f"submitted job_id={job_id} ({tier} tier)")
        result = poll(client, headers, job_id, deadline, interval_s)

    # Cloud service nests papers under result["result"]["papers"]; hoist them
    # so downstream callers can rely on result["papers"].
    if not result.get("papers") and isinstance(result.get("result"), dict):
        result["papers"] = result["result"].get("papers", [])
    result.setdefault("papers", [])
    result["skipped"] = False
    result["tier"] = tier
    write_output(output, result)
    return {"skipped": False, "tier": tier,
            "count": len(result["papers"]), "output": output}


# ---------------------------------------------------------------------------
# JSON-RPC scaffolding (mirrors mcp-servers/llm-chat/server.py)
# ---------------------------------------------------------------------------

TOOL_SCHEMA = {
    "name": "search_papers",
    "description": (
        "Retrieve papers from the mechanic_database cloud SEARCH service. "
        "Pass an Agent-built `decomposed` query object (preferred) or a flat "
        "`query` string. The full result JSON is written to `output`; the tool "
        "returns only a {count, output, skipped, tier} summary, so read the "
        "papers[] list back from the output file. One call typically takes 5-7 "
        "minutes; the service kills any job that has not finished within 15 "
        "minutes of submission, so a call either returns within that or fails. "
        "Searches are rate limited (20/min, 1000/day with an API key "
        "configured; 2/min, 20/day without one, shared with everything else on "
        "this IP) and only one search may run at a time, so avoid issuing "
        "several in quick succession."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "output": {
                "type": "string",
                "description": "ABSOLUTE path to write the full result JSON to. Required (the MCP "
                               "server's cwd is not the project dir, so a relative path will not "
                               "land where the caller expects).",
            },
            "decomposed": {
                "type": "object",
                "description": "Agent-built decomposed query object (flat ParsedQuery shape). "
                               "Preferred over `query`. Mutually exclusive with `query`.",
            },
            "query": {
                "type": "string",
                "description": "Flat free-form English query (fallback when context is too thin "
                               "to write a decomposition).",
            },
            "temporal_mode": {
                "type": "string",
                "enum": ["default", "recent", "history"],
                "description": "Temporal bias. default=no boost; recent=frontier (α=0.08, year>=2020); history.",
            },
            "recent_alpha": {"type": "number", "description": "Override recency α (recent mode only, 0-1)."},
            "recent_min_year": {"type": "integer", "description": "Override year_min floor (recent mode only)."},
            "top_k": {"type": "integer", "description": "Top-K papers to return (default 300)."},
            "timeout": {"type": "integer",
                        "description": "Whole-call budget in seconds, covering both the wait for a "
                                       "submission slot and the polling (default 1200). The service "
                                       "kills the job at 15 minutes regardless."},
            "poll_interval": {"type": "integer", "description": "Polling interval in seconds (default 10)."},
        },
        "required": ["output"],
    },
}


def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    if request_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [TOOL_SCHEMA]}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        if tool_name != "search_papers":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        try:
            summary = run_search(arguments)
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": f"Argument error: {e}"}], "isError": True},
            }
        except Exception as e:
            # Catch-all (httpx.HTTPError, RuntimeError, TimeoutError, ImportError
            # from a misconfigured proxy, etc.) so a failure ALWAYS returns a
            # JSON-RPC isError result instead of bubbling to main() and leaving
            # the caller hanging with no response.
            debug_log(f"search failed: {type(e).__name__}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": f"mechanic-db search failed: {type(e).__name__}: {e}"}], "isError": True},
            }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]},
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def read_message():
    global _use_ndjson
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.decode("utf-8").rstrip("\r\n")

    if line.lower().startswith("content-length:"):
        try:
            content_length = int(line.split(":", 1)[1].strip())
        except ValueError:
            return None
        while True:
            hdr = sys.stdin.readline()
            if not hdr:
                return None
            if hdr.decode("utf-8").rstrip("\r\n") == "":
                break
        body = sys.stdin.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    if line.startswith("{") or line.startswith("["):
        _use_ndjson = True
        try:
            return json.loads(line)
        except Exception:
            return None

    return None


def main():
    debug_log("Entering main loop")
    while True:
        try:
            request = read_message()
            if request is None:
                break
            response = handle_request(request)
            if response:
                send_response(response)
        except Exception as e:
            debug_log(f"ERROR: {e}")
    debug_log("=== Server Exiting ===")


if __name__ == "__main__":
    main()

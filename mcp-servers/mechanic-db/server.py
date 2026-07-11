#!/usr/bin/env python3
"""Mechanic-DB Search MCP Server — cloud paper-retrieval bridge.

Wraps the mechanic_database cloud SEARCH service as a single MCP tool,
`search_papers`. The configured API key reaches this process via the plugin
manifest's mcpServers env mapping (`${MECHANIC_DB_API_KEY}` read from the
environment that launched Claude Code); this is the only channel through which
a plugin-configured secret reliably arrives, so the retrieval call lives here
rather than in a Bash-invoked standalone script.

Environment Variables:
    MECHANIC_DB_API_KEY   - cloud SEARCH key (sk_...). Empty => skip gracefully.
    MECHANIC_DB_SERVER_NAME - MCP server name (default: mechanic-db).

The service base URL is at http://mechanist.openkg.cn.

Contract:
  * The tool writes the FULL server response JSON to the caller-supplied
    `output` path (so 300-paper payloads stay on disk, out of the model's
    context) and returns only a compact {count, output, skipped} summary.
  * If the API key is empty it writes {"papers": [], "skipped": true,
    "reason": "no_api_key"} and reports skipped=true — callers treat
    mechanic-db as simply unavailable and continue with their other sources.
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
BASE_URL = "http://mechanist.openkg.cn"
SERVER_NAME = os.environ.get("MECHANIC_DB_SERVER_NAME", "mechanic-db")

TERMINAL_OK = {"succeeded", "completed", "done", "finished"}
TERMINAL_ERR = {"failed", "error"}

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


def poll(client: httpx.Client, headers: dict, job_id: str, timeout_s: int, interval_s: int) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        data = client.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=60).json()
        status = data.get("status", "")
        debug_log(f"[{job_id}] status={status}")
        if status in TERMINAL_OK:
            return data
        if status in TERMINAL_ERR:
            raise RuntimeError(f"job {job_id} failed: {data}")
        time.sleep(interval_s)
    raise TimeoutError(f"polling exceeded {timeout_s}s for job {job_id}")


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

    if not API_KEY:
        debug_log("API_KEY empty; skipping cloud SEARCH.")
        write_output(output, {"papers": [], "skipped": True, "reason": "no_api_key"})
        return {"skipped": True, "reason": "no_api_key", "count": 0, "output": output}

    headers = {"Authorization": f"Bearer {API_KEY}"}
    timeout_s = args.get("timeout", 1200)
    interval_s = args.get("poll_interval", 10)

    # trust_env=False: ignore ambient proxy env vars (http_proxy / all_proxy).
    # The SEARCH backend is reached at the fixed BASE_URL, which should never
    # be tunneled through a personal SOCKS/HTTP proxy. Honoring a
    # `all_proxy=socks5://...` here would also force an httpx[socks]/socksio
    # dependency and crash the connect with ImportError before any request is
    # sent — the exact failure that made earlier calls hang with no response.
    with httpx.Client(trust_env=False) as client:
        job = client.post(f"{BASE_URL}/search", json=build_payload(args), headers=headers, timeout=60)
        job.raise_for_status()
        job_id = job.json().get("job_id")
        if not job_id:
            raise RuntimeError(f"malformed submit response: {job.text[:500]}")
        debug_log(f"submitted job_id={job_id}")
        result = poll(client, headers, job_id, timeout_s, interval_s)

    # Cloud service nests papers under result["result"]["papers"]; hoist them
    # so downstream callers can rely on result["papers"].
    if not result.get("papers") and isinstance(result.get("result"), dict):
        result["papers"] = result["result"].get("papers", [])
    result.setdefault("papers", [])
    result["skipped"] = False
    write_output(output, result)
    return {"skipped": False, "count": len(result["papers"]), "output": output}


# ---------------------------------------------------------------------------
# JSON-RPC scaffolding (mirrors mcp-servers/llm-chat/server.py)
# ---------------------------------------------------------------------------

TOOL_SCHEMA = {
    "name": "search_papers",
    "description": (
        "Retrieve papers from the mechanic_database cloud SEARCH service. "
        "Pass an Agent-built `decomposed` query object (preferred) or a flat "
        "`query` string. The full result JSON is written to `output`; the tool "
        "returns only a {count, output, skipped} summary, so read the papers[] "
        "list back from the output file. One call takes ~3-20 minutes."
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
            "timeout": {"type": "integer", "description": "Polling timeout in seconds (default 1200)."},
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

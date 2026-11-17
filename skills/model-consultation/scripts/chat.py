#!/usr/bin/env python3
"""Consult an external model using an OpenAI-compatible chat-completions API.

Credentials come from LLM_API_KEY; endpoint and model can be configured with
LLM_BASE_URL and LLM_MODEL. LLM_FALLBACK_MODEL is optional and explicit.
Input is text, a UTF-8 file, or stdin. No local file access is granted to the
remote model beyond the text the caller deliberately supplies.
"""

import argparse
import json
import math
import os
from pathlib import Path
import sys


def consult(prompt, *, system="", model=None, timeout=300, max_tokens=4096):
    """Return actual/requested model metadata and response text, or raise."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Provide a nonempty prompt.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be a positive finite number.")
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer.")
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise ValueError("Set LLM_API_KEY in the script's environment.")
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("Install this skill's scripts/requirements.txt before consultation.") from exc

    requested = model or os.environ.get("LLM_MODEL") or "gpt-5.4"
    fallback = os.environ.get("LLM_FALLBACK_MODEL", "").strip()
    endpoint = (os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": prompt})
    attempts = [requested, requested]
    if fallback and fallback != requested:
        attempts.append(fallback)

    with httpx.Client(timeout=timeout) as client:
        for index, current in enumerate(attempts):
            try:
                response = client.post(
                    endpoint + "/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": current, "messages": messages, "max_tokens": max_tokens},
                )
            except httpx.TransportError:
                if index + 1 < len(attempts):
                    continue
                raise RuntimeError("Could not reach the external model after retries.") from None
            if response.status_code == 504 and index + 1 < len(attempts):
                continue
            if response.status_code != 200:
                # Do not print provider bodies: they may echo submitted material.
                raise RuntimeError(f"External model request failed with HTTP {response.status_code}.")
            try:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError):
                raise RuntimeError("External model returned an invalid chat response.") from None
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("External model returned no response text.")
            return {
                "requested_model": requested,
                "model": data.get("model") or current,
                "fallback_used": current != requested,
                "response": answer,
            }
    raise RuntimeError("External model consultation failed.")


def read_text(path):
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8-sig")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt", help="Prompt text (use a file for long material).")
    prompt.add_argument("--prompt-file", help="UTF-8 prompt file, or - for stdin.")
    system = parser.add_mutually_exclusive_group()
    system.add_argument("--system", default="", help="Optional role instruction.")
    system.add_argument("--system-file", help="UTF-8 role-instruction file.")
    parser.add_argument("--model", help="Override LLM_MODEL for this call.")
    parser.add_argument("--timeout", type=float, default=300, help="Timeout in seconds per attempt.")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--output", help="Optional destination for the full JSON response.")
    args = parser.parse_args(argv)
    try:
        if args.prompt_file == "-" and args.system_file == "-":
            raise ValueError("Prompt and system instruction cannot both read stdin.")
        result = consult(
            read_text(args.prompt_file) if args.prompt_file else args.prompt,
            system=read_text(args.system_file) if args.system_file else args.system,
            model=args.model, timeout=args.timeout, max_tokens=args.max_tokens,
        )
        if args.output:
            output = Path(args.output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {key: value for key, value in result.items() if key != "response"}
            result["output"] = str(output)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as exc:
        error = str(exc)
        key = os.environ.get("LLM_API_KEY", "").strip()
        if key:
            error = error.replace(key, "[redacted]")
        print(json.dumps({"error": error}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

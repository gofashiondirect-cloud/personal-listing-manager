#!/usr/bin/env python3
"""PostToolUse: shrink oversized tool results before they enter Claude's context.

- Bash: long stdout/stderr -> first/last lines plus error lines from the middle.
- Other built-in tools (Grep, Glob, WebFetch, WebSearch, ...): the result keeps its exact
  structure (required by Claude Code), but long strings are cut and long lists capped.
- MCP/connector tools: JSON is compacted (noise keys, nulls and long values dropped), then capped.
The full original is saved to a temp file whose path is given to Claude.

Tune: CLAUDE_TRIM_MAX_LINES (200), CLAUDE_TRIM_KEEP (60), CLAUDE_TRIM_MAX_CHARS (12000),
      CLAUDE_TRIM_MAX_ITEMS (50).
"""
import json, os, re, tempfile, time
from _kit import setting, safe_run, log_event, read_input, emit

MAX_LINES = setting("CLAUDE_TRIM_MAX_LINES", 200)
KEEP = setting("CLAUDE_TRIM_KEEP", 60)
MAX_CHARS = setting("CLAUDE_TRIM_MAX_CHARS", 12000)
MAX_ITEMS = setting("CLAUDE_TRIM_MAX_ITEMS", 50)
ERR = re.compile(r"error|fail|exception|traceback|panic|fatal|warn", re.I)
NOISE = re.compile(r"(^|_)(node_id|avatar_url|gravatar_id|etag|_links|.+_url)$")
TOOL = ""
KEEP_URLS = {"url", "html_url", "web_url", "webUrl"}


def save_full(obj):
    log_event("trim", "trimmed", TOOL)
    fd, path = tempfile.mkstemp(prefix=f"claude-out-{int(time.time())}-", suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, default=str))
    return path


def trim_lines(text, note):
    lines = text.splitlines()
    if len(lines) <= MAX_LINES:
        return text
    middle = lines[KEEP:-KEEP]
    errs = [l for l in middle if ERR.search(l)][:40]
    parts = lines[:KEEP] + [f"\n... [{len(middle)} lines trimmed by hook{note}] ..."]
    if errs:
        parts += ["--- error/warning lines from trimmed section ---", *errs, "--- end ---\n"]
    return "\n".join(parts + lines[-KEEP:])


def trim_str(s, limit):
    if len(s) <= limit:
        return s
    head, tail = int(limit * 0.7), int(limit * 0.2)
    return s[:head] + f"\n... [{len(s) - head - tail} chars trimmed by hook] ...\n" + s[-tail:]


def shrink(obj, limit):
    """Same structure, smaller values."""
    if isinstance(obj, str):
        return trim_str(obj, limit)
    if isinstance(obj, list):
        return [shrink(x, limit) for x in obj[:MAX_ITEMS]]
    if isinstance(obj, dict):
        return {k: shrink(v, limit) for k, v in obj.items()}
    return obj


def compact_json(obj, depth=0):
    """For MCP results: drop noise, keep the useful fields."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if (NOISE.search(k) and k not in KEEP_URLS) or v in (None, "", [], {}):
                continue
            out[k] = compact_json(v, depth + 1)
        return out
    if isinstance(obj, list):
        items = [compact_json(x, depth + 1) for x in obj[:25]]
        return items + ([f"... {len(obj) - 25} more items trimmed by hook"] if len(obj) > 25 else [])
    if isinstance(obj, str):
        return trim_str(obj, 600)
    return obj


def mcp_text(resp):
    if isinstance(resp, str):
        return resp
    if isinstance(resp, list):
        return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in resp)
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        return mcp_text(resp["content"])
    return json.dumps(resp, default=str)


def main():
    data = read_input()
    global TOOL
    tool, resp = data.get("tool_name", ""), data.get("tool_response")
    TOOL = tool
    if resp is None or tool == "Agent":
        return
    size = len(json.dumps(resp, default=str))

    if tool.startswith("mcp__"):
        if size <= MAX_CHARS // 2:
            return
        text = mcp_text(resp)
        try:
            new = json.dumps(compact_json(json.loads(text)), separators=(",", ":"), ensure_ascii=False)
        except ValueError:
            new = text
        new = trim_str(new, MAX_CHARS)
        if len(new) >= len(text):
            return
        path = save_full(text)
        return emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                     "updatedMCPToolOutput": new + f"\n[compacted by hook from {len(text)} chars; full: {path}]"}})

    if tool == "Bash" and isinstance(resp, dict):
        text = "\n".join(s for s in (resp.get("stdout"), resp.get("stderr")) if s)
        if len(text.splitlines()) <= MAX_LINES and size <= MAX_CHARS * 2:
            return
        path = save_full(text)
        new = dict(resp)
        for k in ("stdout", "stderr"):
            if isinstance(new.get(k), str):
                new[k] = trim_str(trim_lines(new[k], f"; full output: {path}"), MAX_CHARS)
        return emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": new}})

    if size <= MAX_CHARS:
        return
    new = shrink(resp, max(2000, MAX_CHARS // 3))
    if len(json.dumps(new, default=str)) >= size:
        return
    path = save_full(resp)
    emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": new,
          "additionalContext": f"{tool} result was trimmed by a hook (long values cut, lists capped "
                               f"at {MAX_ITEMS}). Full result: {path}. Narrow the query if you need more."}})


if __name__ == "__main__":
    safe_run(main)

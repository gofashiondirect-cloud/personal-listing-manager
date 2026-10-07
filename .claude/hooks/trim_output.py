#!/usr/bin/env python3
"""PostToolUse(Bash): replace very long command output with head + error lines + tail.

The full output is saved to a temp file so Claude can grep it if needed.
Tune with env vars: CLAUDE_TRIM_MAX_LINES (default 200), CLAUDE_TRIM_KEEP (default 60).
"""
import json, os, re, sys, tempfile, time

MAX_LINES = int(os.environ.get("CLAUDE_TRIM_MAX_LINES", "200"))
KEEP = int(os.environ.get("CLAUDE_TRIM_KEEP", "60"))
ERR = re.compile(r"error|fail|exception|traceback|panic|fatal|warn", re.I)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    resp = data.get("tool_response")
    if isinstance(resp, dict):
        text = "\n".join(s for s in (resp.get("stdout"), resp.get("stderr")) if s)
    elif isinstance(resp, str):
        text = resp
    else:
        return
    lines = text.splitlines()
    if len(lines) <= MAX_LINES:
        return

    fd, path = tempfile.mkstemp(prefix=f"claude-out-{int(time.time())}-", suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
        f.write(text)

    middle = lines[KEEP:-KEEP]
    errs = [l for l in middle if ERR.search(l)][:40]
    parts = lines[:KEEP]
    parts.append(f"\n... [{len(middle)} lines trimmed by hook; full output: {path}] ...")
    if errs:
        parts.append("--- error/warning lines from trimmed section ---")
        parts.extend(errs)
        parts.append("--- end ---\n")
    parts.extend(lines[-KEEP:])

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedToolOutput": "\n".join(parts),
    }}))


if __name__ == "__main__":
    main()

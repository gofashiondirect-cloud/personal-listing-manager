#!/usr/bin/env python3
"""PreToolUse(Read): block reading a large file whole; ask for a section or grep instead.

Tune with env var CLAUDE_READ_MAX_LINES (default 500).
"""
import json, os, sys

MAX_LINES = int(os.environ.get("CLAUDE_READ_MAX_LINES", "500"))
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ipynb", ".svg"}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    inp = data.get("tool_input") or {}
    path = inp.get("file_path")
    if not path or inp.get("limit") or inp.get("offset"):
        return
    if os.path.splitext(path)[1].lower() in SKIP_EXT or not os.path.isfile(path):
        return
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        return
    if n <= MAX_LINES:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{path} has {n} lines (limit {MAX_LINES}). Grep for what you need, "
            f"or Read again with offset/limit to load only the relevant section."
        ),
    }}))


if __name__ == "__main__":
    main()

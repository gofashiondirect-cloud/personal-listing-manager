#!/usr/bin/env python3
"""PreToolUse(Read): block whole reads of large files, and re-reads of unchanged content.

A repeat read is blocked once; if Claude asks again (e.g. content was lost), it is allowed.
State resets on compaction (see session_summary.py).
Tune: CLAUDE_READ_MAX_LINES (default 500).
"""
import os
from _kit import setting, safe_run, log_event, read_input, session_path, load, save, emit

MAX_LINES = setting("CLAUDE_READ_MAX_LINES", 500)
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ipynb", ".svg"}


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
          "permissionDecision": "deny", "permissionDecisionReason": reason}})


def main():
    data = read_input()
    inp = data.get("tool_input") or {}
    path = inp.get("file_path")
    if not path or not os.path.isfile(path):
        return
    if "claude-out-" in os.path.basename(path):
        log_event("trim", "used_full")
    ranged = bool(inp.get("limit") or inp.get("offset"))

    # 1. Repeat-read guard
    state_file = session_path(data.get("session_id"), "reads.json")
    reads = load(state_file, {})
    key = f"{os.path.abspath(path)}|{inp.get('offset')}|{inp.get('limit')}"
    mtime = os.path.getmtime(path)
    prev = reads.get(key)
    repeat_guard = setting("CLAUDE_REPEAT_READ_GUARD", 1)
    if prev and prev[0] == mtime and prev[1] and repeat_guard:
        log_event("guard_read", "override", "repeat")
    if prev and prev[0] == mtime and not prev[1] and repeat_guard:
        log_event("guard_read", "deny", "repeat")
        reads[key] = [mtime, 1]
        save(state_file, reads)
        return deny(f"You already read this exact range of {path} and it hasn't changed since; "
                    "use what is already in context. If that content is no longer available, "
                    "request it again and it will be allowed.")
    reads[key] = [mtime, 0]
    save(state_file, reads)

    # 2. Large-file guard
    if ranged or os.path.splitext(path)[1].lower() in SKIP_EXT:
        return
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        return
    if n > MAX_LINES:
        log_event("guard_read", "deny", "large")
        reads.pop(key, None)
        save(state_file, reads)
        deny(f"{path} has {n} lines (limit {MAX_LINES}). Grep for what you need, "
             "or Read again with offset/limit to load only the relevant section.")


if __name__ == "__main__":
    safe_run(main)

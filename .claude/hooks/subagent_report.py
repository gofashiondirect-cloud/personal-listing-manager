#!/usr/bin/env python3
"""SubagentStop: send an over-long subagent report back to be condensed before the parent sees it.

Tune: CLAUDE_SUBAGENT_MAX_CHARS (3000, about 450 words).
"""
import os
from _kit import read_input, emit

MAX_CHARS = int(os.environ.get("CLAUDE_SUBAGENT_MAX_CHARS", "3000"))


def main():
    data = read_input()
    msg = data.get("last_assistant_message") or ""
    if data.get("stop_hook_active") or len(msg) <= MAX_CHARS:
        return
    emit({"decision": "block", "reason": (
        f"Your final report is {len(msg)} characters; the limit is {MAX_CHARS}. Rewrite it as a "
        "condensed final answer: the conclusion first, then only the key facts and file:line "
        "references the caller needs. No raw file contents, logs or long code blocks.")})


if __name__ == "__main__":
    main()

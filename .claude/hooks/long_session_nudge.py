#!/usr/bin/env python3
"""UserPromptSubmit: once the session transcript gets large, tell Claude to warn the user.

Every message re-sends the whole conversation, so long sessions cost the most.
Tune with env var CLAUDE_NUDGE_KB (default 400 KB of transcript).
"""
import json, os, sys

LIMIT_KB = int(os.environ.get("CLAUDE_NUDGE_KB", "400"))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    path = data.get("transcript_path")
    try:
        kb = os.path.getsize(path) // 1024
    except (TypeError, OSError):
        return
    if kb < LIMIT_KB:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": (
            f"This session's transcript is {kb} KB, which makes every reply costly. "
            "After answering, add one short line telling the user to start a new chat "
            "for the next unrelated task, or type /compact to continue this one."
        ),
    }}))


if __name__ == "__main__":
    main()

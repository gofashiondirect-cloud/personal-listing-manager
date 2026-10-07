#!/usr/bin/env python3
"""PreToolUse(Bash): before `git commit`, run the project's full test suite; block the commit on failure.

Skipped when nothing changed since the last passing run. Disable with CLAUDE_PRECOMMIT_TESTS=0.
"""
import hashlib, os, re, subprocess
from _kit import setting, safe_run, ROOT, read_input, state_dir, load, save, emit, log_event


def tree_stamp():
    out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT,
                         capture_output=True, text=True, timeout=10).stdout
    diff = subprocess.run(["git", "diff", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout
    return hashlib.sha1((out + diff).encode()).hexdigest()


def main():
    data = read_input()
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+commit\b", cmd) or not setting("CLAUDE_PRECOMMIT_TESTS", 1):
        return
    from stack import detect
    cmds = detect(ROOT)[1]
    from stack import database
    db = database(ROOT) or {}
    steps = [c for c in (db.get("check"), cmds.get("typecheck"), cmds.get("test")) if c]
    if os.path.exists(os.path.join(ROOT, ".claude", "hooks", "linkcheck.py")):
        from linkcheck import check
        broken = check(ROOT)
        if broken:
            return deny("Broken links/loops found:\n" + "\n".join(broken[:30]))
    if not steps:
        return
    stamp_file = os.path.join(state_dir(), "precommit.json")
    stamp = tree_stamp()
    if load(stamp_file, {}).get("passed") == stamp:
        return
    for step in steps:
        try:
            r = subprocess.run(step, shell=True, cwd=ROOT, capture_output=True, text=True,
                               timeout=setting("CLAUDE_SUITE_TIMEOUT", 600))
        except subprocess.TimeoutExpired:
            return  # too slow to gate on; CI will catch it
        if r.returncode not in (0, 5):
            log_event("precommit", "fail", step)
            tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-40:])
            return deny(f"Full check `{step}` fails, so the commit was stopped. Something else depends on "
                        f"what you changed. Fix it (or /undo), then commit again:\n{tail}")
    save(stamp_file, {"passed": stamp})
    log_event("precommit", "pass")


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
          "permissionDecisionReason": reason}})


if __name__ == "__main__":
    safe_run(main)

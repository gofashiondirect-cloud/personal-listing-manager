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
    from plan_check import open_plan, review_done
    plan = open_plan(ROOT)
    if plan and not review_done(plan):
        return deny("A plan is open (.claude/plans/current.md) and its final Review isn't done. Re-check the "
                    "request and Done-when, run the code-review skill on the diff, fix findings, tick Review "
                    "with what you checked, then commit.")
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
    stamp_file = os.path.join(state_dir(), "precommit.json")
    stamp = tree_stamp()
    state = load(stamp_file, {})
    if state.get("passed") == stamp:
        return
    from checks import HEAVY, deferred, fast_mode, run
    late = set(HEAVY) if fast_mode(data.get("session_id")) else deferred()
    extra = {}
    if "boot" in late:
        extra["boot"] = boot
    if "visual" in late and state.get("visual_seen") != stamp:
        extra["visual"] = visual
    failing = run(extra, stamp_file, stamp)
    if failing:
        return deny(failing)
    if not steps:
        save(stamp_file, {**load(stamp_file, {}), "passed": stamp})
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
    save(stamp_file, {**load(stamp_file, {}), "passed": stamp})
    log_event("precommit", "pass")


def boot(stamp_file, stamp):
    from stack import detect
    cmd = detect(ROOT)[1].get("dev")
    if not cmd or cmd.startswith("open "):
        return None
    from smoke import smoke
    ok, tail = smoke(cmd, setting("CLAUDE_SMOKE_SECONDS", 25))
    return None if ok else f"The app no longer starts (`{cmd}`), so the commit was stopped:\n{tail}"


def visual(stamp_file, stamp):
    """Show visual changes once per change set; committing again after review is allowed."""
    import visual as vis
    if not vis.chrome():
        return None
    cfg = vis.server_config()
    results = vis.check_server(cfg) if cfg else vis.check_static()
    save(stamp_file, {**load(stamp_file, {}), "visual_seen": stamp})
    if not results:
        return None
    return ("Before committing, review how these pages changed:\n" + vis.report(results) +
            "\nIf all changes are intended, run the same commit again; otherwise fix them first.")


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
          "permissionDecisionReason": reason}})


if __name__ == "__main__":
    safe_run(main)

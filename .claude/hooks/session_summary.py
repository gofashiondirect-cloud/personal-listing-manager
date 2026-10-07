#!/usr/bin/env python3
"""SessionStart: give Claude a compact project overview so it needn't explore.

Prints branch, recent commits, git status and a depth-limited file tree.
"""
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import setting, safe_run, log_event, state_dir, session_path, load, read_input

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
SKIP = {".git", "node_modules", "dist", "build", ".venv", "venv", "coverage",
        "__pycache__", ".next", "target", ".cache"}
MAX_DEPTH, MAX_ENTRIES = 2, 80


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def tree():
    out = []
    for dirpath, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith("."))
        if depth >= MAX_DEPTH:
            dirs[:] = []
        for name in sorted(files):
            out.append(os.path.normpath(os.path.join(rel, name)))
            if len(out) >= MAX_ENTRIES:
                return out + ["... (truncated)"]
    return out


def usage_summary(days=7):
    usage = load(os.path.join(state_dir(), "usage.json"), {})
    since = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    rows = [r for r in usage.values() if r.get("date", "") >= since]
    if not rows:
        return []
    by_proj = {}
    for r in rows:
        by_proj[r["project"]] = by_proj.get(r["project"], 0) + r.get("output_tokens", 0)
    top = ", ".join(f"{p} {n:,}" for p, n in sorted(by_proj.items(), key=lambda x: -x[1])[:3])
    return [f"Usage last {days}d: {len(rows)} sessions; output tokens by project: {top}"]


data = read_input()
if data.get("source") in ("compact", "clear"):
    try:
        os.remove(session_path(data.get("session_id"), "reads.json"))
    except OSError:
        pass

lines = ["## Project snapshot (from SessionStart hook)"]
branch = git("branch", "--show-current")
if branch:
    lines.append(f"Branch: {branch}")
    log = git("log", "--oneline", "-5")
    if log:
        lines += ["Recent commits:", log]
    status = git("status", "--short")
    lines.append("Uncommitted changes:\n" + status if status else "Working tree clean.")
lines += [f"Files (depth {MAX_DEPTH}, max {MAX_ENTRIES}):", *tree()]
try:
    from stack import sync_claude_md
    block = sync_claude_md(ROOT)
    if block:
        lines += [l for l in block.splitlines() if not l.startswith("<!--")]
except Exception:
    pass
if data.get("source") == "compact":
    label = load(session_path(data.get("session_id"), "label.json"), {}).get("label")
    lines.insert(1, "Context was just compacted. Continue from the summary; re-read only the files "
                    "the next step needs, using grep or offset/limit." + (f" Task: {label}." if label else ""))
def health():
    """Report hook scripts that no longer compile and hook errors from the last 2 days."""
    hooks_dir = os.path.dirname(os.path.abspath(__file__))
    out = []
    for f in sorted(os.listdir(hooks_dir)):
        if f.endswith(".py"):
            try:
                compile(open(os.path.join(hooks_dir, f), encoding="utf-8").read(), f, "exec")
            except SyntaxError as e:
                out.append(f"BROKEN HOOK {f}: line {e.lineno}: {e.msg}")
    since = time.strftime("%Y-%m-%d", time.localtime(time.time() - 2 * 86400))
    try:
        errs = [l.strip() for l in open(os.path.join(state_dir(), "hook-errors.log"), encoding="utf-8")
                if l[:10] >= since]
    except OSError:
        errs = []
    out += [f"Hook error: {e}" for e in errs[-5:]]
    if out:
        out.insert(0, "Kit health: fix these first (hooks live in .claude/hooks/, rules in .claude/kit/):")
    return out


for part in (usage_summary, health):
    try:
        lines += part()
    except Exception:
        pass
try:
    from tune import tune
    changes = tune()
    if changes:
        lines.append("Kit auto-tuned today: " + "; ".join(changes))
except Exception:
    pass
print("\n".join(lines))  # kit-ignore: stdout is the hook protocol

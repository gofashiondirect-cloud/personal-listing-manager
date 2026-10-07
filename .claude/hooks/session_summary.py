#!/usr/bin/env python3
"""SessionStart: give Claude a compact project overview so it needn't explore.

Prints branch, recent commits, git status and a depth-limited file tree.
"""
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import state_dir, session_path, load, read_input

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
lines += usage_summary()
print("\n".join(lines))

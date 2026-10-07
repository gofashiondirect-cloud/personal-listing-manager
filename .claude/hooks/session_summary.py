#!/usr/bin/env python3
"""SessionStart: give Claude a compact project overview so it needn't explore.

Prints branch, recent commits, git status and a depth-limited file tree.
"""
import os, subprocess

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
print("\n".join(lines))

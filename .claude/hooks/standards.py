#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit): give Claude the right-way checklist for the file type it is about to touch.

Each checklist is shown once per session. Checklists live in .claude/standards/<type>.md
(or ~/.claude/standards for a global install); add <type>.local.md to extend one for a project.
"""
import os, re
from _kit import safe_run, ROOT, HOOKS, read_input, session_path, load, save, emit

RULES = [
    (r"\.(html?|njk|hbs|ejs)$", ["html", "ux"]),
    (r"\.(css|scss|sass|less)$", ["css", "ux"]),
    (r"\.(jsx|tsx|vue|svelte)$", ["react", "javascript", "ux"]),
    (r"\.(js|mjs|cjs|ts)$", ["javascript"]),
    (r"\.py$", ["python"]),
    (r"(\.sql$|(^|/)migrations?/|(^|/)db/migrate/|schema\.prisma$)", ["sql"]),
    (r"(^|/)(api|routes|controllers|endpoints)/|(^|/)(views|urls|routes|router)\.(py|js|ts)$|/route\.(js|ts)$", ["api"]),
    (r"(^|/)(Dockerfile|docker-compose[^/]*\.ya?ml|Procfile|vercel\.json|netlify\.toml|fly\.toml|render\.ya?ml)$|"
     r"(^|/)\.github/workflows/|(^|/)(infra|deploy|terraform|k8s|helm)/", ["devops"]),
    (r"(auth|login|signup|register|account|profile|user|cookie|consent|analytics|tracking|privacy|payment|"
     r"checkout|billing|newsletter|subscribe|contact)", ["privacy"]),
    (r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$", ["tests"]),
]


def standards_dirs():
    return [os.path.join(ROOT, ".claude", "standards"),
            os.path.normpath(os.path.join(HOOKS, "..", "standards")),
            os.path.normpath(os.path.join(HOOKS, "..", "kit", "standards"))]


def read_standard(name):
    text = ""
    for d in standards_dirs():
        base = os.path.join(d, f"{name}.md")
        if not text and os.path.exists(base):
            text = open(base, encoding="utf-8").read().strip()
        local = os.path.join(d, f"{name}.local.md")
        if os.path.exists(local):
            text += "\n" + open(local, encoding="utf-8").read().strip()
    return text


def main():
    data = read_input()
    path = (data.get("tool_input") or {}).get("file_path") or ""
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/") if path else ""
    if not rel or rel.startswith((".claude/", "..")) or rel.startswith(".github/") and "workflows" not in rel:
        return
    wanted = ["architecture"] if data.get("tool_name") == "Write" and not os.path.exists(path) else []
    for rx, names in RULES:
        if re.search(rx, rel, re.I):
            wanted += [n for n in names if n not in wanted]
    state_file = session_path(data.get("session_id"), "standards.json")
    shown = load(state_file, [])
    new = [n for n in wanted if n not in shown]
    texts = [t for t in (read_standard(n) for n in new) if t]
    if not texts:
        return
    save(state_file, shown + new)
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext":
          "Follow these standards for this file (project rules in CLAUDE.md take precedence):\n\n"
          + "\n\n".join(texts)}})


if __name__ == "__main__":
    safe_run(main)

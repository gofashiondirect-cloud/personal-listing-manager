#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): run a fast check on the changed file; report failures to Claude.

Per-project overrides in .claude/checks.json, e.g. {".ts": "npx --no-install tsc --noEmit", ".py": "ruff check {file}"}.
An empty string disables checks for that extension.
"""
import os, shutil, subprocess
from _kit import ROOT, PY, read_input, load, save, session_path, emit

TIMEOUT = int(os.environ.get("CLAUDE_CHECK_TIMEOUT", "60"))
MAX_FILE_LINES = int(os.environ.get("CLAUDE_MAX_FILE_LINES", "400"))
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".rb",
            ".php", ".cs", ".swift", ".vue", ".svelte", ".css", ".scss", ".html", ".sh"}


def size_warning(data, path, ext):
    """Once per file per session: nudge Claude to split files that grow too big."""
    if ext not in CODE_EXT:
        return None
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
    except OSError:
        return None
    state_file = session_path(data.get("session_id"), "size-warned.json")
    warned = load(state_file, [])
    if n <= MAX_FILE_LINES or path in warned:
        return None
    save(state_file, warned + [path])
    return (f"{path} is now {n} lines (guideline {MAX_FILE_LINES}). If it fits the task, split it into "
            "smaller, well-named modules so future sessions read less. Otherwise carry on.")


def default_cmd(ext):
    eslint = os.path.join(ROOT, "node_modules", ".bin", "eslint")
    if ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx") and os.path.exists(eslint):
        return f'"{eslint}" {{file}}'
    if ext == ".py":
        return "ruff check {file}" if shutil.which("ruff") else PY + " -m py_compile {file}"
    if ext == ".json":
        return PY + ' -c "import json,sys; json.load(open(sys.argv[1], encoding=\'utf-8\'))" {file}'
    if ext in (".js", ".mjs", ".cjs") and shutil.which("node"):
        return "node --check {file}"
    if ext == ".sh" and shutil.which("bash"):
        return "bash -n {file}"
    return None


def main():
    data = read_input()
    path = (data.get("tool_input") or {}).get("file_path")
    if not path or not os.path.isfile(path):
        return
    ext = os.path.splitext(path)[1].lower()
    warning = size_warning(data, path, ext)
    custom = load(os.path.join(ROOT, ".claude", "checks.json"), {})
    cmd = custom[ext] if ext in custom else default_cmd(ext)
    if not cmd:
        return warn(warning)
    cmd = cmd.replace("{file}", f'"{path}"')
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return warn(warning)
    if r.returncode == 0:
        return warn(warning)
    out = (r.stdout + r.stderr).strip().splitlines()[-40:]
    emit({"decision": "block",
          "reason": f"Check failed after editing {path} (`{cmd}`):\n" + "\n".join(out)
                    + "\nFix this before moving on." + (f"\n{warning}" if warning else "")})


def warn(warning):
    if warning:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": warning}})


if __name__ == "__main__":
    main()

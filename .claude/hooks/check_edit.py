#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): run a fast check on the changed file; report failures to Claude.

Per-project overrides in .claude/checks.json, e.g. {".ts": "npx --no-install tsc --noEmit", ".py": "ruff check {file}"}.
An empty string disables checks for that extension.
"""
import os, shutil, subprocess
from _kit import ROOT, PY, read_input, load, emit

TIMEOUT = int(os.environ.get("CLAUDE_CHECK_TIMEOUT", "60"))


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
    custom = load(os.path.join(ROOT, ".claude", "checks.json"), {})
    cmd = custom[ext] if ext in custom else default_cmd(ext)
    if not cmd:
        return
    cmd = cmd.replace("{file}", f'"{path}"')
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return
    if r.returncode == 0:
        return
    out = (r.stdout + r.stderr).strip().splitlines()[-40:]
    emit({"decision": "block",
          "reason": f"Check failed after editing {path} (`{cmd}`):\n" + "\n".join(out)
                    + "\nFix this before moving on."})


if __name__ == "__main__":
    main()

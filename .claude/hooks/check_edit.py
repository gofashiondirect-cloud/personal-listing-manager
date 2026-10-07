#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): run a fast check on the changed file; report failures to Claude.

First runs the project's own formatter (auto-detected; only if the project has one configured).
Per-project overrides in .claude/checks.json, e.g. {".ts": "npx --no-install tsc --noEmit",
".py": "ruff check {file}", "format": {".py": "black -q {file}"}}. An empty string disables one.
"""
import os, re, shutil, subprocess
from _kit import setting, safe_run, log_event, ROOT, PY, read_input, load, save, session_path, emit

TIMEOUT = setting("CLAUDE_CHECK_TIMEOUT", 60)
MAX_FILE_LINES = setting("CLAUDE_MAX_FILE_LINES", 400)
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
    if ext in (".html", ".htm"):
        return PY + f' "{os.path.join(os.path.dirname(os.path.abspath(__file__)), "htmlcheck.py")}" {{file}}'
    if ext == ".json":
        return PY + ' -c "import json,sys; json.load(open(sys.argv[1], encoding=\'utf-8\'))" {file}'
    if ext in (".js", ".mjs", ".cjs") and shutil.which("node"):
        return "node --check {file}"
    if ext == ".sh" and shutil.which("bash"):
        return "bash -n {file}"
    return None


FORMAT_EXT = {
    "prettier": {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".css", ".scss", ".html", ".json", ".md", ".yaml", ".yml", ".vue"},
    "ruff": {".py"}, "black": {".py"}, "gofmt": {".go"}, "rustfmt": {".rs"},
}


def auto_format(path, ext, custom):
    """Run the project's own formatter on the edited file. Returns a note if the file changed."""
    if "format" in custom:
        cmd = custom["format"].get(ext)
    else:
        from stack import detect
        cmd = detect(ROOT)[1].get("formatter")
        if cmd and not any(tool in cmd and ext in exts for tool, exts in FORMAT_EXT.items()):
            cmd = None
    if not cmd:
        return None
    before = os.path.getmtime(path), os.path.getsize(path)
    try:
        subprocess.run(cmd.replace("{file}", f'"{path}"'), shell=True, cwd=ROOT,
                       capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    if (os.path.getmtime(path), os.path.getsize(path)) != before:
        return f"{os.path.basename(path)} was auto-formatted by the project's formatter."
    return None


SIG = [re.compile(p, re.M) for p in (
    r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)",                     # python
    r"(?:^|\s)(?:export\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*\(([^)]*)\)",  # js function
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",       # js arrow
    r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(([^)]*)\)",                    # go
)]


def signatures(code):
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip() for rx in SIG for m in rx.finditer(code or "")}


def caller_note(data, path):
    """If an edit renamed a function or changed its parameters, list the places that call it."""
    inp = data.get("tool_input") or {}
    pairs = [(e.get("old_string"), e.get("new_string")) for e in inp.get("edits", [])] or \
            [(inp.get("old_string"), inp.get("new_string"))]
    changed = []
    for old, new in pairs:
        before, after = signatures(old), signatures(new)
        changed += [n for n, params in before.items() if after.get(n) != params]
    notes = []
    for name in sorted(set(changed))[:5]:
        try:
            out = subprocess.run(["git", "grep", "-n", "-w", name, "--", ".", ":!*.md"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=10).stdout.splitlines()
        except Exception:
            continue
        rel = os.path.relpath(path, ROOT)
        uses = [l[:160] for l in out if not l.startswith(rel + ":")][:15]
        if uses:
            notes.append(f"`{name}` changed signature/name; update these callers:\n" + "\n".join(uses))
    return "\n".join(notes) or None


def rule_problems(data, path):
    """Core-rule violations in the lines this edit touched (whole file for Write)."""
    if not setting("CLAUDE_RULE_CHECKS", 1):
        return []
    from codecheck import check, region_for
    text = open(path, encoding="utf-8", errors="replace").read()
    inp = data.get("tool_input") or {}
    if data.get("tool_name") == "Write" or "content" in inp:
        region = None
    else:
        news = [e.get("new_string") for e in inp.get("edits", [])] or [inp.get("new_string")]
        regions = [r for r in (region_for(text, n) for n in news if n) if r]
        if not regions:
            return []
        region = (min(r[0] for r in regions), max(r[1] for r in regions))
    return check(path, text, region)


def main():
    data = read_input()
    path = (data.get("tool_input") or {}).get("file_path")
    if not path or not os.path.isfile(path):
        return
    ext = os.path.splitext(path)[1].lower()
    custom = load(os.path.join(ROOT, ".claude", "checks.json"), {})
    formatted = auto_format(path, ext, custom)
    warning = "\n".join(x for x in (formatted, size_warning(data, path, ext), caller_note(data, path)) if x) or None
    rules = rule_problems(data, path)
    if rules:
        log_event("rules", "block", ext)
        return emit({"decision": "block", "reason":
                     f"{os.path.relpath(path, ROOT)} breaks the core coding rules:\n" + "\n".join(rules[:20])
                     + "\nFix these now. If one is genuinely intended, add `kit-ignore: <reason>` on that line."
                     + (f"\n{warning}" if warning else "")})
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
    safe_run(main)

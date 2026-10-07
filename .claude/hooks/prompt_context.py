#!/usr/bin/env python3
"""UserPromptSubmit: add cheap pointers to the user's message so Claude searches less.

- Names likely-relevant project files when the message mentions things but no paths.
- When a big log or paste is included, extracts its error lines and tells Claude to focus on them.
Tune: CLAUDE_HINT_MAX_FILES (8), CLAUDE_PASTE_LINES (60).
"""
import os, re, subprocess
from _kit import setting, safe_run, log_event, ROOT, read_input, emit

MAX_FILES = setting("CLAUDE_HINT_MAX_FILES", 8)
PASTE_LINES = setting("CLAUDE_PASTE_LINES", 60)
ERR = re.compile(r"error|exception|traceback|fail|fatal|panic|denied|not found|undefined|cannot|\bat \S+:\d+", re.I)
STOP = set("""about above after again all also and any are because been before being below between both but
can could did does doing done down during each few for from further had has have having her here him his how
into its just like make more most need now off once only other our out over own same should some such than that
the their them then there these they this those through too under until very was were what when where which while
who why will with would you your yes please want thing things work working build add fix change update check use
code file files project app make sure new get got let lets also okay ok""".split())
SKIP_DIRS = ("node_modules/", "dist/", "build/", ".venv/", "vendor/", ".git/", "coverage/")


def project_files():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout
        files = out.splitlines()
    except Exception:
        files = []
    if not files:
        for dp, dirs, fs in os.walk(ROOT):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d + "/" not in SKIP_DIRS]
            files += [os.path.relpath(os.path.join(dp, f), ROOT) for f in fs]
            if len(files) > 5000:
                break
    return [f for f in files if not f.startswith(SKIP_DIRS) and not f.startswith(".claude/")]


def file_hints(prompt):
    if re.search(r"[\w-]+/[\w./-]+|\b[\w-]+\.(py|js|ts|tsx|jsx|css|html|md|json|go|rs|java|rb|php|sql|yml|yaml)\b", prompt):
        return []  # user already named files
    words = {w for w in re.findall(r"[a-z][a-z0-9_-]{3,}", prompt.lower()) if w not in STOP}
    if not words:
        return []
    scored = []
    for f in project_files():
        parts = set(re.split(r"[/._-]+", f.lower()))
        score = sum(2 if w in parts else 1 for w in words if w in f.lower())
        if score:
            scored.append((-score, len(f), f))
    return [f for _, _, f in sorted(scored)[:MAX_FILES]]


def paste_focus(prompt):
    lines = prompt.splitlines()
    if len(lines) < PASTE_LINES:
        return None
    errs = [l.strip()[:200] for l in lines if ERR.search(l)]
    msg = f"The user's message includes a large paste ({len(lines)} lines). Don't restate or summarise it; "
    if errs:
        msg += "focus on these error lines from it:\n" + "\n".join(errs[:20])
    else:
        msg += "find only the part relevant to their question."
    return msg


def main():
    prompt = read_input().get("prompt") or ""
    notes = []
    hints = file_hints(prompt)
    if hints:
        notes.append("Likely relevant files (from names; verify before relying on them): " + ", ".join(hints))
    focus = paste_focus(prompt)
    if focus:
        notes.append(focus)
    if notes:
        emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes)}})


if __name__ == "__main__":
    safe_run(main)

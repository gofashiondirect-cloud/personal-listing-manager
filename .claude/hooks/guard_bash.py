#!/usr/bin/env python3
"""PreToolUse(Bash): stop commands that flood the context, and suggest the cheap version.

Each blocked command is allowed if Claude sends the exact same command again.
Tune: CLAUDE_READ_MAX_LINES (500) for `cat` on large files.
"""
import os, re, shlex
from _kit import tuning, setting, safe_run, log_event, ROOT, read_input, session_path, load, save, emit

MAX_LINES = setting("CLAUDE_READ_MAX_LINES", 500)


def line_count(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def deps_current():
    nm = os.path.join(ROOT, "node_modules")
    if not os.path.isdir(nm):
        return False
    files = [os.path.join(ROOT, f) for f in ("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml")]
    return all(os.path.getmtime(f) <= os.path.getmtime(nm) for f in files if os.path.exists(f))


def problem(cmd):
    limited = re.search(r"\|\s*(head|tail|grep|wc|less|jq|sort|uniq|cut|awk|sed)\b|>\s*\S", cmd)
    for seg in re.split(r"&&|\|\||;", cmd):
        seg = seg.strip()
        m = re.match(r"cat\s+(.+)", seg)
        if m and not limited:
            try:
                args = [a for a in shlex.split(m.group(1).split("|")[0]) if not a.startswith("-")]
            except ValueError:
                args = []
            big = [a for a in args if line_count(os.path.join(ROOT, a) if not os.path.isabs(a) else a) > MAX_LINES]
            if big:
                return "cat", f"`cat` on large file(s) {big}: use grep, or the Read tool with offset/limit."
    if re.search(r"\bfind\s+(/|~|\$HOME)(\s|$)", cmd) and "-maxdepth" not in cmd:
        return "find", "`find` over the whole filesystem/home: search within the project, or add -maxdepth."
    if re.search(r"\bgit\s+(log|reflog)\b", cmd) and not re.search(r"(-n\s*\d+|\s-\d+|--max-count|\|\s*head)", cmd):
        return "gitlog", "Unbounded `git log`: add -n 20 (and --oneline if you only need subjects)."
    if re.search(r"\bls\s+(-\w*R|--recursive)", cmd) and not limited:
        return "lsR", "Recursive `ls`: use the Glob tool, or pipe through head."
    if re.search(r"\btree\b", cmd) and not re.search(r"-L\s*\d", cmd) and not limited:
        return "tree", "`tree` without depth: add -L 2."
    if re.fullmatch(r"\s*(npm\s+(install|i|ci)|pnpm\s+install|yarn(\s+install)?)\s*", cmd) and deps_current():
        return "deps", "Dependencies already installed and up to date with package.json/lockfiles; skip the install."
    if re.search(r"\b(npm|pnpm|yarn)\s+(install|i|ci|add)\b", cmd) and not limited and "--silent" not in cmd and "--quiet" not in cmd:
        return "install", "Package installs print long logs: add --silent (npm/pnpm) or pipe through tail -20."
    return None, None


def main():
    data = read_input()
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if "claude-out-" in cmd:
        log_event("trim", "used_full")
    key, reason = problem(cmd)
    if not reason or key in tuning().get("disabled_bash_rules", []):
        return
    state_file = session_path(data.get("session_id"), "bash-denied.json")
    denied = load(state_file, [])
    if cmd in denied:
        log_event("guard_bash", "override", key)
        return  # second identical attempt: Claude insists, allow it
    save(state_file, denied + [cmd])
    log_event("guard_bash", "deny", key)
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
          "permissionDecisionReason": reason + " (If you really need it as written, run the exact same command again.)"}})


if __name__ == "__main__":
    safe_run(main)

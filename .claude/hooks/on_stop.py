#!/usr/bin/env python3
"""Stop: log token usage, then make Claude keep the project self-improving before it finishes.

In order, once per session each:
  1. new top-level files/dirs missing from the CLAUDE.md project map -> update the map
  2. no task label yet (and real work was done) -> record one via task_log.py
  3. label repeated CLAUDE_SKILL_AFTER times with no skill -> create the skill
Trivial turns (fewer than 3 tool calls in the session) are never blocked.
"""
import csv, json, os, subprocess
from _kit import (ROOT, HOOKS, PY, read_input, state_dir, session_path, load, save,
                  emit, slug, project_name, today)

SKILL_AFTER = int(os.environ.get("CLAUDE_SKILL_AFTER", "3"))
MAX_BLOCKS = 3


def scan_transcript(path):
    """Return (usage totals, tool call count, model) from the session transcript."""
    msgs, tools, model = {}, 0, ""
    try:
        f = open(path, encoding="utf-8")
    except (TypeError, OSError):
        return {}, 0, ""
    with f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message") or {}
            if e.get("type") != "assistant" or not isinstance(m, dict):
                continue
            model = m.get("model") or model
            if m.get("usage"):
                msgs[m.get("id") or len(msgs)] = m["usage"]
            for block in m.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools += 1
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    totals = {k: sum(int(u.get(k) or 0) for u in msgs.values()) for k in keys}
    totals["turns"] = len(msgs)
    return totals, tools, model


def log_usage(sid, totals, model):
    if not totals.get("turns"):
        return
    d = state_dir()
    usage = load(os.path.join(d, "usage.json"), {})
    usage[sid] = {"date": usage.get(sid, {}).get("date", today()), "project": project_name(),
                  "model": model, **totals}
    save(os.path.join(d, "usage.json"), usage)
    with open(os.path.join(d, "usage.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["date", "project", "model", "turns", "input_tokens", "output_tokens",
                "cache_read_input_tokens", "cache_creation_input_tokens"]
        w.writerow(["session"] + cols)
        for s, r in sorted(usage.items(), key=lambda x: x[1].get("date", "")):
            w.writerow([s] + [r.get(c, "") for c in cols])


def unmapped_paths():
    claude_md = os.path.join(ROOT, "CLAUDE.md")
    try:
        text = open(claude_md, encoding="utf-8").read()
        out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT,
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return []
    if "## Project map" not in text:
        return []
    tops = set()
    for line in out.splitlines():
        if line[:2].strip() not in ("A", "??"):
            continue
        top = line[3:].strip().strip('"').split("/")[0]
        if top and not top.startswith(".") and top != "CLAUDE.md":
            tops.add(top)
    return sorted(t for t in tops if t not in text)


def main():
    data = read_input()
    sid = data.get("session_id") or "unknown"
    totals, tools, model = scan_transcript(data.get("transcript_path"))
    try:
        log_usage(sid, totals, model)
    except OSError:
        pass

    flags_file = session_path(sid, "stop.json")
    flags = load(flags_file, {"blocks": 0})
    if tools < 3 or flags["blocks"] >= MAX_BLOCKS:
        return

    def block(key, reason):
        flags[key] = True
        flags["blocks"] += 1
        save(flags_file, flags)
        emit({"decision": "block", "reason": reason})

    if not flags.get("map"):
        missing = unmapped_paths()
        if missing:
            return block("map", "Before finishing: add these new top-level paths to the "
                         "'## Project map' section of CLAUDE.md, one short line each: "
                         + ", ".join(missing))

    task_log = f'{PY} "{os.path.join(HOOKS, "task_log.py")}"'
    label = load(session_path(sid, "label.json"), {}).get("label")
    if not label and not flags.get("label"):
        log = load(os.path.join(state_dir(), "task-log.json"), {"tasks": []})
        known = sorted({e["label"] for e in log["tasks"]})[-30:]
        return block("label", "Before finishing: record a 2-4 word label for the kind of task "
                     f"done this session by running: {task_log} add \"<label>\" {sid}. "
                     + (f"Reuse one of these if it is the same kind of task: {known}. " if known else "")
                     + "Then finish normally.")

    if label and not flags.get("skill"):
        log = load(os.path.join(state_dir(), "task-log.json"), {"tasks": [], "skills": {}})
        n = sum(1 for e in log["tasks"] if slug(e["label"]) == slug(label))
        if n >= SKILL_AFTER and slug(label) not in log.get("skills", {}):
            return block("skill", f"'{label}' has now been done {n} times with no skill. Before finishing, "
                         f"create .claude/skills/{slug(label)}/SKILL.md (frontmatter: name, description "
                         "saying when to use it; body: the concise, tested steps from this session), "
                         f"then run: {task_log} skill \"{label}\" {slug(label)}")


if __name__ == "__main__":
    main()

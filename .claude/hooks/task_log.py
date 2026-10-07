#!/usr/bin/env python3
"""Task log used by the Stop hook to spot repeated work and force skill creation.

  task_log.py add "<label>" [session]  record this session's task
  task_log.py skill "<label>" <name>   register the skill that now covers a label
  task_log.py list                     show labels, counts and skills
"""
import json, os, sys
from _kit import setting, safe_run, log_event, state_dir, session_path, load, save, slug, project_name, today

SKILL_AFTER = setting("CLAUDE_SKILL_AFTER", 3)
LOG = os.path.join(state_dir(), "task-log.json")


def counts(log):
    c = {}
    for e in log["tasks"]:
        c[slug(e["label"])] = c.get(slug(e["label"]), 0) + 1
    return c


def main():
    log = load(LOG, {"tasks": [], "skills": {}})
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add" and len(sys.argv) > 2:
        label = sys.argv[2]
        log["tasks"].append({"date": today(), "project": project_name(), "label": label,
                             "session": sys.argv[3] if len(sys.argv) > 3 else ""})
        save(LOG, log)
        sid = sys.argv[3] if len(sys.argv) > 3 else "unknown"
        save(session_path(sid, "label.json"), {"label": label})
        n = counts(log)[slug(label)]
        skill = log["skills"].get(slug(label))
        msg = f"Logged '{label}' (seen {n}x)."
        if skill:
            msg += f" Covered by skill '{skill}'; use it next time."
        elif n >= SKILL_AFTER:
            msg += " Repeated task with no skill: you will be asked to create one."
        print(msg)
    elif cmd == "skill" and len(sys.argv) > 3:
        log["skills"][slug(sys.argv[2])] = sys.argv[3]
        save(LOG, log)
        print(f"Registered skill '{sys.argv[3]}' for '{sys.argv[2]}'.")
    else:
        c = counts(log)
        for k, n in sorted(c.items(), key=lambda x: -x[1]):
            print(f"{n:3}x  {k}" + (f"  -> skill {log['skills'][k]}" if k in log["skills"] else ""))


if __name__ == "__main__":
    safe_run(main)

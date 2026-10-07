#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) on .claude/plans/current.md: decide the disciplines up front.

Reads the plan as soon as it is written: planned file paths (routed like the standards hook) and
what the plan is about (login, payments, deploy, database...) give the disciplines. The dated
record is created or extended right away, so Claude builds against those checklists from the start.
The Stop hook still adds any discipline the real changes touch later.
"""
import os, re
from _kit import safe_run, ROOT, read_input, emit

TOPICS = {
    "privacy": r"login|sign[ -]?up|register|password|account|profile|personal data|payment|checkout|billing|"
               r"cookie|analytics|tracking|newsletter|contact form|email list|gdpr|consent",
    "devops": r"deploy|docker|ci/cd|pipeline|hosting|server config|environment variable|backup|monitoring",
    "sql": r"\bdatabase|\bschema\b|\bmigrations?\b|\b(db|database) (table|index)|\bcolumns?\b|\bsql\b",
    "api": r"\bapi\b|endpoint|route|webhook|rest",
    "ux": r"\bpage|screen|form|button|modal|layout|design|navigation|\bui\b|mobile",
    "architecture": r"new (module|file|page|component|service|feature)|refactor|restructure|folder",
    "tests": r"\btest",
}
PATH = re.compile(r"`?([\w./-]+\.(?:html?|css|scss|js|jsx|ts|tsx|vue|svelte|py|sql|prisma|ya?ml|toml|json)|Dockerfile)`?")


def specific_text(plan):
    """Only what is specific to this plan: title, request, done-when and the Changes section."""
    keep = re.findall(r"^(?:# Plan:|Request:|Done when:)(.*)$", plan, re.M)
    changes = re.search(r"^## Changes[^\n]*\n(.*?)(?=^## |\Z)", plan, re.M | re.S)
    if changes:
        keep.append(changes.group(1))
    return "\n".join(k for k in keep if "<" not in k or ">" not in k)


def planned_keys(plan):
    from standards import RULES
    text = specific_text(plan)
    keys = set()
    for path in PATH.findall(text):
        for rx, names in RULES:
            if re.search(rx, path, re.I):
                keys.update(names)
    for key, rx in TOPICS.items():
        if re.search(rx, text, re.I):
            keys.add(key)
    if keys & {"html", "css", "javascript", "react", "python", "sql", "api"}:
        keys.add("tests")
    return keys


def main():
    data = read_input()
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path.replace(os.sep, "/").endswith(".claude/plans/current.md") or not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()
    if re.search(r"^Status:\s*(done|cancelled)", text, re.I | re.M):
        return
    import records
    from plan_check import DISCIPLINE
    keys = sorted(k for k in planned_keys(text) if k in DISCIPLINE)
    if not keys:
        return
    record = records.current_record()
    if record and os.path.exists(record):
        added = records.sync(record, keys)
        if not added:
            return
        note = f"Plan now also touches: {', '.join(DISCIPLINE[k] for k in added)}; their checklists were added"
    else:
        title = re.search(r"^# Plan:\s*(.+)$", text, re.M)
        record, keys = records.create(title.group(1) if title else "change", keys)
        note = "Discipline record created"
    rel = os.path.relpath(record if os.path.isabs(record) else os.path.join(ROOT, record), ROOT)
    emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
        f"{note}: {rel}. This plan works against the best-practice checklists for: "
        f"{', '.join(DISCIPLINE[k] for k in keys)}. Build to meet each item, and fill each one "
        "(`- note:` how/where, or `- n/a:` reason) as you go, not at the end.")}})


if __name__ == "__main__":
    safe_run(main)

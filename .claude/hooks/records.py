#!/usr/bin/env python3
"""Dated discipline checklist records: the audit trail of which best practices a change met.

  records.py new <slug>   create .claude/records/<date>-<slug>.md with the full checklist of every
                          discipline the current changes touch, and link it from the open plan
  records.py check        list unfinished items (exit 1 if any)

Each item must end up as `- [x] <item> - note: <how/where>` or `- [x] <item> - n/a: <reason>`.
The Stop hook adds sections for disciplines touched later, and blocks finishing until all are filled.
"""
import os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import ROOT
from plan_check import DISCIPLINE, ITEM, plan_path, required_standards
from standards import read_standard

RECORDS = os.path.join(ROOT, ".claude", "records")
LINK = re.compile(r"^Record:.*$", re.M)
RECORD_PATH = re.compile(r"\.claude/records/[^\s)]+\.md")


def checklist(key):
    """Bullet items of a standard file, as unticked record lines."""
    items = [l[2:].strip() for l in read_standard(key).splitlines() if l.startswith("- ")]
    return [f"- [ ] {i} - note: " for i in items]


def section(key):
    return [f"## {DISCIPLINE[key]} ({key}.md)"] + checklist(key) + [""]


def current_record():
    try:
        line = LINK.search(open(plan_path(ROOT), encoding="utf-8").read())
    except OSError:
        return None
    found = RECORD_PATH.search(line.group(0)) if line else None
    return os.path.join(ROOT, found.group(0)) if found else None


def create(slug):
    os.makedirs(RECORDS, exist_ok=True)
    path = os.path.join(RECORDS, f"{time.strftime('%Y-%m-%d')}-{re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')}.md")
    keys = required_standards(ROOT)
    lines = [f"# Discipline record: {slug}", f"Date: {time.strftime('%Y-%m-%d %H:%M')}", "Plan: .claude/plans/current.md",
             "Fill every item: `- [x] ... - note: how/where (file:line, check, test)` or `- [x] ... - n/a: reason`.", ""]
    for k in keys:
        lines += section(k)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    plan = plan_path(ROOT)
    if os.path.exists(plan):
        text = open(plan, encoding="utf-8").read()
        text = LINK.sub(f"Record: {rel}", text) if LINK.search(text) else text.replace("\n", f"\nRecord: {rel}\n", 1)
        open(plan, "w", encoding="utf-8").write(text)
    return rel, keys


def sync(path):
    """Append sections for disciplines touched since the record was created."""
    text = open(path, encoding="utf-8").read()
    have = set(re.findall(r"^## .*\((\w+)\.md\)", text, re.M))
    new = [k for k in required_standards(ROOT) if k not in have]
    if new:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(l for k in new for l in section(k)))
    return new


def unfinished(path):
    """Per-discipline counts of items not ticked with a note or n/a."""
    out, name, todo, total = [], None, 0, 0
    for line in open(path, encoding="utf-8").read().splitlines() + ["## end"]:
        if line.startswith("## "):
            if name and todo:
                out.append(f"{name}: {todo} of {total} items not done")
            name, todo, total = line[3:], 0, 0
            continue
        m = ITEM.match(line)
        if m:
            total += 1
            body = m.group(2)
            filled = re.search(r"-\s*(note|n/a):\s*\S", body)
            if m.group(1).lower() != "x" or not filled:
                todo += 1
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "new":
        rel, keys = create(sys.argv[2] if len(sys.argv) > 2 else "change")
        print(f"Created {rel} with: {', '.join(DISCIPLINE[k] for k in keys) or 'no disciplines yet'}")
    else:
        path = current_record()
        if not path or not os.path.exists(path):
            sys.exit(print("no record linked from the open plan") or 1)
        sync(path)
        left = unfinished(path)
        print("\n".join(left) or "record complete")
        sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()

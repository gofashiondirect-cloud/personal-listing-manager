"""Read .claude/plans/current.md and report what is still unproven (used by on_stop.py and precommit.py)."""
import os, re

ITEM = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")


def plan_path(root):
    return os.path.join(root, ".claude", "plans", "current.md")


def open_plan(root):
    """Returns the plan text if a plan is in progress, else None."""
    p = plan_path(root)
    if not os.path.exists(p):
        return None
    text = open(p, encoding="utf-8").read()
    return None if re.search(r"^Status:\s*(done|cancelled)", text, re.I | re.M) else text


def unproven(text):
    missing = []
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        m = ITEM.match(line)
        if not m:
            continue
        done, body = m.group(1).lower() == "x", m.group(2).strip()
        if not done:
            missing.append(f"[{section}] not done: {body[:100]}")
        elif not re.search(r"\b(proof|dropped)\s*:", body, re.I):
            missing.append(f"[{section}] ticked without proof: {body[:100]}")
    return missing


def review_done(text):
    sect = text.split("## Review", 1)[1] if "## Review" in text else ""
    items = [ITEM.match(l) for l in sect.splitlines()]
    return any(m and m.group(1).lower() == "x" for m in items)

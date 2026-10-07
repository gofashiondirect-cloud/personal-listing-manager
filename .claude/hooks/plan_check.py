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


DISCIPLINE = {  # standard -> sign-off name shown in the plan
    "html": "Engineering (HTML)", "css": "Engineering (CSS)", "javascript": "Engineering (JS/TS)",
    "react": "Engineering (React)", "python": "Engineering (Python)", "architecture": "Architecture",
    "ux": "UX/UI", "tests": "QA", "sql": "Database", "api": "API", "privacy": "Privacy & security",
    "devops": "DevOps",
}


def required_signoffs(root):
    """Discipline names the current changes touch."""
    return sorted({DISCIPLINE[n] for n in required_standards(root)})


def required_standards(root):
    """Standard keys (html, ux, privacy, ...) the current changes touch, from the changed and new files."""
    import subprocess
    from standards import RULES
    out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=root,
                         capture_output=True, text=True, timeout=5).stdout
    needed = set()
    for line in out.splitlines():
        rel = line[3:].strip().strip('"').split(" -> ")[-1]
        if rel.startswith(".claude/") or rel in ("CHANGELOG.md", "CLAUDE.md"):
            continue
        if line[:2].strip() in ("??", "A"):
            needed.add("architecture")
        for rx, names in RULES:
            if re.search(rx, rel, re.I):
                needed.update(names)
    if needed & {"html", "css", "javascript", "react", "python", "sql", "api"}:
        needed.add("tests")
    return sorted(n for n in needed if n in DISCIPLINE)


def missing_signoffs(text, required):
    """Required disciplines without a ticked, proven line in the plan's '## Sign-off' section."""
    sect = text.split("## Sign-off", 1)[1].split("\n## ", 1)[0] if "## Sign-off" in text else ""
    signed = []
    for line in sect.splitlines():
        m = ITEM.match(line)
        if m and m.group(1).lower() == "x" and re.search(r"\b(proof|n/a)\s*:", m.group(2), re.I):
            signed.append(m.group(2).lower())
    def key(d):  # "Engineering (HTML)" -> "html"; "Privacy & security" -> "privacy"
        m = re.search(r"\((.+)\)", d)
        return (m.group(1) if m else d.split(" &")[0].split("/")[0]).lower()
    return [d for d in required if not any(key(d) in s for s in signed)]

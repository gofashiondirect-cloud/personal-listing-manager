#!/usr/bin/env python3
"""Auto-tune hook limits from the event log (run at most once a day by session_summary.py).

- A guard rule Claude overrides more than half the time (5+ blocks in 30 days) is switched off.
- Trimming: if Claude often opens the saved full output, limits go up 25%;
  if it never does across 20+ trims, they go down 15%.
Changes are written to tuning.json and explained in tuning-history.log.
"""
import json, os, time
from _kit import state_dir, load, save, today

BOUNDS = {"CLAUDE_TRIM_MAX_LINES": (100, 1000), "CLAUDE_TRIM_MAX_CHARS": (6000, 50000)}
DEFAULTS = {"CLAUDE_TRIM_MAX_LINES": 200, "CLAUDE_TRIM_MAX_CHARS": 12000}


def events(days=30):
    since = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    out = []
    try:
        with open(os.path.join(state_dir(), "events.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("date", "") >= since:
                    out.append(e)
    except OSError:
        pass
    return out


def tune(force=False):
    path = os.path.join(state_dir(), "tuning.json")
    t = load(path, {})
    if t.get("last_run") == today() and not force:
        return []
    t["last_run"] = today()
    ev, changes = events(), []

    def count(hook, kind, key=None):
        return sum(1 for e in ev if e["hook"] == hook and e["kind"] == kind and (key is None or e["key"] == key))

    for key in sorted({e["key"] for e in ev if e["hook"] == "guard_bash"}):
        d, o = count("guard_bash", "deny", key), count("guard_bash", "override", key)
        disabled = t.setdefault("disabled_bash_rules", [])
        if d >= 5 and o / d > 0.5 and key not in disabled:
            disabled.append(key)
            changes.append(f"disabled bash rule '{key}' (overridden {o}/{d})")

    d, o = count("guard_read", "deny", "repeat"), count("guard_read", "override", "repeat")
    if d >= 5 and o / d > 0.5 and t.get("CLAUDE_REPEAT_READ_GUARD", 1):
        t["CLAUDE_REPEAT_READ_GUARD"] = 0
        changes.append(f"disabled repeat-read guard (overridden {o}/{d})")

    trims, used = count("trim", "trimmed"), count("trim", "used_full")
    factor = 1.25 if trims >= 10 and used / trims > 0.3 else 0.85 if trims >= 20 and used == 0 else None
    if factor:
        for name, (lo, hi) in BOUNDS.items():
            old = t.get(name, DEFAULTS[name])
            new = int(min(hi, max(lo, old * factor)))
            if new != old:
                t[name] = new
                changes.append(f"{name} {old} -> {new} (full output used {used}/{trims} trims)")

    save(path, t)
    if changes:
        with open(os.path.join(state_dir(), "tuning-history.log"), "a", encoding="utf-8") as f:
            f.writelines(f"{today()} {c}\n" for c in changes)
    return changes


if __name__ == "__main__":
    print("\n".join(tune(force=True)) or "no changes")

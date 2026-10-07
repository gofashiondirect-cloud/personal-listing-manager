#!/usr/bin/env python3
"""Install the claude-kit (rules, hooks, settings) into a project or globally.

  python3 install.py --project /path/to/repo   adds .claude/ + CLAUDE.md section to that repo
  python3 install.py --global                  installs into ~/.claude for every project on this machine

Safe to re-run: kit hooks are replaced, your own settings and CLAUDE.md text are kept.
"""
import argparse, json, os, shutil, sys

KIT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(KIT)  # the .claude folder this kit ships in
START, END = "<!-- claude-kit:start -->", "<!-- claude-kit:end -->"
PROJECT_HOOKS = "${CLAUDE_PROJECT_DIR}/.claude/hooks/"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def merge_settings(dest, src, kit_files):
    for k, v in src.items():
        if k == "permissions":
            for kind in ("allow", "deny"):
                if not v.get(kind):
                    continue
                cur = dest.setdefault("permissions", {}).setdefault(kind, [])
                cur += [d for d in v.get(kind, []) if d not in cur]
        elif k == "env":
            for ek, ev in v.items():
                dest.setdefault("env", {}).setdefault(ek, ev)
        elif k == "hooks":
            for event, groups in v.items():
                cur = dest.setdefault("hooks", {}).setdefault(event, [])
                # drop older kit entries, keep everything else
                for g in cur:
                    g["hooks"] = [h for h in g.get("hooks", [])
                                  if not any(f in h.get("command", "") for f in kit_files)]
                cur[:] = [g for g in cur if g.get("hooks")] + groups
        else:
            dest.setdefault(k, v)
    return dest


def write_rules(path, rules):
    block = f"{START}\n{rules.strip()}\n{END}\n"
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if START in text and END in text:
        text = text[:text.index(START)] + block + text[text.index(END) + len(END):].lstrip("\n")
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--project")
    g.add_argument("--global", dest="glob", action="store_true")
    a = ap.parse_args()

    if a.glob:
        dest_claude = os.path.join(os.path.expanduser("~"), ".claude")
        rules_path = os.path.join(dest_claude, "CLAUDE.md")
    else:
        root = os.path.abspath(a.project)
        dest_claude = os.path.join(root, ".claude")
        rules_path = os.path.join(root, "CLAUDE.md")
    hooks_dir = os.path.join(dest_claude, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    kit_files = [f for f in os.listdir(os.path.join(SRC, "hooks")) if f.endswith(".py")]
    if os.path.abspath(hooks_dir) != os.path.abspath(os.path.join(SRC, "hooks")):
        for f in kit_files:
            shutil.copy2(os.path.join(SRC, "hooks", f), hooks_dir)

    src = load(os.path.join(SRC, "settings.json"), {})
    raw = json.dumps(src)
    if a.glob:
        # absolute paths and this machine's Python, so it works on Windows too
        raw = raw.replace("python3 ", json.dumps(f'"{sys.executable}" ')[1:-1])
        raw = raw.replace(PROJECT_HOOKS, hooks_dir.replace("\\", "/") + "/")
    src = json.loads(raw)
    if a.glob:
        src.get("env", {}).pop("CLAUDE_KIT_STATE_DIR", None)  # global state lives in ~/.claude/state

    settings_path = os.path.join(dest_claude, "settings.json")
    merged = merge_settings(load(settings_path, {}), src, kit_files)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")

    skills_src = os.path.join(KIT, "skills")
    if os.path.isdir(skills_src):
        shutil.copytree(skills_src, os.path.join(dest_claude, "skills"), dirs_exist_ok=True)
        if a.glob:  # skills must call the global hooks, not a project path
            for name in os.listdir(skills_src):
                md = os.path.join(dest_claude, "skills", name, "SKILL.md")
                if os.path.exists(md):
                    text = open(md, encoding="utf-8").read().replace(
                        "python3 .claude/hooks/", f'"{sys.executable}" "{hooks_dir}/'.replace("\\", "/"))
                    text = text.replace('checkpoint.py ', 'checkpoint.py" ').replace('checkpoint.py`', 'checkpoint.py"`')
                    open(md, "w", encoding="utf-8").write(text)

    write_rules(rules_path, open(os.path.join(KIT, "CLAUDE.kit.md"), encoding="utf-8").read())
    if not a.glob:
        text = open(rules_path, encoding="utf-8").read()
        if "## Project map" not in text[:text.index(START)] + text[text.index(END):]:
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write("# Project rules for Claude\n\n## Project map\n"
                        "- (Claude fills this in as it learns the project)\n\n" + text)
        kit_dst = os.path.join(dest_claude, "kit")
        if os.path.abspath(kit_dst) != KIT:
            shutil.copytree(KIT, kit_dst, dirs_exist_ok=True)

    if not a.glob:
        sys.path.insert(0, hooks_dir)
        try:
            from ci import write as write_ci
            wf = write_ci(os.path.dirname(dest_claude))
            if wf:
                print(f"CI workflow added: {wf}")
        except Exception as e:
            print(f"(CI workflow skipped: {e})")

    print(f"claude-kit installed -> {dest_claude} (rules in {rules_path})")


if __name__ == "__main__":
    main()

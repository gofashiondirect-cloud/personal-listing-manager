#!/usr/bin/env python3
"""Generate a GitHub Actions workflow that runs the project's checks on every push and PR.

  ci.py [root]   writes .github/workflows/claude-kit-ci.yml if the project has no workflows yet
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack import detect

HEAD = """name: checks
on:
  push:
  pull_request:
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""


def workflow(root):
    name, c = detect(root)
    steps = []
    if name == "node":
        pm = c.get("install", "npm install").split()[0]
        if pm == "pnpm":
            steps.append("      - uses: pnpm/action-setup@v4")
        steps.append("      - uses: actions/setup-node@v4\n        with:\n          node-version: 20")
        steps.append(f"      - run: {'npm ci' if pm == 'npm' and os.path.exists(os.path.join(root, 'package-lock.json')) else c['install']}")
    elif name == "python":
        steps.append("      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'")
        steps.append(f"      - run: pip install pytest ruff && {c.get('install', 'true')}")
    elif name == "go":
        steps.append("      - uses: actions/setup-go@v5\n        with:\n          go-version: stable")
    elif name == "rust":
        steps.append("      - uses: dtolnay/rust-toolchain@stable")
    for key in ("lint", "typecheck", "test", "build"):
        if key in c and not c[key].startswith("open "):
            steps.append(f"      - run: {c[key]}")
    steps.append("      - run: python3 .claude/hooks/linkcheck.py .")
    return HEAD + "\n".join(steps) + "\n"


def write(root):
    wf_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf_dir) and any(f.endswith((".yml", ".yaml")) for f in os.listdir(wf_dir)):
        return None  # the project already has CI; don't add a second one
    os.makedirs(wf_dir, exist_ok=True)
    path = os.path.join(wf_dir, "claude-kit-ci.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(workflow(root))
    return path


if __name__ == "__main__":
    print(write(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")) or "project already has CI workflows")

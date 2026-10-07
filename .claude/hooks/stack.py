"""Detect a project's stack and its run/test/lint/format/build commands (stdlib only).

Used by session_summary.py (writes the Commands block in CLAUDE.md), check_edit.py
(formatter) and on_stop.py (related tests).
"""
import json, os, re, shutil

START, END = "<!-- claude-kit:commands:start -->", "<!-- claude-kit:commands:end -->"


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _node(root):
    pkg_path = os.path.join(root, "package.json")
    if not os.path.exists(pkg_path):
        return None
    try:
        pkg = json.loads(_read(pkg_path) or "{}")
    except ValueError:
        pkg = {}
    pm = ("pnpm" if os.path.exists(os.path.join(root, "pnpm-lock.yaml")) else
          "yarn" if os.path.exists(os.path.join(root, "yarn.lock")) else
          "bun" if os.path.exists(os.path.join(root, "bun.lockb")) else "npm")
    scripts = pkg.get("scripts") or {}
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    run = lambda s: f"{pm} run {s}" if pm != "npm" or s not in ("test", "start") else f"npm {s}"
    cmds = {"install": f"{pm} install"}
    for key, names in (("dev", ("dev", "start", "serve")), ("test", ("test",)), ("lint", ("lint",)),
                       ("typecheck", ("typecheck", "type-check", "tsc")), ("format", ("format", "fmt")),
                       ("build", ("build",))):
        for n in names:
            if n in scripts and not (n == "test" and "no test specified" in scripts[n]):
                cmds[key] = run(n)
                break
    runner = "vitest" if "vitest" in deps else "jest" if "jest" in deps else None
    if runner == "vitest":
        cmds["test_related"] = "npx vitest related --run {files}"
    elif runner == "jest":
        cmds["test_related"] = "npx jest --findRelatedTests {files}"
    if "prettier" in deps or os.path.exists(os.path.join(root, "node_modules", ".bin", "prettier")):
        cmds["formatter"] = "npx --no-install prettier --write {file}"
    return "node", cmds


def _python(root):
    markers = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile")
    if not any(os.path.exists(os.path.join(root, m)) for m in markers):
        return None
    py = _read(os.path.join(root, "pyproject.toml"))
    cmds = {}
    if os.path.exists(os.path.join(root, "requirements.txt")):
        cmds["install"] = "pip install -r requirements.txt"
    elif py:
        cmds["install"] = "pip install -e ."
    has_tests = os.path.isdir(os.path.join(root, "tests")) or os.path.isdir(os.path.join(root, "test"))
    if has_tests or "pytest" in py:
        cmds["test"] = "pytest -q"
        cmds["test_related"] = "pytest -q {files}"
    ruff_cfg = "ruff" in py or os.path.exists(os.path.join(root, "ruff.toml")) or os.path.exists(os.path.join(root, ".ruff.toml"))
    if ruff_cfg or shutil.which("ruff"):
        cmds["lint"] = "ruff check ."
    if ruff_cfg:  # format only when the project opted in, never reformat unasked
        cmds["formatter"] = "ruff format {file}"
    elif "black" in py:
        cmds["formatter"] = "black -q {file}"
    if "mypy" in py:
        cmds["typecheck"] = "mypy ."
    for entry in ("main.py", "app.py", "manage.py"):
        if os.path.exists(os.path.join(root, entry)):
            cmds["dev"] = f"python {entry}" + (" runserver" if entry == "manage.py" else "")
            break
    return "python", cmds


def _go(root):
    if not os.path.exists(os.path.join(root, "go.mod")):
        return None
    return "go", {"dev": "go run .", "test": "go test ./...", "test_related": "go test {pkgs}",
                  "lint": "go vet ./...", "formatter": "gofmt -w {file}", "build": "go build ./..."}


def _rust(root):
    if not os.path.exists(os.path.join(root, "Cargo.toml")):
        return None
    return "rust", {"dev": "cargo run", "test": "cargo test", "lint": "cargo clippy",
                    "formatter": "rustfmt {file}", "build": "cargo build"}


def _make(root, cmds):
    mk = _read(os.path.join(root, "Makefile"))
    for target in ("dev", "run", "test", "lint", "format", "build"):
        if re.search(rf"^{target}:", mk, re.M):
            cmds.setdefault("dev" if target == "run" else target, f"make {target}")


def detect(root):
    """Return (stack name or 'static'/'unknown', {purpose: command})."""
    for fn in (_node, _python, _go, _rust):
        found = fn(root)
        if found:
            name, cmds = found
            _make(root, cmds)
            return name, cmds
    cmds = {}
    _make(root, cmds)
    if cmds:
        return "make", cmds
    if os.path.exists(os.path.join(root, "index.html")):
        return "static", {"dev": "open index.html in a browser (no build step)"}
    return "unknown", {}


LABELS = [("dev", "Run"), ("test", "Test"), ("test_related", "Test changed files"), ("lint", "Lint"),
          ("typecheck", "Typecheck"), ("format", "Format"), ("formatter", "Auto-format on edit (hook)"), ("build", "Build"), ("install", "Install")]


def commands_block(root):
    name, cmds = detect(root)
    if not cmds:
        return None
    lines = [START, f"## Commands (auto-detected: {name}; refreshed each session)"]
    lines += [f"- {label}: `{cmds[k]}`" for k, label in LABELS if k in cmds]
    return "\n".join(lines + [END])


def sync_claude_md(root):
    """Write or refresh the Commands block in CLAUDE.md. Returns the block (or None)."""
    block = commands_block(root)
    path = os.path.join(root, "CLAUDE.md")
    text = _read(path)
    if not block or not text:
        return block
    if START in text and END in text:
        new = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        anchor = text.find("\n## ", text.find("## Project map") + 1) if "## Project map" in text else -1
        new = (text[:anchor] + "\n\n" + block + text[anchor:]) if anchor > 0 else text.rstrip() + "\n\n" + block + "\n"
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    return block

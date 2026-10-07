#!/usr/bin/env python3
"""Enforce the core coding rules on code Claude writes (stdlib only, any project).

Checks only the lines an edit touched (whole file for a new file), so old code never blocks new work.
Silence one line with a reason: `kit-ignore: <reason>` (also honours `noqa` and `eslint-disable`).

  codecheck.py <file>            check a whole file; exit 1 with problems
  scan_secrets(text)             used by precommit.py on added lines
"""
import os, re, sys

MAX_FUNC_LINES = int(os.environ.get("CLAUDE_MAX_FUNC_LINES", "60"))
IGNORE = re.compile(r"kit-ignore|noqa|eslint-disable|nosec", re.I)

SECRETS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"\b(sk|rk)_live_[0-9a-zA-Z]{16,}", "Stripe live key"),
    (r"\bsk-(proj-|ant-)?[A-Za-z0-9_-]{20,}", "API secret key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "private key"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b", "Google API key"),
    (r"(?i)\b(password|passwd|secret|api_?key|access_?token|auth_?token|client_?secret)\b\s*[:=]\s*[\"'](?!\s*$)"
     r"(?!(?:changeme|example|placeholder|your[_-]|xxx|\*{3}|<|\$\{|\{\{|process\.env|os\.environ|test|dummy|fake))"
     r"[^\"'\s]{8,}[\"']", "hard-coded secret"),
]

PY = [
    (r"^\s*print\(", "debug print(); use logging (or kit-ignore if this is CLI output)"),
    (r"^\s*(breakpoint\(\)|import pdb|pdb\.set_trace\(\))", "debugger left in code"),
    (r"^\s*except\s*:", "bare except; catch a specific exception"),
    (r"\b(eval|exec)\(", "eval/exec on dynamic input is unsafe"),
    (r"\.execute\(\s*f[\"']|\.execute\([^)]*[\"']\s*(%|\+)\s*\w|\.execute\([^)]*\.format\(",
     "SQL built from strings; use query parameters"),
    (r"subprocess\.\w+\([^)]*shell\s*=\s*True[^)]*\bf[\"']", "shell=True with interpolated input"),
]
JS = [
    (r"\bconsole\.(log|debug|trace)\(", "console.log left in code; remove or use a logger"),
    (r"^\s*debugger;?\s*$", "debugger statement"),
    (r"\bcatch\s*(\([^)]*\))?\s*\{\s*\}", "empty catch swallows errors; handle or rethrow"),
    (r"\.innerHTML\s*[+]?=(?!\s*([\"'])[^\"'`$]*\1\s*;?\s*$)", "innerHTML with dynamic content (XSS); use textContent"),
    (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML (XSS risk); sanitise or avoid"),
    (r"\beval\(|new Function\(", "eval/new Function is unsafe"),
    (r"`\s*(SELECT|INSERT|UPDATE|DELETE)\b[^`]*\$\{", "SQL built with template strings; use query parameters"),
    (r"^\s*var\s+\w", "use const/let, not var"),
]
CODE_LIKE = re.compile(r"(;\s*$|\)\s*\{?\s*$|^\s*(def|class|return|import|from|if|for|while|const|let|var|function)\b|=\s*\S)")


def lang(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "py"
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"):
        return "js"
    return None


def is_test(path):
    b = os.path.basename(path)
    return b.startswith("test_") or "_test." in b or ".test." in b or ".spec." in b or "/tests/" in path.replace(os.sep, "/")


def scan_secrets(text, start=1):
    out = []
    for i, line in enumerate(text.splitlines(), start):
        if IGNORE.search(line):
            continue
        for rx, what in SECRETS:
            if re.search(rx, line):
                out.append((i, f"{what} in code; move it to an environment variable"))
                break
    return out


def functions(lines, kind):
    """Yield (start, end) line numbers (1-based) of function bodies."""
    if kind == "py":
        stack = []
        for i, l in enumerate(lines, 1):
            if not l.strip():
                continue
            ind = len(l) - len(l.lstrip())
            while stack and ind <= stack[-1][1]:
                s, _ = stack.pop()
                yield s, last
            if re.match(r"\s*(async\s+)?def\s", l):
                stack.append((i, ind))
            last = i
        for s, _ in stack:
            yield s, len(lines)
    else:
        for i, l in enumerate(lines):
            if re.search(r"\bfunction\b[^(]*\(|=>\s*\{\s*$|^\s*(async\s+)?\w+\s*\([^)]*\)\s*\{\s*$", l) and "{" in l:
                depth, j = 0, i
                while j < len(lines):
                    depth += lines[j].count("{") - lines[j].count("}")
                    if depth <= 0 and j > i or (depth <= 0 and j == i and "}" in lines[j]):
                        break
                    j += 1
                yield i + 1, min(j + 1, len(lines))


def check(path, text, region=None):
    """Return problems as 'line N: message'. region = (first, last) line numbers to check, None = all."""
    kind = lang(path)
    lines = text.splitlines()
    in_region = (lambda n: region[0] <= n <= region[1]) if region else (lambda n: True)
    problems = [(n, m) for n, m in scan_secrets(text) if in_region(n)]
    if kind:
        rules = PY if kind == "py" else JS
        test = is_test(path)
        for n, line in enumerate(lines, 1):
            if not in_region(n) or IGNORE.search(line):
                continue
            for rx, msg in rules:
                if test and ("print" in msg or "console" in msg):
                    continue
                if kind == "py" and "print" in msg and "__main__" in text:
                    continue  # CLI scripts may print
                if re.search(rx, line, re.I if "SQL" in msg else 0):
                    problems.append((n, msg))
        comment = "#" if kind == "py" else "//"
        run = []
        for n, line in enumerate(lines + [""], 1):
            s = line.strip()
            if s.startswith(comment) and CODE_LIKE.search(s[len(comment):]) and not IGNORE.search(s):
                run.append(n)
                continue
            if len(run) >= 3 and any(in_region(x) for x in run):
                problems.append((run[0], f"{len(run)} lines of commented-out code; delete it (git keeps history)"))
            run = []
        for s, e in functions(lines, kind):
            if e - s + 1 > MAX_FUNC_LINES and (region is None or not (e < region[0] or s > region[1])):
                if not IGNORE.search(lines[s - 1]):
                    problems.append((s, f"function is {e - s + 1} lines (limit {MAX_FUNC_LINES}); split it"))
    ext = os.path.splitext(path)[1].lower()
    if ext in (".css", ".scss", ".less", ".html", ".htm"):
        import webcheck
        found = webcheck.contrast(text) if ext in (".css", ".scss", ".less") else webcheck.page_weight(path, text)
        problems += [(n, m) for n, m in found if ext in (".html", ".htm") or in_region(n)]
    if not kind and ext not in (".md", ".txt", ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".env", ".ini", ".cfg", ".sh", ".sql", ""):
        return []
    seen, out = set(), []
    for n, m in sorted(problems):
        if (n, m) not in seen:
            seen.add((n, m))
            out.append(f"line {n}: {m}")
    return out


def region_for(text, new_string):
    """Line range of new_string inside the file, or None if it can't be located."""
    if not new_string:
        return None
    idx = text.find(new_string)
    if idx < 0:
        return None
    first = text.count("\n", 0, idx) + 1
    return first, first + new_string.count("\n")


if __name__ == "__main__":
    p = sys.argv[1]
    probs = check(p, open(p, encoding="utf-8", errors="replace").read())
    print("\n".join(probs) or "OK")
    sys.exit(1 if probs else 0)

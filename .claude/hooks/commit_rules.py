"""Commit-time rules (used by precommit.py): secrets, .env files, bug fixes need tests,
features need a CHANGELOG line, focused commits, and a review for sizeable changes."""
import os, re, subprocess
from _kit import ROOT, setting, state_dir, load, save, log_event

MAX_FILES = 25
MAX_LINES = 800
REVIEW_LINES = 80


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout


def commit_message(cmd):
    heredoc = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n\s*\1\b", cmd, re.S)
    if heredoc and re.search(r"(-[a-zA-Z]*m|--message|-F\s*-)", cmd):
        lines = [l.strip() for l in heredoc.group(2).splitlines() if l.strip()]
        return lines[0] if lines else ""
    m = re.search(r"(?:\s-[a-zA-Z]*m|--message)[ =]+(?:\"\$\(cat <<'?EOF'?\s*\n)?([\"']?)(.+?)(?:\1|\n|$)", cmd, re.S)
    return (m.group(2) if m else "").strip()


def files_and_diff(cmd):
    """What this commit will contain. Covers `git add ... && git commit` and `commit -a`."""
    stage_all = re.search(r"git\s+add\b", cmd) or re.search(r"\bcommit\b[^|;&]*\s-\w*a", cmd)
    if stage_all:
        names = git("diff", "HEAD", "--name-only").split() + git("ls-files", "--others", "--exclude-standard").split()
        diff = git("diff", "HEAD")
        for f in git("ls-files", "--others", "--exclude-standard").split():
            try:
                diff += "".join(f"+{l}\n" for l in open(os.path.join(ROOT, f), encoding="utf-8").read().splitlines())
            except (OSError, UnicodeDecodeError):
                pass
    else:
        names, diff = git("diff", "--cached", "--name-only").split(), git("diff", "--cached")
    return sorted(set(names)), diff


def problems(cmd, stamp, plan_open):
    from codecheck import scan_secrets
    from stack import is_test_file
    names, diff = files_and_diff(cmd)
    if not names:
        return None
    added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    secrets = scan_secrets(added)
    if secrets:
        return "Secrets in this commit: " + "; ".join(m for _, m in secrets[:5]) + ". Move them to environment variables."
    env_files = [n for n in names if re.search(r"(^|/)\.env(\.|$)", n) and not n.endswith((".example", ".sample", ".template"))]
    if env_files:
        return f"{env_files} would be committed; .env files hold secrets. Add them to .gitignore and commit a .env.example instead."
    msg = commit_message(cmd).lower()
    code = [n for n in names if re.search(r"\.(py|js|jsx|ts|tsx|mjs|cjs|go|rs|rb|php|java|kt|cs|vue|svelte)$", n)]
    has_tests = any(is_test_file(n) for n in names)
    if re.match(r"(fix|bugfix|hotfix)\b", msg) and code and not has_tests and not os.environ.get("CLAUDE_KIT_NO_TESTS"):
        from stack import detect
        if "test" in detect(ROOT)[1]:
            return "A bug-fix commit must include a test that would have caught the bug (no test file in this commit)."
    if re.match(r"feat\b", msg) and "CHANGELOG.md" not in names:
        return "A feature commit needs a one-line entry at the top of CHANGELOG.md (user-facing words)."
    changed = sum(1 for l in diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))
    state_file = os.path.join(state_dir(), "precommit.json")
    state = load(state_file, {})
    if (len(names) > MAX_FILES or changed > MAX_LINES) and state.get("size_warned") != stamp:
        save(state_file, {**state, "size_warned": stamp})
        return (f"This commit is large ({len(names)} files, {changed} lines). Split it into focused commits if it "
                "mixes unrelated changes; if it is one coherent change, run the same commit again.")
    code_lines = sum(1 for l in diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))
    if (not plan_open and code and code_lines >= REVIEW_LINES and setting("CLAUDE_COMMIT_REVIEW", 1)
            and state.get("review_asked") != stamp):
        save(state_file, {**load(state_file, {}), "review_asked": stamp})
        log_event("commit_rules", "review")
        return (f"Before committing {code_lines} changed lines: run the `code-review` skill (low effort) on this diff, "
                "check it against the Core coding rules (correct edge cases, readable, simple, secure, errors, tests), "
                "fix real findings, then run the same commit again.")
    return None

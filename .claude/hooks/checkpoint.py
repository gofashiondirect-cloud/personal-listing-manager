#!/usr/bin/env python3
"""Hidden checkpoints of the working tree, so any change can be undone.

Saved as refs/claude-checkpoints/<n> (never pushed, never on a branch, real index untouched).
  checkpoint.py create ["message"]   snapshot now (the Stop hook calls this after each turn)
  checkpoint.py list                 newest first
  checkpoint.py diff <n>             files changed since checkpoint n
  checkpoint.py restore <n>          put files back as they were at checkpoint n
                                     (the current state is checkpointed first, so restore is undoable)
"""
import os, subprocess, sys, tempfile, time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
PREFIX = "refs/claude-checkpoints/"
KEEP = 30


def git(*args, env=None, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30,
                       env={**os.environ, **(env or {})})
    if check and r.returncode:
        raise RuntimeError(r.stderr.strip() or f"git {args[0]} failed")
    return r.stdout.strip()


def refs():
    out = git("for-each-ref", "--sort=-refname", "--format=%(refname) %(objectname) %(contents:subject)", PREFIX)
    rows = []
    for line in out.splitlines():
        ref, sha, msg = (line.split(" ", 2) + [""])[:3]
        rows.append((int(ref[len(PREFIX):]), sha, msg))
    return sorted(rows, reverse=True)


def create(message="checkpoint"):
    """Snapshot tracked + untracked (non-ignored) files. Returns the number, or None if unchanged."""
    if git("rev-parse", "--is-inside-work-tree", check=False) != "true":
        return None
    fd, index = tempfile.mkstemp(prefix="claude-cp-index-")
    os.close(fd)
    os.remove(index)
    env = {"GIT_INDEX_FILE": index}
    try:
        head = git("rev-parse", "--verify", "-q", "HEAD", check=False)
        if head:
            git("read-tree", "HEAD", env=env)
        git("add", "-A", env=env)
        tree = git("write-tree", env=env)
    finally:
        if os.path.exists(index):
            os.remove(index)
    existing = refs()
    if existing and git("rev-parse", f"{existing[0][1]}^{{tree}}") == tree:
        return None  # nothing changed since the last checkpoint
    if head and git("rev-parse", "HEAD^{tree}") == tree and not existing:
        return None  # clean tree, nothing worth saving yet
    args = ["commit-tree", tree, "-m", f"{time.strftime('%Y-%m-%d %H:%M')} {message}"]
    if head:
        args[2:2] = ["-p", head]
    sha = git(*args)
    n = (existing[0][0] + 1) if existing else 1
    git("update-ref", f"{PREFIX}{n:06d}", sha)
    for old_n, _, _ in existing[KEEP - 1:]:
        git("update-ref", "-d", f"{PREFIX}{old_n:06d}", check=False)
    return n


def find(n):
    for num, sha, msg in refs():
        if num == int(n):
            return sha
    sys.exit(f"No checkpoint {n}. Run: checkpoint.py list")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "create":
        n = create(sys.argv[2] if len(sys.argv) > 2 else "checkpoint")
        print(f"checkpoint {n}" if n else "no changes since last checkpoint")
    elif cmd == "list":
        rows = refs()
        print("\n".join(f"{n:4}  {msg}" for n, _, msg in rows[:15]) or "no checkpoints yet")
    elif cmd == "diff" and len(sys.argv) > 2:
        print(git("diff", "--stat", find(sys.argv[2])) or "no differences")
    elif cmd == "restore" and len(sys.argv) > 2:
        sha = find(sys.argv[2])
        saved = create(f"before restoring checkpoint {sys.argv[2]}")
        git("restore", f"--source={sha}", "--worktree", "--", ".")
        added = git("diff", "--name-only", "--diff-filter=A", sha, check=False)
        print(f"Restored files to checkpoint {sys.argv[2]}."
              + (f" Previous state saved as checkpoint {saved}." if saved else ""))
        if added:
            print("Files created after that checkpoint were left in place:\n" + added)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

"""Shared helpers for the claude-kit hooks (stdlib only)."""
import json, os, re, sys, tempfile, time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
HOOKS = os.path.dirname(os.path.abspath(__file__))
PY = f'"{sys.executable}"'


def state_dir():
    """Durable state (usage, task log). Relative CLAUDE_KIT_STATE_DIR = inside the project."""
    d = os.environ.get("CLAUDE_KIT_STATE_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "state")
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    os.makedirs(d, exist_ok=True)
    return d


def session_path(session_id, name):
    """Throwaway per-session state in the temp dir."""
    d = os.path.join(tempfile.gettempdir(), "claude-kit", session_id or "unknown")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def emit(obj):
    print(json.dumps(obj))  # kit-ignore: stdout is the hook protocol


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def project_name():
    return os.path.basename(os.path.normpath(ROOT))


def today():
    return time.strftime("%Y-%m-%d")


def tuning():
    return load(os.path.join(state_dir(), "tuning.json"), {})


def setting(name, default):
    """Env var wins, then the auto-tuned value (tune.py), then the default."""
    if name in os.environ:
        return type(default)(os.environ[name])
    return type(default)(tuning().get(name, default))


def log_event(hook, kind, key="", **extra):
    """Append one guard/trim event; tune.py reads these to adjust limits."""
    try:
        path = os.path.join(state_dir(), "events.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"date": today(), "hook": hook, "kind": kind, "key": key, **extra}) + "\n")
        if os.path.getsize(path) > 400_000:  # keep the newest ~2000 events
            lines = open(path, encoding="utf-8").readlines()[-2000:]
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
    except OSError:
        pass


def safe_run(main):
    """A hook must never break the session: log the error and exit quietly."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(os.path.join(state_dir(), "hook-errors.log"), "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M')} {os.path.basename(sys.argv[0])}: "
                        f"{type(e).__name__}: {e}\n")
        except OSError:
            pass

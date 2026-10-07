#!/usr/bin/env python3
"""Start the project's dev/run command briefly and confirm it boots without crashing.

  smoke.py [seconds]   exit 0 = booted (or still running healthy), 1 = crashed/errored
Passes as soon as the output shows the app is ready/listening; fails if the process exits
with an error or prints a crash. The process is always stopped afterwards.
"""
import os, re, signal, subprocess, sys, threading, time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
READY = re.compile(r"listening|ready|running (at|on)|started|localhost:\d+|127\.0\.0\.1:\d+|compiled successfully", re.I)
CRASH = re.compile(r"traceback|unhandled|uncaught|exception|error:|cannot find module|syntaxerror|eaddrinuse|panic:", re.I)


def smoke(cmd, seconds=25):
    """Returns (ok, last output lines)."""
    proc = subprocess.Popen(cmd, shell=True, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace", start_new_session=True,
                            env={**os.environ, "CI": "1", "BROWSER": "none"})
    lines = []
    reader = threading.Thread(target=lambda: lines.extend(proc.stdout), daemon=True)
    reader.start()
    ok, deadline, seen = None, time.time() + seconds, 0
    try:
        while time.time() < deadline and ok is None:
            time.sleep(0.3)
            new = "".join(lines[seen:])
            seen = len(lines)
            if CRASH.search(new):
                ok = False
            elif READY.search(new):
                ok = True
            elif proc.poll() is not None:
                reader.join(2)
                ok = proc.returncode == 0 and not CRASH.search("".join(lines))
        if ok is None:
            ok = not CRASH.search("".join(lines))  # still running after the window with no errors
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(5)
            except Exception:
                os.killpg(proc.pid, signal.SIGKILL)
    return ok, "".join(lines[-30:]).strip()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from stack import detect
    cmd = detect(ROOT)[1].get("dev")
    if not cmd or " " in cmd and cmd.startswith("open "):
        sys.exit(print("no run command to smoke-test") or 0)
    ok, tail = smoke(cmd, int(sys.argv[1]) if len(sys.argv) > 1 else 25)
    print(("booted OK: " if ok else "FAILED to boot: ") + cmd + "\n" + tail)
    sys.exit(0 if ok else 1)

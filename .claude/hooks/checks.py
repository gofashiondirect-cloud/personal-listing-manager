"""Run the heavy end-of-turn checks fast: in parallel, timed, and deferred to commit when slow.

- Every check is timed and logged; tune.py moves checks whose typical run exceeds the budget
  (CLAUDE_CHECK_BUDGET_MS, default 15000) to commit time, and back when they get fast again.
- Fast mode (say "fast mode on" in a message, or set CLAUDE_KIT_FAST=1) defers all heavy checks
  to commit for the session; "fast mode off" restores them.
"""
import os, time
from concurrent.futures import ThreadPoolExecutor
from _kit import setting, tuning, session_path, load, save, log_event

HEAVY = ("tests", "links", "boot", "visual")


def fast_mode(session_id):
    if setting("CLAUDE_KIT_FAST", 0):
        return True
    return bool(load(session_path(session_id, "fast.json"), {}).get("on"))


def set_fast_mode(session_id, on):
    save(session_path(session_id, "fast.json"), {"on": bool(on)})


def deferred():
    return set(tuning().get("deferred_checks", []))


def timed(name, fn, *args):
    start = time.time()
    try:
        return fn(*args)
    finally:
        ms = int((time.time() - start) * 1000)
        if ms > 50:  # skipped checks return instantly; don't let them skew the timing
            log_event("timing", "check", name, ms=ms)


def run(checks, *args):
    """checks: {name: fn}. Runs them in parallel; returns the first failure message (in given order)."""
    if not checks:
        return None
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = {name: pool.submit(timed, name, fn, *args) for name, fn in checks.items()}
        results = {}
        for name, fut in futures.items():
            try:
                results[name] = fut.result()
            except Exception as e:
                log_event("checks", "error", name, error=str(e)[:200])
                results[name] = None
    return next((results[n] for n in checks if results[n]), None)


def stop_checks(session_id):
    """Which heavy checks run at the end of a turn (the rest run at commit)."""
    if fast_mode(session_id):
        return set()
    return set(HEAVY) - deferred()

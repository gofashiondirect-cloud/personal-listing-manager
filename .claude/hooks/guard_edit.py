#!/usr/bin/env python3
"""PreToolUse(Edit|MultiEdit): before changing existing code that has no test, ask for a lock-in test.

A lock-in (characterization) test records what the code does today, so a change that breaks it
shows up immediately. Asked once per file per session; editing again is then allowed.
Only applies to projects with a test command. Disable with CLAUDE_LOCKIN_TESTS=0.
"""
import os
from _kit import setting, safe_run, ROOT, read_input, session_path, load, save, emit, log_event


def main():
    data = read_input()
    path = (data.get("tool_input") or {}).get("file_path")
    if not setting("CLAUDE_LOCKIN_TESTS", 1) or not path or not os.path.isfile(path):
        return  # new files need no lock-in
    from stack import detect, is_test_file, tests_for, SRC_EXT
    rel = os.path.relpath(path, ROOT)
    if rel.startswith((".claude", "..")) or not rel.endswith(SRC_EXT) or is_test_file(rel):
        return
    cmds = detect(ROOT)[1]
    if "test" not in cmds or tests_for(ROOT, rel):
        return
    state_file = session_path(data.get("session_id"), "lockin.json")
    asked = load(state_file, [])
    if rel in asked:
        log_event("guard_edit", "override", "lockin")
        return
    save(state_file, asked + [rel])
    log_event("guard_edit", "deny", "lockin")
    stem = os.path.splitext(os.path.basename(rel))[0]
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
          "permissionDecisionReason": (
              f"{rel} has no tests yet. First write a small lock-in test for the functions you are about "
              f"to change (e.g. test_{stem} / {stem}.test next to the project's other tests) that asserts what "
              f"they return today, run it (`{cmds['test']}`), then make your edit. If this file truly can't "
              "be tested (pure config, UI markup), just retry the edit.")}})


if __name__ == "__main__":
    safe_run(main)

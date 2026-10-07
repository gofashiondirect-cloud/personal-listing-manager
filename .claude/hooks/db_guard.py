#!/usr/bin/env python3
"""Database safety.

PreToolUse(Bash): destructive database commands (DROP, TRUNCATE, DELETE/UPDATE without WHERE,
  migrate reset, db:drop, flush, downgrade base, --accept-data-loss ...) need the user's OK.
PreToolUse(Edit|MultiEdit|Write): migrations that are already committed must not be edited;
  create a new migration instead (asked once per file per session).
"""
import os, re, subprocess
from _kit import safe_run, ROOT, read_input, session_path, load, save, emit, log_event

DANGER = [
    (r"\bdrop\s+(table|database|schema)\b", "drops a table/database"),
    (r"\btruncate\s+(table\s+)?\w+", "empties a table"),
    (r"\bdelete\s+from\s+[\w.\"`]+\s*(;|$|\"|')", "deletes every row (no WHERE)"),
    (r"\bupdate\s+[\w.\"`]+\s+set\b(?![^;]*\bwhere\b)", "updates every row (no WHERE)"),
    (r"prisma\s+migrate\s+reset|prisma\s+db\s+push\b.*--(force-reset|accept-data-loss)", "resets the Prisma database"),
    (r"\b(rails|rake)\s+db:(drop|reset|schema:load)", "drops/reloads the Rails database"),
    (r"manage\.py\s+(flush|reset_db|sqlflush)", "wipes the Django database"),
    (r"alembic\s+downgrade\s+(base|-\d+)", "rolls back migrations (may drop data)"),
    (r"knex\s+migrate:rollback|sequelize\s+db:migrate:undo(:all)?|typeorm\s+schema:drop", "rolls back/drops schema"),
    (r"\bdropdb\b|\bmongo\w*\b.*dropDatabase|\bredis-cli\b.*\bflushall\b", "deletes a whole database"),
]
MIGRATION_DIRS = ("migrations/", "prisma/migrations/", "db/migrate/", "alembic/versions/", "supabase/migrations/")


def bash(data):
    cmd = (data.get("tool_input") or {}).get("command") or ""
    low = cmd.lower()
    for rx, what in DANGER:
        if re.search(rx, low, re.I | re.M):
            log_event("db_guard", "ask", what)
            return emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                         "permissionDecisionReason": f"This command {what}. Only approve if this is a "
                                                     "throwaway/test database or you have a backup."}})


def committed(rel):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True, timeout=5)
    return r.returncode == 0


def edit(data):
    path = (data.get("tool_input") or {}).get("file_path") or ""
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/") if path else ""
    if not any(d in "/" + rel for d in ("/" + m for m in MIGRATION_DIRS)) or not os.path.exists(path):
        return
    if not committed(rel):
        return  # a migration you are still writing is fine to edit
    state_file = session_path(data.get("session_id"), "migration-edit.json")
    asked = load(state_file, [])
    if rel in asked:
        return
    save(state_file, asked + [rel])
    log_event("db_guard", "deny", "migration-edit")
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
          "permissionDecisionReason": f"{rel} is a committed migration and may already be applied to real "
                                      "databases; editing it won't change them and can corrupt history. Create a "
                                      "new migration for the change instead. (Retry only if it was never deployed.)"}})


def main():
    data = read_input()
    (bash if data.get("tool_name") == "Bash" else edit)(data)


if __name__ == "__main__":
    safe_run(main)

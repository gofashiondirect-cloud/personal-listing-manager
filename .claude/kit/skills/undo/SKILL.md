---
name: undo
description: Undo recent changes by restoring an automatic checkpoint. Use when the user says undo, revert, roll back, go back, "that broke it", or wants the code as it was before a change.
---

# Undo with checkpoints

The Stop hook saves a hidden checkpoint of all files after every turn (`refs/claude-checkpoints/*`, never pushed, never on a branch).

1. List them: `python3 .claude/hooks/checkpoint.py list` (newest first, with times).
2. Pick the one from before the unwanted change. If unsure, check `python3 .claude/hooks/checkpoint.py diff <n>`.
3. Restore: `python3 .claude/hooks/checkpoint.py restore <n>`. The current state is checkpointed first, so this is itself undoable.
4. Files created after that checkpoint are listed but left in place; delete them only if the user wants them gone.
5. Tell the user in one line which point you restored to and what changed back.

For changes that were already committed, prefer `git revert <commit>` over restoring.

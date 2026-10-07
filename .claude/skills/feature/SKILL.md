---
name: feature
description: Add or change a feature end to end, fast and safely. Use when the user asks to add, build, change or extend a feature ("/feature add dark mode", "add a search box", "change checkout to support coupons").
---

# Feature workflow

1. **Branch.** If on `main`/`master` and the session hasn't specified a branch, `git switch -c feature/<short-slug>`.
2. **Done means.** One line: what the user will see or be able to do, and which check proves it.
3. **Find the pattern.** Grep for the closest existing feature (same kind of page, endpoint, component, job). Read only that example and the files you will change. Match its structure, naming and style.
4. **Plan.** If it touches more than ~3 files, write a 3-6 line plan. Otherwise skip.
5. **Lock in, then build.** If a file you'll change has no tests, first add a small test of what it does today. Then build in small steps. One coherent change at a time. Hooks auto-format and syntax-check each edit and list callers if you change a function's signature; update them all.
6. **Test.** Add or update a test next to the pattern's tests when the project has tests. Run only related tests (see `## Commands` in CLAUDE.md). The Stop hook re-runs them before you finish.
7. **Check it runs and looks right.** If you changed the database schema, create a migration and apply it to the dev database. Review the Stop hook's visual diff for unintended changes. Then, if there is a Run command and the change is user-visible, start it briefly or use the `run` skill to confirm.
8. **Log it.** Add one line under today's date at the top of `CHANGELOG.md` (create it if missing): `- <what changed, user-facing words>`.
9. **Commit.** `git add` the changed files and commit with `feat: <summary>` (the full suite runs first; fix anything it finds). Don't push unless the user or session asks.
10. **Report.** 2-3 lines: what was added, how to try it, anything left open.

Undo at any point: use the `undo` skill (hidden checkpoints are saved after every turn).

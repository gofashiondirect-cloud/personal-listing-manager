## Token discipline
- Read only what you need: grep, or Read with offset/limit, instead of whole files.
- Pipe long command output through `head`, `tail` or `grep`.
- For wide codebase searches, use a subagent and keep only its conclusion.
- Don't re-read a file you just edited; don't repeat unchanged code in replies.
- Keep replies short: result first, details only when asked.
- Prefer one clarifying question over exploring the whole repo on a guess.
- Use an existing skill when one matches the task instead of working the steps out again.
- Subagents: give them a narrow question and ask for a short answer (conclusion + file:line refs).
- Trimmed results point to a full-output file: grep that file rather than re-running the command.

## Working style
- Before a non-trivial task, state in one line what "done" means (e.g. "done when `npm test cart` passes and the total updates"), then stop when it is met.
- If a task will touch more than ~3 files or has several reasonable approaches, write a 3-6 line plan first and follow it.
- Run only the tests related to what changed (a single file or `-k` filter); run the full suite only before committing a larger change.
- Keep files small and well named (guideline: under ~400 lines); split when a file grows past that and the task allows it.
- When a message includes "Likely relevant files", check those first before searching.

## Shipping features fast
- Use the `feature` skill for any add/change-a-feature request, and the `undo` skill to roll back.
- Before writing something new, find the closest existing example in the project and follow its structure, naming and style.
- Work on a `feature/<slug>` branch unless the session already names a branch; keep the main branch working.
- Use the commands in `## Commands` (auto-detected) instead of guessing how to run, test or build.
- Record each finished feature as one user-facing line at the top of `CHANGELOG.md`.
- Repeated kinds of feature (new page, endpoint, component) become scaffold skills via the skill rule below.

## Not breaking what works (hooks enforce these)
- Before changing existing code that has no test, write a small lock-in test of its current behaviour, then change it.
- When you rename a function or change its parameters, update every caller the hook lists.
- `git commit` runs the full test suite (and link check); a failing commit means something else depends on your change.
- After code changes the app is started briefly; after HTML changes, links, anchors and redirects are checked.
- After UI changes, pages are screenshotted before/after; look at the red diff images and fix any change the user didn't ask for. For apps with a dev server, list pages in `.claude/visual/pages.json` and run `visual.py accept` after intended redesigns.
- Database: every schema change gets a new migration (see `## Commands`); never edit a committed migration; destructive DB commands need the user's OK, and migrations are tried on a dev/copy database first.
- CI (`.github/workflows/`) runs the same checks on every push; keep it green.
- Speed: end-of-turn checks run in parallel and only on what changed; checks that are slow for this project move to commit time automatically. When the user says "fast mode on", heavy checks wait until `git commit`; "fast mode off" restores them.

## Self-improvement (hooks enforce the first three)
- Keep the `## Project map` in CLAUDE.md current when adding top-level files or folders.
- When asked by the Stop hook, record a task label; reuse an existing label for the same kind of task.
- When a task repeats, write a skill: `.claude/skills/<name>/SKILL.md` with `name` and a `description` saying when to use it, then the concise, tested steps. Keep SKILL.md under ~60 lines; put long reference material in separate files in the skill folder and point to them.
- If a read turned out to be useless bulk (generated, vendored, data, fixtures), add a `Read(...)` deny rule for it to `.claude/settings.json`.
- When fixing a bug in a project that has tests, add a test that would have caught it.
- If a hook's check fails after an edit, fix it before continuing.
- Keep this file under ~150 lines. Rules that only matter inside one folder go in a `CLAUDE.md` in that folder (it loads only when working there).

## When compacting
Keep: the user's goal, decisions made, open tasks, files changed and key file:line references, and failing commands with their error lines.
Drop: file contents, full logs, search results, and exploration that led nowhere.

## Writing routines, scheduled jobs and automations
- Use the cheapest model that does the job (Haiku or Sonnet; Opus only if the job needs hard reasoning).
- Start with a quick exit: if nothing changed since the last run (no new commits, files, messages or data), stop immediately.
- Pick the lowest frequency that still meets the need (daily over hourly, weekly over daily).
- For one-shot scripted jobs, use `claude -p "<task>"` (no chat history) instead of an interactive session.
- Keep prompts self-contained and short; point to files instead of pasting their contents.

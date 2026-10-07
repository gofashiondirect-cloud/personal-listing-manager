# Project rules for Claude

## Project map
Static marketing site for Personal Listing Manager. No build step, no JavaScript, no tests.
- `index.html`: landing page
- `privacy-terms.html`: privacy policy and terms
- `styles.css`: all styling, shared by both pages
- `assets/`: images (SVG)
Preview by opening `index.html` in a browser. Keep this map updated when files are added.

## Kit state
`.claude/state/` holds the task log and usage log; commit it with your work so later sessions and the weekly review can use it.

<!-- claude-kit:start -->
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
<!-- claude-kit:end -->

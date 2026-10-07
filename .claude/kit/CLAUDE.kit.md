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

## Core coding rules
- Correct first: handle normal, empty, invalid, error and slow cases; never break existing behaviour.
- Readable: clear names, small single-purpose functions, follow the project's existing style; comments say why, not what.
- Simple: build only what is needed now; reuse instead of copy-paste, but no premature abstractions; platform built-ins before new libraries.
- Secure (OWASP): validate all external input; parameterised queries only; escape user content in pages; check permissions on every request for the specific object; no secrets in code.
- Errors: catch specific errors, show users a helpful message, log the details; never swallow errors silently.
- Tested: test behaviour, not internals; fast, independent tests; every bug fix gets a test that would have caught it.
- User-facing: accessible (labels, alt, keyboard, contrast), fast (optimised images, no blocking scripts), works on mobile.
- Clean: no dead code, debug prints or commented-out blocks; one formatter and linter per project; pinned dependencies with committed lockfiles.
- Small, focused commits with clear messages; one change at a time so problems are easy to find and undo.
- Well designed, not just well coded: follow `.claude/standards/architecture.md` for structure and `ux.md` for anything users see.
- Keep README (run/test/deploy), CHANGELOG and CLAUDE.md conventions current when behaviour changes.
- Enforced by hooks: edits are checked for debug prints, commented-out code, long functions (>60 lines), unsafe SQL/HTML/eval, empty or bare catches, secrets and low colour contrast; commits block on secrets, `.env` files, `fix:` without a test, `feat:` without a CHANGELOG line, and get a review step when large. Intended exceptions: add `kit-ignore: <reason>` on the line.

## Plan, research, prove
- Anything bigger than a one-line fix starts with the `plan` skill: plan in `.claude/plans/current.md`, researched against (in order) the request, this project and `## Preferences`, saved notes in `.claude/research/`, official docs for the installed versions, then the standards in `.claude/standards/`.
- Every plan item gets ticked only with proof (`- proof: test name / file:line / check result`); the Stop hook blocks finishing until it is.
- Before committing: re-check the request and Done-when, run the `code-review` skill on the diff, tick Review.
- Save reusable research to `.claude/research/<topic>.md` (date + versions); reuse notes under ~90 days old instead of searching again.

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

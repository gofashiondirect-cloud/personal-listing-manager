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

## Self-improvement (hooks enforce the first three)
- Keep the `## Project map` in CLAUDE.md current when adding top-level files or folders.
- When asked by the Stop hook, record a task label; reuse an existing label for the same kind of task.
- When a task repeats, write a skill: `.claude/skills/<name>/SKILL.md` with `name` and a `description` saying when to use it, then the concise, tested steps.
- If a read turned out to be useless bulk (generated, vendored, data, fixtures), add a `Read(...)` deny rule for it to `.claude/settings.json`.
- When fixing a bug in a project that has tests, add a test that would have caught it.
- If a hook's check fails after an edit, fix it before continuing.
- Keep this file under ~150 lines. Rules that only matter inside one folder go in a `CLAUDE.md` in that folder (it loads only when working there).

## When compacting
Keep: the user's goal, decisions made, open tasks, files changed and key file:line references, and failing commands with their error lines.
Drop: file contents, full logs, search results, and exploration that led nowhere.

## Building apps that call the Claude API
- Put stable content (system prompt, tool definitions, reference docs) first and mark it for prompt caching.
- Pick the cheapest model that meets the quality bar: Haiku for classification, extraction and routing; Sonnet for general work; Opus only for hard reasoning.
- Always set `max_tokens`; ask for concise or structured (JSON) output.
- Use the Message Batches API for non-urgent bulk jobs.
- Don't resend whole histories or large documents every call: trim, summarise, or retrieve only relevant chunks.
- Log token usage per request so costs are visible.

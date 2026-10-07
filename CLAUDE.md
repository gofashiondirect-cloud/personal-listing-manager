# Project rules for Claude

## Project map
Static marketing site for Personal Listing Manager. No build step, no JavaScript, no tests.
- `index.html`: landing page
- `privacy-terms.html`: privacy policy and terms
- `styles.css`: all styling, shared by both pages
- `assets/`: images (SVG)
Preview by opening `index.html` in a browser. Keep this map updated when files are added.

## Token discipline
- Read only what you need: use line ranges (offset/limit) or grep instead of whole files.
- Pipe long command output through `head`, `tail` or `grep`; never dump full logs.
- For wide codebase searches, use a subagent and keep only its conclusion.
- Don't re-read a file you just edited; don't repeat unchanged code in replies.
- Keep replies short: result first, details only when asked.
- Ask one clarifying question rather than exploring the whole repo on a guess.
- Never read dependency, build or log folders (node_modules, dist, build, .venv, *.log).

## Cost
- Default model is Sonnet (set in `.claude/settings.json`). Switch to Opus with `/model` only for hard design or debugging work.
- Subagents run on Haiku; give them narrow search tasks, not open-ended ones.
- If a section here grows past a few lines (deploy steps, style guide), move it into a skill under `.claude/skills/` so it loads only when needed.

## Session hygiene (for the user)
- One task per session; start a new chat for an unrelated task.
- Long session? Type `/compact` (optionally `/compact keep <what matters>`).
- Check what fills context with `/context`.
- Turn off connectors this project doesn't use (claude.ai Settings > Connectors, or `/mcp` locally); each one adds tool definitions to every request.

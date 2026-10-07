# Project rules for Claude

## Token discipline
- Read only what you need: use line ranges (offset/limit) or grep instead of whole files.
- Pipe long command output through `head`, `tail` or `grep`; never dump full logs.
- For wide codebase searches, use a subagent and keep only its conclusion.
- Don't re-read a file you just edited; don't repeat unchanged code in replies.
- Keep replies short: result first, details only when asked.
- Ask one clarifying question rather than exploring the whole repo on a guess.
- Never read dependency, build or log folders (node_modules, dist, build, .venv, *.log).

## Session hygiene (for the user)
- One task per session; start a new chat for an unrelated task.
- Long session? Type `/compact` (optionally `/compact keep <what matters>`).
- Check what fills context with `/context`.

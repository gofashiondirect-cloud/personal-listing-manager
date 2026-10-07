# Python standard (sources: PEP 8, PEP 257, PEP 484, Python docs, OWASP)
- PEP 8 style (enforced by ruff/black when configured); clear names, no single-letter names except loop indexes.
- Type hints on public functions; docstrings on public modules, classes and functions.
- Small functions with one job; no module-level side effects beyond constants.
- Catch specific exceptions, never bare `except:`; log or re-raise with context.
- Use `pathlib`, `with` for files and connections, f-strings for formatting.
- Validate external input; parameterised SQL only (never f-strings into queries).
- Secrets from environment variables, never in code; pin dependencies.
- Tests with pytest next to the existing tests; each bug fix gets a regression test.

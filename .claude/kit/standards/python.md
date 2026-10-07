# Python standard (sources: PEP 8, PEP 257, PEP 484, Python docs, OWASP)
- PY-01 PEP 8 style (enforced by ruff/black when configured); clear names, no single-letter names except loop indexes.
- PY-02 Type hints on public functions; docstrings on public modules, classes and functions.
- PY-03 Small functions with one job; no module-level side effects beyond constants.
- PY-04 Catch specific exceptions, never bare `except:`; log or re-raise with context.
- PY-05 Use `pathlib`, `with` for files and connections, f-strings for formatting.
- PY-06 Validate external input; parameterised SQL only (never f-strings into queries).
- PY-07 Secrets from environment variables, never in code; pin dependencies.
- PY-08 Tests with pytest next to the existing tests; each bug fix gets a regression test.

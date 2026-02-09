# Repository Guidelines

## Project Structure & Module Organization
- `src/chorelib/` holds the library code. Core modules include `ruledef.py` (DSL and decorators), `depgraph.py` (dependency graph), `deprunner.py` (async execution), and `depmain.py` (CLI entry point).
- `tests/` contains pytest-based tests (e.g., `test_ruledef.py`, `test_runner.py`).
- `samples/` provides runnable examples (`samples/build-c/`, `samples/sqlite/`).
- Root files: `pyproject.toml` (build/config), `README.md` (user docs), `uv.lock` (locked deps).

## Build, Test, and Development Commands
Use `uv` for local workflows:
- `uv sync` — install/sync dev dependencies.
- `uv run pytest tests` — run the full test suite.
- `uv run pytest tests/test_ruledef.py -k "name"` — run a single test (substring match).
- `uv run ruff check src/ tests/` — lint.
- `uv run ruff check --fix src/ tests/` — lint with autofix.
- `uv run ruff format src/ tests/` — format.

## Coding Style & Naming Conventions
- Language: Python; target runtime is `>=3.10` per `pyproject.toml` (development commonly uses newer 3.x).
- Line length: 99.
- Linting/formatting: Ruff (`E4`, `E7`, `E9`, `F`, `I`).
- Naming: modules and functions use `snake_case`; tests follow `test_*.py` and `test_*` function names.
- Write all code and docs in English.

## Testing Guidelines
- Framework: pytest.
- Place tests in `tests/` and keep file names `test_*.py`.
- Prefer focused unit tests; add new cases near related modules (e.g., `tests/test_utils.py`).

## Commit & Pull Request Guidelines
- Git history shows no enforced commit convention. Use concise, imperative summaries (e.g., `Add mtime override docs`).
- PRs should include: a brief summary, relevant test results, and links to issues if applicable. Include screenshots only for user-facing behavior.

## Configuration & Data Notes
- Example data files (`sample.db`, `tutorial.db`) are tracked for demos; avoid mutating them in tests.

# Repository Guidelines

## Project Structure & Module Organization
- `src/invokeai_py_client/` — core package (client, models, exceptions) with submodules `board/`, `workflow/`, `quick/`, and `ivk_fields/`.
- `tests/` — pytest suite covering workflows, images, boards, and quick APIs.
- `examples/` — runnable usage patterns and pipelines.
- `docs/` — MkDocs site (developer/user guides, API reference).
- `scripts/` — helper scripts for local tasks.

## Build, Test, and Development Commands
Prefer Pixi for a consistent toolchain:
- Setup: `pixi run dev-setup` (editable install + pre-commit).
- Test: `pixi run test` | Coverage: `pixi run test-cov`.
- Lint: `pixi run lint` | Autofix: `pixi run lint-fix` | Format: `pixi run format`.
- Type check: `pixi run typecheck` | All checks: `pixi run quality`.
- Docs: `pixi run docs-serve` (preview) | `pixi run docs-build`.
Alternative: `pip install -e .[dev,test,docs]` then `pytest`.

## Coding Style & Naming Conventions
- Python ≥ 3.11, 4-space indentation, line length 88, double quotes.
- Use Ruff for linting/formatting; keep imports clean; no unused code.
- Type hints required for public APIs (mypy strict mode).
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.

## Testing Guidelines
- Framework: pytest with markers `unit`, `integration`, `slow`.
- Location/naming: `tests/`, files `test_*.py`, functions `test_*`.
- Run locally with `pixi run test` and add coverage via `pixi run test-cov`.
- Add focused unit tests for new logic; mark slow/integration appropriately.

## Architecture Overview
- This client targets InvokeAI REST APIs and exported GUI workflow JSON; it does not re-implement the UI.
- Maintain compatibility with upstream graph/fields: avoid structural edits to workflow JSON; treat Form-exposed fields as inputs.
- Upstream references: `context/hints/invokeai-kb/` (KB) and `context/refcode/InvokeAI/` (source mirror).
- On upstream API changes, update models, docs, and add round-trip tests for workflows and boards.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat:`, `fix:`, `ci:`, `chore:`).
  Example: `feat(client): add async job polling`.
- PRs must include: clear description, linked issues, tests, and docs updates when relevant.
- Ensure `pixi run quality` passes before requesting review. CI runs ruff, mypy, and pytest on multiple OS/Python versions.

## Security & Configuration Tips
- Do not hardcode credentials or URLs; pass the base URL (e.g., `http://localhost:9090`) via config/env.
- Avoid committing large binaries or sensitive data; respect `.gitignore`.
- Validate inputs from external services and handle network errors explicitly.

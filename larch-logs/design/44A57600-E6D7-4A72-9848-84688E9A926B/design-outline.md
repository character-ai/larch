## Proposed Design Outline

### Goals
- Ship two AST linters under `python/`: subprocess-via-Runner and env-via-config-constant.
- Invoke both in CI: the `python-lint` job runs them via `make py-lint-main`; the `python-tests` job runs their harnesses via `make py-test`. Pre-commit runs them locally too.
- Baseline ratchet so only new violations fail; grandfather every current violation now and edit no existing module logic.

### Non-goals
- Fixing existing violations (routing subprocess through Runner, swapping env literals); deferred to follow-ups.
- Flagging test files, `proc.py` (the seam), or env vars with no matching `config.ENV_*` constant.
- New CLI surfaces beyond two `python/cli.py lint <name>` verbs.
- Editing `.github/workflows/ci.yaml`: existing `python-lint` and `python-tests` jobs already invoke `py-lint-main` and `py-test`, so wiring into those Makefile targets is sufficient.
- Auditing or re-wiring other existing linters' CI coverage (out of scope for this issue).

### Approach sketch
- Mirror `lint_keyword_only.py`: baseline JSON (`--write` regen) + optional exemptions JSON (with `reason`) + inline `# lint-<name>: ok <reason>` pragma.
- Linter 1: flag `subprocess.*` calls in `python/` library modules; exclude `proc.py`, tests, and exemptions; baseline the current ~57.
- Linter 2: build a `config.py` map of `ENV_*: Final = "VALUE"`; flag `os.environ.get("X")` / `os.environ["X"]` whose literal matches a VALUE, outside `config.py`; exempt `*_SH` and no-constant vars.
- Reuse `lint_common` helpers; register both as `python/cli.py lint <name>`.

### Surfaces in scope
- `python/lint_subprocess_via_runner.py`, `python/lint_env_via_config_constant.py` (+ `test_lint_*.py` harnesses).
- `python/*-baseline.json` (+ optional `*-exemptions.json`), `python/cli.py` dispatch, `Makefile`, `.pre-commit-config.yaml`, `docs/linting.md`.

### Open questions
- None.

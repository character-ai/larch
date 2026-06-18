# CI-fix continuation — issue #4634 / PR #4696

The original `/implement --merge 4634` run (this run-log) ended before CI was
green. This addendum records the follow-up session that resumed the same PR
from a separate clone, fixed the red CI checks, and drove it to merge.

## Starting state

PR #4696 (`sergey-zhupanov/implementing-sh-to-py-g5-design-step-2-d-4634`) was
open with 8 failing checks: `agent-lint`, `lint`, `lint-local`, `python-lint`,
`python-lint-duplicate-code`, `test-harnesses (13)`, `test-harnesses (15)`, and
the derived `test-harnesses-gate`.

## Actions

- Rebased the branch on latest `origin/main` (was 1 behind).
- **python-lint (E402/F811):** moved the late `design_lifecycle.py` imports
  above the module body and dropped a duplicate `import design_pause`.
- **python-lint-duplicate-code (R0801):** extracted the shared /design wrapper
  machinery into `session_env.py` — `COMMON_DESIGN_ENV_DEFAULTS`,
  `VALIDATOR_STATUS_ENV_DEFAULTS`, `WRAPPER_VALUE_FLAGS`,
  `parse_allowlisted_env_line`, `finalize_wrapper_env`, `require_plugin_root` —
  and re-pointed `design_lifecycle.py` and `plan_quality.py` at them. Restructured
  `test_design_cli_ports.py` so its expected table no longer mirrors the
  `cli.py` registry verbatim.
- **lint / lint-local / agent-lint / test-design-structure:** removed 22 stale
  `design-step0-*` / `step1d*` raw-path refs from the `skills/design/SKILL.md`
  wrapper-contract inventory (those scripts are retired and absent on disk; the
  PR's own `test-design-structure.sh` asserts their absence).
- **test-harnesses (13) partition guard:** changed the `test-design-step2b-drafter`
  Make target from a FULL-FILE run to `-k 'step2a or step2b'` so
  `test_design_lifecycle.py` strictly partitions across its five harness targets.
- **test-harnesses (15):** fixed `contains`/`not_contains` in
  `test-design-structure.sh` to pass `grep -e` so `-`-prefixed literals (e.g.
  `--with-plan-size`) are not parsed as options.
- Annotated three `monkeypatch.setattr(..., lambda _d: 11)` lines with
  `# type: ignore[arg-type]` per `.claude/rules/python-test-monkeypatch-lambdas.md`.

## Local verification

`make py-lint`, `make py-lint-duplicate-code`, `make py-test`,
`make lint`, `scripts/lint-harness-pytest-partition.py`, and
`scripts/test-design-structure.sh` all pass.

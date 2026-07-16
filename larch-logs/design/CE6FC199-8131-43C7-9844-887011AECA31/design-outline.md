## Proposed Design Outline

### Goals
- Add an engine-backed Python lint (`status-routing-truthiness`) that flags bare truthiness tests of status/verdict/result/outcome expressions when the same function proves via explicit comparisons that the expression has multiple semantic members.
- Provide an occurrence baseline with reason-bearing rows, `--write` regeneration, and same-line suppression.
- Wire the rule into the CLI, Makefile targets, and `docs/linting.md`.

### Non-goals
- Do not extend `lint_unreachable_branch`; the new detector classifies the first reachable boolean decision, not a later unreachable duplicate branch.
- Do not flag ordinary optional-string truthiness checks (e.g. `if rendered_result:`) lacking same-scope semantic-member evidence.
- Do not scan test files, `conftest.py`, `test_support.py`, `review_test_support.py`, or the lint module itself.

### Approach sketch
- New standalone detector in `python/larch/lint/lint_status_routing_truthiness.py`: two-pass scope-local AST walk (first pass collects semantic evidence per normalized expression; second pass flags bare truthiness uses of evidence-qualified expressions).
- Use the shared engine in `python/larch/lint/engine.py` (`LintRule`, `run_rule_cli`, `EngineFinding`, `SourceFile`) following the `lint_unreachable_branch` pattern.
- Baseline at `python/status-routing-truthiness-baseline.json`, keyed by `(file, qualified_symbol, normalized_condition, occurrence)`.
- Register CLI command `("lint", "status-routing-truthiness")` in `python/larch/cli.py`.
- Add `lint-status-routing-truthiness`, `test-lint-status-routing-truthiness`, and `regen-status-routing-truthiness-baseline` Makefile targets; add `status-routing-truthiness` to `py-lint-checks-fast`.
- Add a `new-module-justified` row to `python/lint-module-manifest.json`.
- Document in `docs/linting.md`.

### Surfaces in scope
- `python/larch/lint/lint_status_routing_truthiness.py` (new)
- `python/tests/lint/test_lint_status_routing_truthiness.py` (new)
- `python/larch/cli.py`
- `python/lint-module-manifest.json`
- `Makefile`
- `docs/linting.md`
- `python/status-routing-truthiness-baseline.json` (new, generated)

### Open questions
- None.

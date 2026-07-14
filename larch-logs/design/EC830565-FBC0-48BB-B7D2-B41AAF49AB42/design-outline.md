## Proposed Design Outline

### Goals
- Port `lint_markdown_heading_fence_state.py` to the shared engine: thin `detect(SourceFile)` function + `LintRule` + thin `main` calling `run_rule`.
- Delete all self-contained argparse, baseline I/O, discovery, and suppression code; delegate each to `engine.run_rule`.
- Keep `make lint-markdown-heading-fence-state`, `make test-lint-markdown-heading-fence-state`, and the markdown equivalence cases passing with identical rendered findings.

### Non-goals
- Changing the AST walking detection logic or its edge-case behavior.
- Adding new CLI flags beyond `--root`, `--write`, `--initial-reason` (already required).
- Porting `lint_unreachable_branch.py` or `lint_self_disarmable_gate.py` (separate pieces).
- Changing `python/larch/cli.py`, `Makefile`, or CI configs.

### Approach sketch
- Move detection into `detect(source: SourceFile) -> list[engine.Finding]`; path-filter (test files, excluded dirs) at top of detect; use `source.python_ast` from engine.
- Emit `engine.Finding` with `path`, `line`, `rule_id=SUPPRESSION`, encoded `message` (`applies heading regex {name} to splitlines without fence-state gating (occurrence {n})`); omit `qualified_symbol` so `_project_finding` uses `GenericBaselineRow`.
- Build `RULE = LintRule(rule_id=SUPPRESSION, ..., syntax_policy="skip", suppression_token=SUPPRESSION)` and call `run_rule(RULE, root, ProcRunner(), paths=["python"], ...)` in thin `main`.
- Update `test_lint_markdown_heading_fence_state.py`: remove old-schema helpers; cover `detect`, inline suppression via engine, and baseline write/check via `main`.
- Update `test_lint_engine_equivalence.py` adapter and fixture `qualified_symbol` to `null`.

### Surfaces in scope
- `python/larch/lint/lint_markdown_heading_fence_state.py` (rewrite, ~450 lines)
- `python/tests/lint/test_lint_markdown_heading_fence_state.py` (rewrite)
- `python/tests/lint/test_lint_engine_equivalence.py` (adapter update, MAY_UPDATE)
- `python/tests/lint/fixtures/lint_engine_equivalence/markdown_heading_fence_state.json` (fixture update, MAY_UPDATE)

### Open questions
- None.

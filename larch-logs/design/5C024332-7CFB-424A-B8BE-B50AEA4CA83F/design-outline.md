## Proposed Design Outline

### Goals
- Create `python/larch/lint/engine.py` with frozen `Finding`, `SourceFile`, and `LintRule` models, injected-Runner git discovery, UTF-8 loading, lazy AST cache, syntax-error policies, same-line suppression, detector output validation, deterministic rendering, and `run_rule` scan-only orchestration.
- Create `python/tests/lint/test_lint_engine.py` with a recording `Runner` fake covering discovery, path filtering, source/AST behavior, syntax policies, suppression, detector validation, rendering, and exit codes 0/1/2.

### Non-goals
- Baseline load/compare, `--write-baseline`, or `--strict-stale` support (deferred to later partitions).
- Equivalence tests or golden fixtures (separate partition).
- CLI registration, Makefile targets, or CI workflow changes.
- Changes to any existing lint module, baseline file, or entry point.

### Approach sketch
- Add two new files only; touch nothing existing.
- Define `Finding`, `SourceFile`, `LintRule` as frozen dataclasses in `engine.py`; `LintRule` carries `rule_id`, `description`, `detect`, `syntax_policy`, `suppression_token`.
- `SourceFile` holds `path`, `text`, `lines`; lazy `ast` property parses on first access for `.py` files, governed by the rule's `syntax_policy`.
- `run_rule(rule, root, runner, paths=None)` discovers tracked files via `git ls-files --cached`, optionally filters to `paths`, loads, detects, suppresses same-line pragma matches, validates detector output, renders `path:line: RULE_ID message` to stdout; returns exit code 0/1/2.
- Tests inject a recording `Runner` fake (records argv/cwd); no git binary needed.

### Surfaces in scope
- `python/larch/lint/engine.py` (new)
- `python/tests/lint/test_lint_engine.py` (new)

### Open questions
- None.

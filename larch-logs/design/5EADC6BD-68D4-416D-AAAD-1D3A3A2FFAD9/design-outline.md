## Proposed Design Outline

### Goals
- Add baseline parsing, stale detection, and match/suppress logic to `engine.py`.
- Add guarded `--write-baseline` via `larch.io` atomic no-follow writes with read-back validation.
- Extend `run_rule` with `baseline`, `write_baseline`, and `strict_stale` params; maintain exit-code contract.

### Non-goals
- No CLI registration or argparse entrypoint in `engine.py`.
- No changes to committed baseline files or existing production lint rules.
- No new sibling modules; all changes land in `engine.py` and `test_lint_engine.py`.

### Approach sketch
- Add `BaselineRecord` frozen dataclass with `path`, `line`, `rule_id`, `message`, `reason`, and optional `qualified_symbol`/`metric`.
- Add `load_baseline(path)` that parses JSON, validates schema, and rejects duplicate-identity records.
- Add two identity projection functions: generic `(path, line, rule_id, message)` and symbol-metric `(path, qualified_symbol, rule_id, metric)`.
- Extend `run_rule` to load baseline, suppress matched findings, warn on stale (or exit 2 with `strict_stale`), and write new baseline via `larch.io.atomic_write` with `nofollow=True` plus read-back parse.
- Validate flag combinations before doing any I/O; refuse invalid combos with exit 2.

### Surfaces in scope
- `python/larch/lint/engine.py`
- `python/tests/lint/test_lint_engine.py`

### Open questions
- None.

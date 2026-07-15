## Proposed Design Outline

### Goals
- Rewrite `lint_self_disarmable_gate.py` as a thin engine-backed rule (≤250 lines).
- Preserve all detection behavior: metadata-disarm detection, suppression with owner validation, `OptionalMetadata` re-export resolution, and design-module scope.
- Keep all existing tests passing; update the unit test to exercise the engine API.

### Non-goals
- Do not change detection logic or flag behavior.
- Do not add a baseline file; the rule stays baseline-free.
- Do not port any other lint modules.

### Approach sketch
- Extract all AST scanning helpers plus `resolve_optional_metadata`, `iter_gate_modules`, and `scan_file` into a new `self_disarmable_gate_detector.py`.
- Build a thin `lint_self_disarmable_gate.py` with `detect(SourceFile)`, a `RULE` constant, and a `run_rule`-based `main()`.
- Pre-resolve `OptionalMetadata` fields once in `_build_rule(root)` via a captured closure; the engine's per-file `detect()` receives the resolved `meta_fields`.
- Handle suppression (including owner-name validation) inside `detect()` itself; set `allow_inline_suppression=False` on the engine rule.
- Re-export `Finding`, `ScanError`, `MetadataResolution`, `SUPPRESSION`, `scan_file`, and `resolve_optional_metadata` from the thin wrapper for backward compatibility with existing tests.

### Surfaces in scope
- `python/larch/lint/self_disarmable_gate_detector.py` (new)
- `python/larch/lint/lint_self_disarmable_gate.py` (rewrite)
- `python/tests/lint/test_lint_self_disarmable_gate.py` (update)
- `python/tests/lint/test_lint_engine_equivalence.py` (update adapter to use `detect()`)
- `python/lint-module-manifest.json` (add entry for new detector module)

### Open questions
- None.

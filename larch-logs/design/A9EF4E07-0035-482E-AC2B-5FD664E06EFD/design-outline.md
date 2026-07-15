## Proposed Design Outline

### Goals
- Merge `_REGISTRY` and `_MACHINE_STDOUT_KEYS` into one dict: values become `(module, func, machine_stdout_bool)`.
- Repoint 39 facade-routing entries away from `design_lifecycle`, `review_pipeline`, and `run_logs` facades to the defining sub-modules.
- Eliminate the silent-omission failure class where adding a verb to `_REGISTRY` without `_MACHINE_STDOUT_KEYS` silently disables quiet-mode.

### Non-goals
- Do not delete or modify `design_lifecycle.py`, `review_pipeline.py`, or `run_logs.py` (facades remain for other consumers).
- Do not touch files outside the three firm headings: `python/larch/cli.py`, `python/tests/test_cli.py`, `python/tests/skills/_structure_design_specialized.py`.
- Do not change verb behavior, module implementations, or public CLI surface.

### Approach sketch
- Change `_REGISTRY` value type from `tuple[str, str]` to `tuple[str, str, bool]` (module, func, machine_stdout).
- Delete the hand-edited `_DESIGN_LIFECYCLE_STDOUT_KEYS` frozenset literal; all its consumers are in the firm headings.
- Replace the hand-edited `_MACHINE_STDOUT_KEYS` frozenset literal with a computed property derived from the new registry (`frozenset(k for k, v in _REGISTRY.items() if v[2])`); other test files outside firm headings reference this name, so the name stays as a computed backward-compatible alias.
- Update dispatch to unpack three values and use the bool directly.
- Repoint 28 design entries from `design_lifecycle` to actual sub-modules, 6 review entries from `review_pipeline` to sub-modules, 5 run-log entries from `run_logs` to `run_log_commit`/`run_log_flush`.
- Update `test_cli.py` assertions: `_REGISTRY[key]` now returns a 3-tuple; remove `_DESIGN_LIFECYCLE_STDOUT_KEYS` checks; retain `_MACHINE_STDOUT_KEYS` checks (the computed alias still satisfies them).
- Update `_structure_design_specialized.py` to drop the `_DESIGN_LIFECYCLE_STDOUT_KEYS` block extraction check and the assertion that `design_lifecycle` appears as a registry module.

### Surfaces in scope
- `python/larch/cli.py`
- `python/tests/test_cli.py`
- `python/tests/skills/_structure_design_specialized.py`

### Open questions
- None.

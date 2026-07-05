## Proposed Design Outline

### Goals
- Guideline deviation notes always land under `Warnings` in `execution-issues.md`, never `Tool Failures`.
- Each deviation note is written at most once per run (dedup on the append path).

### Non-goals
- No changes to the flush logic in `run_log_flush.py` or `execution_issues.py`.
- No changes to how other execution-issue entries (non-guideline) are written.
- No backfill of existing committed run logs.

### Approach sketch
- Add `append_deviation_note(implement_tmpdir, note)` in `architectural_guidelines.py`: always uses `category="Warnings"`, checks if entry already exists before appending (text-level dedup).
- Expose as `python3 cli.py architectural-guidelines append-deviation-note` (G-CLI-1 compliant).
- Update `architectural-guidelines-present.md` to call the new command instead of bare `execution-issues append`.
- Add unit tests in `test_architectural_guidelines.py` covering: correct category, dedup, and missing tmpdir.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`
- `python/larch/cli.py`
- `skills/implement/references/architectural-guidelines-present.md`
- `python/tests/core/test_architectural_guidelines.py`

### Open questions
- None.

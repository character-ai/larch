## Proposed Design Outline

### Goals
- Every bug issue larch auto-creates uses the canonical `[BUG]` prefix (all caps); no `[Bug]` (mixed-case) generation remains in source.
- Existing mixed-case `[Bug]` issues/comments stay recognizable for dedup and bug-mining (case-insensitive matching preserved).

### Non-goals
- Editing historical run logs under `larch-logs/` (off-limits).
- Changing the case-insensitive `bug_title_match` predicate or its input-based test coverage.
- Renaming or relocating the `BUG_PREFIX` constant.

### Approach sketch
- Generation sites switch from `[Bug]` literals to `title_match.BUG_PREFIX` (`[BUG]`): `_report.py` terminal/escalation titles and the `design_terminal.py` chat-fallback header.
- The two `[Bug]` consumers update to accept `[BUG]`: the `removeprefix` title-strip in `design_terminal.py` and the dedup regex in `file-failure-report-cross-repo.sh`. The dedup regex retains `[Bug]` too so historical comments still dedup.
- Test fixtures asserting generated output move to `[BUG]`; input-based matcher tests stay on `[Bug]`.

### Surfaces in scope
- `python/larch/state/_report.py`
- `python/larch/design/design_terminal.py`
- `scripts/file-failure-report-cross-repo.sh`
- `scripts/test-file-failure-report-cross-repo.sh`
- `python/tests/design/test_design_lifecycle.py`

### Open questions
- None.

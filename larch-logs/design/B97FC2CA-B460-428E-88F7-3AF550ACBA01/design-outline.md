## Proposed Design Outline

### Goals
- Remove remaining em-dash violations from 6 distinct production surfaces (OOS_1, 3, 4, 5, 6, 7).
- Keep `test-write-final-report.sh` fixture strings aligned with the current `: ` renderer contract.
- Harden the stalled-heading parser to scan all lines, not just the first non-empty line.

### Non-goals
- Changing timing-mark wire labels (OOS_2: accepted as passthrough per issue guidance).
- Updating test mock fixtures that contain `[content truncated — safety]` (they trigger on the prefix only).
- Refactoring ci_monitor beyond the single banner string change.

### Approach sketch
- One-line string fix in `ci_monitor.py` banner.
- One-line string fix in `redact.py` `_UNTERMINATED_MARKER`.
- One-line string fix in `bootstrap.py` append-failure fallback.
- Fixture-string updates in `test-write-final-report.sh` (heading assertions + top-reviewer assertion).
- Doc updates in `write-final-report.md`, `docs/run-logs.md`, and `skills/implement/SKILL.md`.
- Scan-all-lines fix in `final_report.py` `summary_heading_is_stalled` and `_summary_stalled_heading_index`.

### Surfaces in scope
- `python/larch/implement/ci_monitor.py`
- `python/larch/core/redact.py`
- `python/larch/state/bootstrap.py`
- `skills/implement/scripts/test-write-final-report.sh`
- `skills/implement/scripts/write-final-report.md`
- `docs/run-logs.md`
- `skills/implement/SKILL.md`
- `python/larch/report/final_report.py`
- `python/tests/implement/test_ship.py` (may need stalled-heading test updates)

### Open questions
- None.

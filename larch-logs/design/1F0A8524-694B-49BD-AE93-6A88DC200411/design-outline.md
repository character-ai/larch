## Proposed Design Outline

### Goals
- Select the most recently active implement session (by tmpdir activity, not pointer file mtime) when multiple stale pointer files exist for the same repo.
- Fix "Step 0 — preflight" false-positive in the progress report during Steps 5 and 8+ phases.

### Non-goals
- Garbage-collect the 591 accumulated stale pointer files (separate issue).
- Fix design session pointer selection (symlinks; different mechanism).

### Approach sketch
- In `_implement_candidate`, use `_path_mtime(tmpdir)` instead of `_path_mtime(pointer)` for the `LiveRun.mtime` field.
- The active session's tmpdir has more recently created entries (Steps 1–4 artifacts, `round-1/`, `ship-pr-state.sh`) than an abandoned stale session's tmpdir.
- Update the existing `test_newest_pointer_wins` test to use tmpdir mtimes instead of pointer mtimes.
- Add `test_stale_pointer_active_tmpdir_wins`: old pointer file mtime but newer tmpdir beats new pointer file mtime with older (stale) tmpdir.

### Surfaces in scope
- `python/progress_report.py` — `_implement_candidate` (one-line change)
- `python/test_progress_report.py` — one updated test + one new test

### Open questions
- None.

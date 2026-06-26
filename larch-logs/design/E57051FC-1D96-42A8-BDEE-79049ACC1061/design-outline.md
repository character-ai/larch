## Proposed Design Outline

### Goals
- Preserve the degraded `voting-tally.md` as a sibling artifact before each retry overwrites it.
- Commit sibling artifacts to `larch-logs/implement/<RUN_ID>/round-N/` for post-run root cause analysis.

### Non-goals
- Do not change the degraded-panel detection condition or retry decision logic.
- Do not change `voting-tally.md` format or the panel retry count limit.
- Do not add new operator-facing messages beyond what the retry already emits.

### Approach sketch
- In `_run_review_round` (review_and_fix.py), add `shutil.copyfile` call immediately before the retry `review_core_capture` call: `voting-tally.md` → `voting-tally-degraded-attempt-1.md`.
- If the retry also degrades (existing `if voting_tally_file.is_file() and "⚠ Degraded"` branch), add a second `shutil.copyfile`: `voting-tally.md` → `voting-tally-degraded-attempt-2.md`.
- Add `"voting-tally-degraded-attempt-*.md"` to `_ROUND_ARTIFACT_ALLOW_GLOBS` in `run_logs.py`.
- Add two tests to `test_review_and_fix.py`: one for degraded→clean retry and one for degraded→still-degraded retry.

### Surfaces in scope
- `python/review_and_fix.py` — `_run_review_round` function
- `python/run_logs.py` — `_ROUND_ARTIFACT_ALLOW_GLOBS` tuple
- `python/test_review_and_fix.py` — two new test functions

### Open questions
- None.

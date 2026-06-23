## Proposed Design Outline

### Goals
- Have Python write `reviewer-status-table.txt` (one rendered line) alongside `latest-reviewer-status.tsv`.
- Remove the ~12-line duplicated round-binding fallback prose from both Step 3 execution blocks in SKILL.md.
- Collapse both blocks to "read and emit `reviewer-status-table.txt` verbatim; warn and skip if absent."

### Non-goals
- Populating elapsed timing in the TSV (still blank; future work).
- Changing the icon set or table format beyond what's in the issue.
- Touching any surface outside `plan_review_round.py`, `test_plan_review_round.py`, and `skills/design/SKILL.md`.

### Approach sketch
- Add `render_reviewer_status_table(tsv_content: str) -> str` in `plan_review_round.py`; maps TSV rows to `📊 Reviewers: | Slot: icon |` line.
- Call the renderer inside `sync_latest_reviewer_status` (or immediately after) so `reviewer-status-table.txt` stays in sync with `latest-reviewer-status.tsv`.
- Expose via `python/cli.py plan-review render-status-table --design-tmpdir` if needed for tests, but the primary path is the auto-write alongside TSV.
- Update `test_plan_review_round.py` with renderer unit tests covering all four icon states.
- Shrink the two duplicated SKILL.md blocks to a two-line emit + warn-and-skip fallback.

### Surfaces in scope
- `python/plan_review_round.py`
- `python/test_plan_review_round.py`
- `skills/design/SKILL.md` (two Step 3 execution blocks)

### Open questions
- None.

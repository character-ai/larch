## Proposed Design Outline

### Goals
- Fix `compose-report --surface issue-input` so the dedup marker appears in the filed GitHub issue body (not before the first heading).
- Add a regression test asserting the marker is in the body section after the title heading.

### Non-goals
- Not modifying `parse_issue_input` (Option 2 rejected; smaller fix is in `compose-report`).
- Not changing Tier B (`chat-print`) path; it already places the marker correctly.
- Not altering `dedup-tier-a-report`, `file-failure-report-cross-repo.sh`, or any filing driver.

### Approach sketch
- Add `report_sig: str` parameter to `_compose_tier_a_issue()` in `python/stall_recovery.py`.
- Insert `_report_marker(report_sig)` into the body list immediately after `f"### {title}"`.
- Update the one caller (line ~1051) to pass `report_sig=report_sig` and drop the outer prepend.
- Add a test in `python/test_stall_recovery.py` reading the output `stall-recovery-issue-input.md` and asserting the marker follows the title heading (not precedes it).

### Surfaces in scope
- `python/stall_recovery.py` — `_compose_tier_a_issue` + its one caller.
- `python/test_stall_recovery.py` — one new regression test.

### Open questions
- None.

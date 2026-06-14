## Proposed Design Outline

### Goals
- Fix `step-5-resume.sh` idempotency bug that records a late duplicate `round` timing entry, causing the Gantt window to span the full run (including ship-pr) instead of just the review phase
- Add status filter to the Gantt AWK in `render-review-phase-detail.sh` to exclude `signal`/`unknown` vendor entries from the timing chart

### Non-goals
- Changing the intentional "unfiltered round overlap" Gantt design (vendor rows overlapping any same-numbered round entry across skills still appear)
- Filtering by task kind (e.g. excluding `-ci-fix` kinds explicitly) — the window fix is sufficient
- Fixing historical already-committed run log files

### Approach sketch
- `step-5-resume.sh` line 68: change `exit found` to `exit !found` so the idempotency check correctly skips recording when any round entry with the matching `start_s` already exists
- `render-review-phase-detail.sh` gantt AWK: tighten `NF >= 9` to `NF >= 13` and add `($13 == "complete" || $13 == "OK")` status filter, matching Python `progress_report.py` behavior
- Add regression test for the `step-5-resume.sh` idempotency fix in `test-render-review-phase-detail.sh`: two round entries for same round → chart uses shorter window, CI-fix vendor entries outside window are excluded
- Update `.md` siblings as required

### Surfaces in scope
- `skills/implement/scripts/step-5-resume.sh`
- `skills/implement/scripts/step-5-resume.md`
- `scripts/render-review-phase-detail.sh`
- `scripts/render-review-phase-detail.md`
- `scripts/test-render-review-phase-detail.sh`

### Open questions
- None.

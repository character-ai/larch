## Proposed Design Outline

### Goals
- Add a `rounds` sub-array to the Step 5 (implement code review) and Step 3 (design plan review) `per_step` entries in `timing-report.json`.
- Each round carries `duration_seconds` plus finding counts: `accepted`/`rejected` for both skills, and an extra `oos` count for design.
- Ship the richer report into the committed larch-log `timing-report` batch and cover it with a test.

### Non-goals
- No changes to the human-readable markdown `## Per-Step Durations` table (JSON-only).
- No changes to downstream analysis tooling (`/report-tokens`, etc.).
- No backfill of historical committed reports; no new flush site; no renamed/removed existing fields.

### Approach sketch
- Persist per-round data in the timing ledger so it survives the flush — `timing-report.json` renders from the ledger TSV, not from tmpdir tally files.
- Instrument round boundaries: `review-and-fix.sh` / its Step 5 round driver for implement; `plan-review-loop.sh` for design — emit one record per finished round, reading counts from the existing per-round tally artifacts.
- Aggregate in `timing-report.sh`: attach the `rounds` array to the matching Step 5 / Step 3 `per_step` entry.
- Keep `rounds` purely additive; keep ledger rows Bash 3.2-portable and within the fixed 13-column invariant.

### Surfaces in scope
- `scripts/timing-ledger.sh`, `scripts/timing-report.sh` (+ `.md` siblings)
- `skills/review-and-fix/scripts/review-and-fix.sh` (and/or its Step 5 round driver)
- `skills/design/scripts/plan-review-loop.sh`
- `scripts/test-timing-report.sh` (extend / add round-field coverage)

### Open questions
- Ledger row encoding (new `round` row kind vs. extending `mark`) and the round→per_step matching key are architectural; resolved during plan drafting (Step 2b).

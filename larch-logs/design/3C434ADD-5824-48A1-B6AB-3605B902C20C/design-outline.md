## Proposed Design Outline

### Goals
- Close the concrete transcript-capture gaps found in `/design` (clarify publish path) and `/implement` (bail/stall paths before Step 7a) so every committed run log carries `session-transcript.jsonl`.
- Extend transcript capture to standalone `/review`'s larch-log batch writer.
- Add per-skill coverage-ratio reporting to `token measure-references-heatmap` (transcript-bearing runs vs. total runs per skill).

### Non-goals
- No backfill or rewriting of historical committed `larch-logs/` runs (issue constraint: "no committed-log rewrites").
- No change to the v3 transcript schema/policy (`render_session_transcript`'s sanitized-Read-stub, prose-errors-only contract) — capture wiring only.
- No change to nested `/review`-within-`/implement` log ownership; only standalone `/review`'s own batch write is in scope.

### Approach sketch
- `/design`: make the clarify publish path (`clarify.py` → `design log-publish`) reuse the same transcript-capture step Step 5c already runs, so clarify round-trips also commit a transcript.
- `/implement`: add a best-effort session-transcript safety net at Step 18 finalize, mirroring the existing `execution-issues flush-safety-net` pattern, so runs that bail/stall before Step 7a still capture a transcript when logs are committed.
- `/review`: register a transcript batch in the Step 4 log-writer path (`review_tally.py` batch allowlist + `skills/review/SKILL.md` Step 4) alongside the existing `review-context`/`review-tally`/etc. batches.
- Reporting: extend `measure_references_heatmap()` in `tokens.py` with a per-skill coverage summary, reusing the measured/not-yet-measured convention already established in `measure_realized_cost()`.

### Surfaces in scope
- `python/larch/design/clarify.py`, `design_publish.py`, `design_log_publish_flow.py`
- `python/larch/implement/dispatch_step18.py`, `skills/implement/scripts/step-18.sh`/`.md`
- `python/larch/review/review_tally.py`, `skills/review/SKILL.md` (Step 4)
- `python/larch/report/tokens.py` (`measure_references_heatmap`), `docs/run-logs.md`

### Open questions
- None.

## Proposed Design Outline

### Goals
- Add `scripts/lib-voter-coverage.sh` + `.md`: a small shared helper that consolidates plan-voter status-counter logic and KV emission so dispatcher and tally agree on coverage shape.
- Make `tally-plan-review.sh` always emit `TALLY_PLAN_REVIEW_STATUS` to stdout (success and every error path) so multi-round callers can parse status unconditionally.
- Cap per-voter waterfall time in `dispatch-plan-voters.sh` at a fixed 1860s so a single hung external cannot extend a round indefinitely.

### Non-goals
- Do not introduce, mention, or remove `voting-tally.env` (already handled in a sibling piece).
- Do not change per-severity counting at this layer; severity stays in the existing 21-field forensic TSV. No new `TALLY_IMPORTANT_*` stdout KVs (piece 5 owns convergence).
- Do not modify the existing single-round default for `--findings-classification-out` (`plan-review/round-1/findings-classification.tsv`); per-round callers already pass it explicitly.

### Approach sketch
- New file `scripts/lib-voter-coverage.sh`: source-only library exposing a function that takes voter status variables and emits the documented `VOTER_*_STATUS` and DEGRADED_PANEL_WARNING KVs via `emit_kv`. Mirror the existing pattern from `lib-voter-parse-rate.sh` (sibling library, same convention).
- `dispatch-plan-voters.sh`: source the new lib, replace the duplicated emit block with a single helper call, and pass a fixed `--timeout 1860` to `dispatch-with-waterfall.sh` for Voters 2–3.
- `tally-plan-review.sh`: add an EXIT trap (or convert each non-zero exit path) that emits `TALLY_PLAN_REVIEW_STATUS=tally-error` when no success status has been emitted yet, before the script exits non-zero. Idempotent — no duplicate emission on the success paths.
- Extend `scripts/test-dispatch-plan-voters.sh` and `skills/design/scripts/test-tally-plan-review.sh` to exercise the new helper, the timeout cap, and the always-emit error path.
- Refresh `.md` sidecars (dispatch + tally) to document per-round `--design-tmpdir` routing, the new shared helper, the always-emit invariant, and the timeout cap.

### Surfaces in scope
- `scripts/lib-voter-coverage.sh` (NEW)
- `scripts/lib-voter-coverage.md` (NEW)
- `scripts/dispatch-plan-voters.sh`
- `scripts/dispatch-plan-voters.md`
- `skills/design/scripts/tally-plan-review.sh`
- `skills/design/scripts/tally-plan-review.md`
- `scripts/test-dispatch-plan-voters.sh`
- `skills/design/scripts/test-tally-plan-review.sh`

### Open questions
- None.

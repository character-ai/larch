## Proposed Design Outline

### Goals
- Fix Bug 1: surface invalid `mechanical_churn` values (e.g., integers) via awk stderr diagnostic and `check-plan-size.sh` exit 2 with `PLAN_SIZE_STATUS=invalid-mechanical-churn`.
- Fix Bug 2: detect ballot-items-lost state (`INSCOPE_REMAINING > 0`, TSV header-only) in `plan-review-loop.sh`, set `DEGRADED_PANEL=1`, and persist `INSCOPE_REMAINING` to `round-summary.env`.
- Update `plan-review-continuation.sh` to continue (`REASON=ballot-items-lost`) when `DEGRADED_PANEL=1` and `ACCEPTED_COUNT=0`.

### Non-goals
- Not changing the Codex/Cursor drafter to avoid emitting integer values (separate concern).
- Not modifying `design-postplan-emit.sh` directly — the existing exit-2 handling in that script already propagates `check-plan-size.sh` errors.
- Not changing nit-prune logic or other plan-review stages beyond the detection point.

### Approach sketch
- `lib-plan-optional-trailers.awk`: add an else-branch when `mechanical_churn` is present but not `true`/`false`; emit `invalid-mechanical-churn: <value>` to stderr.
- `check-plan-size.sh`: after parsing `mechanical_churn` from awk, check for an invalid value; emit `PLAN_SIZE_STATUS=invalid-mechanical-churn` and exit 2.
- `plan-review-loop.sh`: read `INSCOPE_REMAINING` from `_plan_prune_out` (alongside `PRUNED_COUNT`); after `DEGRADED_PANEL` is finalized post-tally, add a check: if `TALLY=ok && INSCOPE_REMAINING>0 && TSV-has-zero-data-rows` then `DEGRADED_PANEL=1`; add `INSCOPE_REMAINING` to `_write_round_summary`.
- `plan-review-continuation.sh`: add branch `DEGRADED_PANEL != 0 && ACCEPTED_COUNT == 0` → `CONTINUE=true REASON=ballot-items-lost` (before existing ACCEPTED_COUNT>0 check).

### Surfaces in scope
- `skills/design/scripts/lib-plan-optional-trailers.awk`
- `skills/design/scripts/check-plan-size.sh`
- `skills/design/scripts/plan-review-loop.sh`
- `skills/design/scripts/plan-review-continuation.sh`
- `skills/design/scripts/plan-review-loop.md`
- `skills/design/scripts/test-check-plan-size.sh`
- `skills/design/scripts/test-plan-review-loop.sh`

### Open questions
- None.

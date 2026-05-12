## Goal
Reduce token/timing instrumentation overhead in `/implement` by consolidating sub-phase marks, removing per-step terse reports, and gating the final table behind `LARCH_VERBOSE_TOKENS`.

## Implementation Plan
**A** — Remove the per-round timing mark inside Step 5's quick-mode review loop (`LARCH_TIMING_SKILL=review timing-ledger.sh mark "review Step 5 quick round N"`).
**B** — Remove all 18 per-step `--since-last-mark --terse` step-end blocks from `skills/implement/SKILL.md` (Steps 0–16). Keep Step 18's already-silenced `/dev/null` calls untouched.
**C** — Add `--summary` flag to `token-report.sh` and `timing-report.sh` (outputs one grand-total line). Gate Step 17's `--full --markdown` behind `LARCH_VERBOSE_TOKENS=true`; default uses `--summary`.

## Test plan
- `/relevant-checks` passes (pre-commit + agent-lint)
- Confirm removed block count matches 18 step-end blocks
- Confirm Step 18 `/dev/null` calls and `--append-token-report` calls are unchanged

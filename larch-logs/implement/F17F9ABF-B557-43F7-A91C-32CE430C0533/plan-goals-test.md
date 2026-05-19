## Goal
Add review-loop convergence: early-termination, degraded-round handling, and churn warning to review-and-fix.sh

## Implementation Plan

### 1. review-and-fix.sh changes

**New flag**: `--convergence-threshold N` (default: 3 when empty, stored as `CONVERGENCE_THRESHOLD`).

**Part B — Degraded round detection** (insert after reading core_out values, before OOS processing):
- Check `$round_dir/voting-tally.md` for `⚠ Degraded code-review panel` banner
- If found: set `degraded_this_round=true`, emit stderr breadcrumb
- If no retry flag exists: write `$round_dir/degraded-retry.flag`, re-call `$REVIEW_CORE_SH` same args, re-read all core_out vars
- Re-check banner on retry; if clean → `degraded_this_round=false`; if still degraded → log warning, proceed best-effort

**Part A — Convergence check** (insert after status determination, before `write_summary_json`):
- Skip when: exit_code != 0, round_num_dec < 2, or `degraded_this_round=true`
- Read prev round's ACCEPTED_COUNT from `$IMPLEMENT_TMPDIR/round-${prev_round}/review-core.env`
- If both prev and current accepted_count <= CONVERGENCE_THRESHOLD:
  - Check `$round_dir/findings.md` and `$prev_round_dir/findings.md` for Important findings
  - If no Important: set `status=converged-small-changes`

**Part C — Churn warning** (insert immediately after Part A):
- When exit_code == 0 and round_num_dec >= 3:
  - Read prev round's ACCEPTED_COUNT from `round-${prev_round}/review-core.env`
  - If current > prev: `larch_err` the warning message

**New emit_kv**: `emit_kv DEGRADED_ROUND "$degraded_this_round"` in the output section.

### 2. review-and-fix.md changes
- Add `--convergence-threshold N` to flags section
- Add `DEGRADED_ROUND` to output keys
- Add `converged-small-changes` to REVIEW_AND_FIX_STATUS values

### 3. test-review-and-fix.sh changes
8 regression tests using:
- Pre-populated `round-N/review-core.env` files for multi-round simulation
- New `TEST_CORE_STATUS=degraded-panel` stub writing voting-tally.md with banner
- New `TEST_CORE_STATUS=degraded-panel-clean-retry` stub for retry tests


## Test plan
(no test plan section in plan-file)

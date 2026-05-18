## Goal
Fix two status-signaling inconsistencies: collapse ship-pr.sh ci-initial phase exit and change review-and-fix.sh exit-3 to exit-0 with stdout KV

## Implementation Plan

### Goal
Fix two control-flow inconsistencies in larch's status-signaling protocol:
1. Part 4a: `ship-pr.sh` ci-initial → ci-merge phase boundary exits unnecessarily, requiring orchestrator re-entry via CI_PASSED=true
2. Part 4b: `review-and-fix.sh` uses exit code 3 to signal "fix-applied; continue review" — a success path should exit 0 with stdout KV

### Part 4a: ship-pr.sh phase collapse (Path A)

**Investigation result**: The `run_ci_phase` function is called from a `while` loop that reads PHASE from state. When ci-initial ACTION=merge fires, the script calls `advance_phase ci-merge; exit 0`. If we change `exit 0` to `return 0`, the while loop naturally continues to `run_ci_phase ci-merge`. No external-state wait crosses this boundary.

**Change in `scripts/ship-pr.sh`**:
- In `run_ci_phase`, when `phase=ci-initial` and `action=merge`: change `exit 0` → `return 0`
- Keep `state_set CI_PASSED true` for state tracking
- Result: ship-pr.sh runs ci-initial → ci-merge → postmerge → done in one invocation

**Change in `skills/implement/SKILL.md`**:
- In the Step 8+ Exit 0 handling: remove the sentence "If `CI_PASSED=true`, re-invoke `ship-pr.sh --resume-phase ci-merge`."
- The `Otherwise continue by re-invoking the script with the current PHASE` clause handles any backward-compat edge cases

### Part 4b: review-and-fix.sh exit-code-3 → exit-0 + KV

**Change in `skills/review-and-fix/scripts/review-and-fix.sh`**:
- In orchestrator mode `fix-required|cap-reached` case, when `coder_status=="applied"`:
  - Change `status="fix-required"; exit_code=3` → `status="fix-applied"; exit_code=0`
- In the log-flush condition: `if [[ "$exit_code" -eq 0 || "$exit_code" -eq 3 ]]` → `if [[ "$exit_code" -eq 0 ]]`

**Change in `skills/review-and-fix/scripts/review-and-fix.md`**:
- Update REVIEW_AND_FIX_STATUS values: add `fix-applied` to the list
- Update exit code section: remove exit 3, fold into exit 0 description
- Update flush-condition description to remove "or 3 (fix-required)"

**Change in `skills/implement/SKILL.md`**:
- In Step 5 exit-code table: remove `**Exit 3**` bullet
- Update `**Exit 0**`: add `REVIEW_AND_FIX_STATUS=fix-applied` case handling (same behavior as prior exit 3)

**Change in `skills/review-and-fix/scripts/test-review-and-fix.sh`**:
- Line ~202: `[[ "$rc" -eq 3 ]]` → `[[ "$rc" -eq 0 ]]` for codex-case and cursor-case
- Line ~203: `REVIEW_AND_FIX_STATUS=fix-required` → `REVIEW_AND_FIX_STATUS=fix-applied`
- Line ~213: `.status == "fix-required"` → `.status == "fix-applied"` in jq filter
- Line ~572: `[[ "$rc" -eq 3 ]]` → `[[ "$rc" -eq 0 ]]` for skipped-routing case


## Test plan
- `make test-review-and-fix` — verifies Part 4b assertions
- `pre-commit` on modified files — verifies shell syntax and agent-lint

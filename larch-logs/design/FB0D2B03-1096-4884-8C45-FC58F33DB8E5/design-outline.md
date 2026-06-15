## Proposed Design Outline

### Goals
- Fix the sanctioned waiter exception to use `.completed/step-3` (not `.step3-review-result.env`) as the Step 3 completion sentinel.
- Clear `.step3-review-result.env` before starting round 2 to prevent stale reads from triggering a premature completion signal.
- Verify `finalize.py` already kills background processes before `shutil.rmtree` (Fix C already in place).

### Non-goals
- Change how rounds are dispatched or how `plan-review-loop.sh` writes per-round results.
- Modify `agent wait-reviewers` timeout behavior.
- Change the happy-path (no premature notification) Step 3 flow.
- Add `kill` logic beyond what's already in `finalize.py`.

### Approach sketch
- `SKILL.md`: Amend Anti-pattern #4 and the Step 3 "Task tool notification boundary" blocks to name `.completed/step-3` as the required condition when the sanctioned one-time waiter fires.
- `review-design-step3-loop.sh`: In `run_design_step3_loop()`, add `rm -f "$DESIGN_TMPDIR/.step3-review-result.env" 2>/dev/null || true` before `round_num` increment on the `PLAN_REVIEW_CONTINUE=true` path.
- `review-design-step3-loop.md`: Document the clearing behavior in the sibling contract.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/scripts/review-design-step3-loop.sh`
- `skills/design/scripts/review-design-step3-loop.md`

### Open questions
- None.

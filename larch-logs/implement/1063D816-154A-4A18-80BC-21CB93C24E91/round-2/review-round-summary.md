# Review Round 2

- Mode: `diff`
- 3 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_3: Missing pytest for `complete` publish refusal without sentinel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `pytest` covers cap-hit publish refusal without `.completed/step-3` but not the symmetric `complete` branch in `_TERMINAL_STATUSES_REQUIRING_SENTINEL`. A future edit could remove or break the `complete` guard while the cap-hit test still passes, weakening the Step 5c safety net for premature loop-complete routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_publish_refuses_complete_without_step3_sentinel` mirroring the cap-hit test and asserting `complete` without `.completed/step-3`.


### FINDING_4: `_splice_plan_provenance()` breaks optional metadata trailer
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_splice_plan_provenance()` inserts provenance immediately above `diff_lines:` and strips `review_status:` / `rounds_completed:` lines globally. This breaks the final optional metadata trailer block; for example `mechanical_churn: true` is no longer adjacent to `diff_lines:` and `plan_quality.parse_optional_metadata()` reads it as absent. It can also delete legitimate plan-body lines that start with those keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Strip only existing provenance lines from the final metadata/provenance trailer area, recompute the insertion index after stripping, and insert provenance before the final size-trailer block so optional trailers remain directly above `diff_lines:`.


### FINDING_6: Recovery waiter must not substitute for original Step 3 task exit
- **Reviewer(s)**: dyn-sentinel-routing-output.txt
- **Severity**: important
- **Concern**: The recovery contract tells the orchestrator to wait on `.completed/step-3` after a premature notification, but does not state that sentinel presence alone is insufficient. In `review-design-step3-loop.sh`, `step3_loop_write_completed_step3()` runs before `step3_loop_emit_envelope()` and loop exit; `design-step3-review.sh` only returns after `wait`, teardown, and stdout parsing. A recovery waiter can unblock while `design-step3-review.sh` is still in teardown, letting Steps 3b–6 race ahead of wrapper cleanup and recreate the tmpdir-deletion / lingering-process failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-routing-output.txt: State explicitly that the recovery waiter is only for premature notifications; after it fires, the orchestrator must still wait for the original `design-step3-review.sh` `<task-notification>` before routing past Step 3, and must not enter Step 6 until that background task has exited.



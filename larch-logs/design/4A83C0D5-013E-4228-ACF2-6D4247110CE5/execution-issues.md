### External Reviewer Issues

- **Step design Step 3 — run-step3-review.sh -> plan-review-loop.sh (--convergence-threshold argv mismatch) failed (exit 2)**:
  ```
Step 3 plan-review panel-failed on first attempt — VERIFIED root cause:
plugin 47.0.19 argv mismatch. run-step3-review.sh passes --convergence-threshold
to plan-review-loop.sh, but plan-review-loop.sh (post-#3243) no longer accepts
that flag and rejects unknown options with exit 2 before writing its inner
result env. This breaks Step 3 on every /design run on this version.

Workaround (session-local, does not modify plugin or repo): RUN_STEP3_PLAN_REVIEW_LOOP_SH
points at a shim that strips --convergence-threshold and forwards the remaining
(all-accepted) args to the real plan-review-loop.sh. Recommend filing a plugin
bug to re-align run-step3-review.sh <-> plan-review-loop.sh argv.
  ```

### Warnings

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=4
total_findings=4
total_ballot_items=4
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=4
total_findings=4
total_ballot_items=4
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=1
total_findings=1
total_ballot_items=1
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=3
total_findings=3
total_ballot_items=3
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```

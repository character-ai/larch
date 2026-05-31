### Warnings

- **Step design Step 3 (run-step3-review.sh) — plan-review-loop.sh --convergence-threshold failed (exit 2)**:
  ```
plan-review-loop.sh: unknown option: --convergence-threshold

Live plugin bug (v47.0.19, main): run-step3-review.sh:208-210 forwards
--convergence-threshold to plan-review-loop.sh, whose argv parser (line 89)
rejects it as an unknown option. Step 3 panel-fails on every /design run.
Workaround for this session only: RUN_STEP3_PLAN_REVIEW_LOOP_SH points at a
shim that strips the flag and execs the real plan-review-loop.sh. No committed
plugin file modified. Separate fix needed on main (drop the forwarded flag or
add a no-op --convergence-threshold case to plan-review-loop.sh).
  ```

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=2
total_findings=2
total_ballot_items=2
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

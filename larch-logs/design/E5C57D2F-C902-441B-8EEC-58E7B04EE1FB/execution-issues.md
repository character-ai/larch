### Warnings

- **Step design Step 3 (pre-wired workaround) — run-step3-review.sh -> plan-review-loop.sh (--convergence-threshold) failed (exit 2)**:
  ```
Plugin 47.0.19 Step 3 plan-review break (pre-wired workaround):
  run-step3-review.sh:210 forwards --convergence-threshold to plan-review-loop.sh.
  plan-review-loop.sh (post-#3243) has no --convergence-threshold case;
  its catch-all rejects unknown flags with exit 2 -> Step 3 panel-failed -> Gate B skipped.
  Workaround: RUN_STEP3_PLAN_REVIEW_LOOP_SH=<TMPDIR>/plan-review-loop-shim.sh
  Shim strips --convergence-threshold and forwards remaining args to the bundled plan-review-loop.sh.
  Verified: shim+--help exit 0; bundled+--convergence-threshold exit 2.
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

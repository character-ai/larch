# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_5: _capture_stdout_stderr can crash before Step 5b machine contract
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_capture_stdout_stderr` opens `stderr_path` before its try block, so annotate can raise `FileNotFoundError` (e.g. `DESIGN_TMPDIR=relative-missing`) before the non-zero branch emits `OOS_ANN_RC` or `STEP5B_STATUS=annotate-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Catch OSError around capture setup/writeback and route it through the existing annotate failure branch without marking completion.


### FINDING_7: Step 3 round cap off-by-one after outer prewrite
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Outer Step 3 prewrites `review-round-count.txt`, but `run_plan_review_round` still uses that file for its own cap gate. With `review-round-count.txt` at 4, `run_step3_review` writes 5 before dispatch; `run_plan_review_round` then sees 5 >= `ROUND_CAP` and skips the fifth allowed round as cap-reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Make run_plan_review_round loop-mode count-neutral, or pass the original prior count into the round body and use that for cap checks and rollback.



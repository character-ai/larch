### OOS_1: [OUT_OF_SCOPE] Success awaiting-continuation uses loop-local round_start_s
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step3-resume-timing-output.txt
- **Severity**: important
- **Concern**: On successful `awaiting-continuation`, `step3_loop_record_timing` at `skills/design/scripts/review-design-step3-loop.sh:757` still uses loop-local `round_start_s` (reset at line 592 each iteration), not `step3_loop_read_round_start_s`. That refresh on every loop iteration, including phase resumes, is the root cause. For `main-agent-vote-required` rounds, `plan-review-loop.sh` skips the snapshot round row, so a success-path record with a resume-time start can narrow the final Gantt window and hide reviewer rows. Final-report Gantt uses min/max across round rows, so impact may be limited when an earlier row exists, but success-vs-failure timing semantics remain inconsistent on resumed phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `step3_loop_read_round_start_s` on line 757 as well (and consider line 626 for panel-failed).
  - From cursor-specialist-edge-cases-output.txt: Use step3_loop_read_round_start_s for the line 757 success record, same as postplan-failed paths.



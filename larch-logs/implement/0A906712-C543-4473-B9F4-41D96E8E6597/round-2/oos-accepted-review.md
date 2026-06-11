### OOS_5: [OUT_OF_SCOPE] Step 2 remains foreground despite immediate-background policy
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-arch-consistency-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: Step 2 still routes a long-running implementer through foreground dispatcher prose, conflicting with the >=30s immediate-background policy and related docs. This also leaves the run-log audit and structure-test coverage for Step 2 unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-arch-consistency-output.txt, dyn-risk-completeness-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Step 5 resume can ignore commit failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `commit-review-fixes.sh --stage-all || true` can hide commit failures before resuming review, leaving fixes uncommitted and later review rounds stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] Step 5 resume lacks explicit post-resume status branching
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After `step-5-resume --ready-to-commit`, non-terminal nested statuses may fall through without re-parsing and re-branching on `STEP5_REVIEW_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] Design Step 2b drafter remains foreground
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: `design-step2b-drafter.sh` still has a foreground timeout-only fence. If the drafter runs for minutes, it bypasses the immediate-background policy, although one source marked it outside the narrow design review-loop scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-risk-completeness-output.txt: Address the concern above.



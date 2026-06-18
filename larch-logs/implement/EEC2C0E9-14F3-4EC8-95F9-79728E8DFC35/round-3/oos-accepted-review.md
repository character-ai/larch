### OOS_1: [OUT_OF_SCOPE] Validator autofix Bash harness deleted without full pytest port
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-design-step-validator-autofix.sh` covered operator-cancel false-ok and Warnings-row paths not present in new validator_autofix pytest cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port the missing operator-cancel and false-ok scenarios into `test_plan_quality.py` or keep a thin compatibility harness.


### OOS_2: [OUT_OF_SCOPE] Harness premature notification / recovery-waiter exit 144 deferred
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-sentinel-contract-output.txt
- **Severity**: latent
- **Concern**: Harness-level premature `<task-notification>` firing and recovery-waiter exit 144 are not fixed in this branch. Recovery waiter can still be killed (exit 144); root cause is unchanged. Foreground probe is mitigation only; explicitly deferred by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track separately per plan; foreground probe is mitigation only.



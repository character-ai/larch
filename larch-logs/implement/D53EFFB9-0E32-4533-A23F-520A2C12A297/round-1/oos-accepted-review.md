### OOS_1: [OUT_OF_SCOPE] Behavioral TERM regression for waterfall trap unproven in CI
- **Reviewer(s)**: dyn-process-cleanup-output.txt
- **Severity**: important
- **Concern**: `scripts/test-dispatch-with-waterfall.sh:634-640` only grep-checks for the EXIT trap; the plan's behavioral TERM regression (stub launcher + assert child reaped) is not implemented, so trap effectiveness is unproven in CI.


### OOS_2: [OUT_OF_SCOPE] `dispatch-plan-voters.sh` backgrounds voter without EXIT trap
- **Reviewer(s)**: dyn-process-cleanup-output.txt
- **Severity**: latent
- **Concern**: `scripts/dispatch-plan-voters.sh:109` still backgrounds the Claude voter without an EXIT trap; that predates this branch and is outside the changed surface, though it can produce similar tmpdir-referenced orphans if the parent exits early.


### OOS_3: [OUT_OF_SCOPE] Kill-helper tests omit symlink and prefix-collision coverage
- **Reviewer(s)**: dyn-tmpdir-validation-output.txt
- **Severity**: latent
- **Concern**: `python/test_finalize.py:420-443` covers missing marker, basename prefix, and newline/`..` rejection, but not symlinked leaf tmpdirs or prefix-collision kill scope. Those gaps leave the amplified kill-scope issues unguarded in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tmpdir-validation-output.txt: Add harness cases for symlinked leaf tmpdirs and prefix-collision kill scope (implied by the cited test gaps in the source finding).


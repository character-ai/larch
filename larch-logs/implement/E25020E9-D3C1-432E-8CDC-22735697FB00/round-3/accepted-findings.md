### FINDING_15: publish push failure omits recovery branch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` preserves a local recovery ref on push failure but does not emit `RECOVERY_BRANCH`, causing pause save to fail closed without surfacing the recoverable local commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: missing registry-order resume test case
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The pause/resume harness lacks the plan-required case where only step-1c and step-2a sentinels exist, so a buggy max-completed-step walk could resume at the wrong step without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: missing force-with-lease remote branch reuse test
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-design-log-publish.sh` lacks the plan-required two-pass pause publish fixture for an existing remote `larch-log-design-<RUN_ID>` branch, so branch reuse regressions may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.



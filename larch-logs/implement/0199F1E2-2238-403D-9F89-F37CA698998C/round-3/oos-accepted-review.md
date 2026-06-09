### OOS_8: [OUT_OF_SCOPE] Structure test does not pin the loop-mode bridge table
- **Reviewer(s)**: dyn-loop-integration-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` still pins legacy `LOOP_STATUS=complete → proceed to Gate B` but not the full `STEP3_REVIEW_LOOP_STATUS` bridge or `--mode loop` handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-loop-integration-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] Approval-gates docs omit `postplan-failed`
- **Reviewer(s)**: dyn-loop-integration-output.txt
- **Severity**: latent
- **Concern**: `approval-gates.md` documents several loop outcomes but does not mention `postplan-failed`, so operators relying on that reference lack Gate B skip guidance for the terminal envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-loop-integration-output.txt: Address the concern above.



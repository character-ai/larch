### OOS_9: [OUT_OF_SCOPE] Mixed mechanical rollback test may miss single-job verify failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The mixed mechanical rollback test uses one fixable job and a verify counter. A verify loop that only checks the first job could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a two-job fixture where mechanical verify fails for one job only.



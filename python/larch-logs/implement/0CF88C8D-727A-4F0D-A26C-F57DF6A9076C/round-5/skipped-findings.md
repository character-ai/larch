### FINDING_20: Plan scope does not cover security-classifier changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan forbids vote-tally logic changes, but the branch rewrites `is_security_block` and updates related security/voting docs outside the planned file list. This changes security routing without an explicit plan amendment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.



### FINDING_21: Plan scope does not cover serializer normalization/classification changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan limited normalization to tally and review-and-fix and said `oos-serialize` stays unchanged on the tally-wrote path, but the serializer now normalizes and uses Python security classification on fallback paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.




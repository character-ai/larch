### OOS_1: [OUT_OF_SCOPE] Research-phase cleanup pin is too weak
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The structural test only proves one cleanup line exists, so a future edit could drop one abort branch and still pass the check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pin each research-phase abort branch individually or assert a minimum occurrence count.


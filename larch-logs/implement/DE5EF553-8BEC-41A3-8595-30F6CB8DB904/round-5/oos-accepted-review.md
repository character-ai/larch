### OOS_8: [OUT_OF_SCOPE] risk-integration: SECURITY.md outer-launcher prose outdated after collector cutover
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Outer-launcher security prose still describes filesystem canonicalization to an allowlisted launcher, but the collector now accepts the non-path token agent launch-review and rejects retired shell launcher paths. Operators auditing retry metadata against SECURITY.md may apply the wrong threat model or miss that legacy launcher paths are intentionally rejected after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.



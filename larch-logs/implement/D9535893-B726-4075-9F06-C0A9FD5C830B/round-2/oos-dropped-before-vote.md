### FINDING_4: [OUT_OF_SCOPE] Scope and symlink parity drift
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: nit
- **Concern**: The review notes point at plan/scope items that are not in this branch’s file set, and Step 5 still differs from plan-review on symlinked tmpdirs/result-env handling; that reads as architecture/scope commentary rather than a runtime regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-kv: Address the concern above.


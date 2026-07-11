### OOS_1: [OUT_OF_SCOPE] Shell helper authorization is weaker than Python authorization
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: `check_mutation_auth` in the Bash helper checks only basic file and marker conditions, not the trusted session-root containment and run-identity rules enforced by Python. A direct caller can supply a crafted authorization file outside a live guarded session and reach `gh` operations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-auth-boundary: Route shell validation through the same Python checker (`python/cli.py session check-live-mutation-auth` or equivalent) or duplicate the trusted-root and run-id rules in Bash; reject contexts whose parent is not under the same allowed roots as `is_allowed_session_tmpdir()`.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

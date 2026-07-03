### OOS_1: [OUT_OF_SCOPE] Step 3 `review core` still uses two-token `--run-id`
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-run-log-validator
- **Severity**: nit
- **Concern**: Step 3 `review core` still documents the two-token `--run-id "$RUN_ID"` form, so dash-leading IDs can misparse earlier in `/review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-run-log-validator: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Excluded slug validation remains in `post-tracking-issue.sh`
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-run-log-validator
- **Severity**: nit
- **Concern**: The excluded helper still duplicates slug validation; if parity is required, that gap should be handled in a separate change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-run-log-validator: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Step 4 guard still uses a shell `grep` pipeline
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The guard still uses a `grep` pipeline even though the validator is Python-based, adding an extra shell dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Guard hoisting is still scoped to the scout-manifest block
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `review_run_id_valid` is still computed only inside the scout-manifest bash block while other Step 4 paths read it, so standalone runs can skip transcript/commit work even when `RUN_ID` is valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Missing structural pin for the Step 4 guard pattern
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is still no structural pin that enforces the `run-log validate-run-id` guard pattern or blocks reintroduced inline slug-regex checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Optional acceptance points at an unregistered site
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The optional acceptance prose references a site that is not registered, so operators hit a missing-site error without added signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Quiet-mode coverage misses the end-to-end CLI path
- **Reviewer(s)**: dyn-dyn-run-log-validator
- **Severity**: latent
- **Concern**: Quiet-mode coverage for `validate-run-id` only mocks the entrypoint and asserts `LARCH_QUIET_DISABLE`; it does not verify that the full `cli.main(["run-log", "validate-run-id", "--run-id=-abc123"])` path prints `VALID=true` under inherited quiet mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-log-validator: Address the concern above.


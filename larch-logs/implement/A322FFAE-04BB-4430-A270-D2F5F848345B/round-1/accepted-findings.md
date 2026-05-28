### FINDING_10: Pin harness does not run scanner against production line shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness never runs `check-contains-pins` against the real repo or `test-design-structure.sh`, so CI can pass even if the scanner breaks on the production double-quoted pin shape that motivated the drift fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: TSV paths are not contained to repo root before reads
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest paths are joined as `ROOT/path` without rejecting traversal, absolute paths, or symlink escapes, so lint could read outside the intended tree during CI or fixture runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: Sketch count uses substring semantics despite exact-line documentation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sketch enforcement uses `grep -Fc` substring matching while other modes use exact-line matching, allowing embedded prompt lines to satisfy the count contrary to the documented exact-line contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Harness does not validate expected_count despite shared TSV contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The shared TSV contract says lint and harness reject invalid `expected_count`, but only the lint script validates it; the harness can ingest malformed rows while building fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


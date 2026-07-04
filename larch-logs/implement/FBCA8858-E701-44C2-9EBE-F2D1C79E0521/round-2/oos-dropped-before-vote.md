### OOS_1: [OUT_OF_SCOPE] Legacy TSV header migration skips the append fallback
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Legacy TSV header migration is skipped on the non-fcntl append path. On platforms without fcntl, appending 16-column rows to a 12-column panel-prompt-sizes.tsv can misalign columns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Duplicate env payload parsing helpers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Duplicate env payload parsing helpers instead of reusing tokens._parse_panel_payload_bytes. No current behavioral divergence; only maintenance cost if parsing rules change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Delegate both helpers to read_panel_payload_bytes / _parse_panel_payload_bytes.

### OOS_3: [OUT_OF_SCOPE] Rendering column assertions are missing from materialization tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Panel dispatch materialization tests were not updated to assert scaffold_bytes and payload_bytes columns. Weaker integration regression guard but dedicated column tests exist in test_tokens.py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update materialization harnesses to parse and assert new TSV columns when rows are written.

### OOS_4: [OUT_OF_SCOPE] Voter dispatch payload_files coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Plan-required per-tool payload_files voter dispatch test with differing tool payload counts is still absent. Voter fallback could pick wrong per-tool payload without a plan-review-specific regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a voter dispatch test asserting payload_files map values reach manifest rows and launch env per selected tool.


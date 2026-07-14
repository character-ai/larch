### FINDING_3: [OUT_OF_SCOPE] Documentation disagrees with security classification
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-harness-parity
- **Severity**: minor
- **Concern**: The gate documentation says prose-only `focus-area = security` is not security-routed, but the shared classifier matches that text anywhere in the block. This is a pre-existing contract/runtime mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Fix classifier in a separate change if product intent matches field-line-only security routing.
  - From cursor-specialist-edge-cases: Align doc with review_types.is_security_block_text or fix classifier in a separate change.
  - From dyn-dyn-harness-parity: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Executable-bit checks were removed from smoke coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-harness-parity
- **Severity**: minor
- **Concern**: The delegation smoke no longer verifies that wrapper scripts are executable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a lightweight executable-bit check elsewhere if install hygiene matters.
  - From cursor-specialist-edge-cases: Add [ -x ] checks to smoke or document the omission in the parity map.
  - From dyn-dyn-harness-parity: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Inline-triage integration paths are mocked
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-harness-parity
- **Severity**: minor
- **Concern**: Focused disposition-gate tests mock `_count_inline_triage`, leaving real git range resolution, commit enumeration, and log-body parsing untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add targeted integration tests that fail git subprocess paths without mocking _count_inline_triage directly.
  - From cursor-specialist-testing: Add one integration test with a tmp git repo and real git log commits, or a direct unit test for _count_inline_triage.
  - From dyn-dyn-harness-parity: Add a small git-fixture test (or stop mocking in this case) that commits messages containing two `Inline-triage rule` lines, runs `disposition_gate_main` with that range, and asserts exit `0` without patching `_count_inline_triage`.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Smoke script exceeds the planned size estimate
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The reduced smoke script is approximately 69 lines rather than the planned 30-line target; this is scope drift without a behavioral regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Trim only if maintainers want strict line budget; not required for correctness.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Disposition-gate tests lack explicit shard assignments
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Disposition-gate tests use round-robin fallback because no explicit shard rows exist, consistent with a pre-existing module pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Run rebalance-tests when optimizing shard wall time.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Security routing differs across manifest and disposition surfaces
- **Reviewer(s)**: dyn-dyn-harness-parity
- **Severity**: minor
- **Concern**: `materialize_manifest_oos` uses `_security_signal`, while disposition counting uses `is_security_block_text`, so prose-security cases can behave differently across surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-harness-parity: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

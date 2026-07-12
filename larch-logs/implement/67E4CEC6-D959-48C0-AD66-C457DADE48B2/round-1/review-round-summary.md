# Review Round 1

- Mode: `diff`
- 14 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Invalid metadata fields are accepted or stringified
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Metadata helpers accept invalid non-string or malformed timestamp values, preventing valid fallback candidates from being used and affecting filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_2: Invalid larch versions mask valid fallback versions
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Ground-truth version fallback accepts invalid nonempty versions instead of validating each candidate and continuing to valid alternatives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: First telemetry row is lost when the output file is absent
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Telemetry discovery requires the output file to pre-exist, so the first or only row can be silently omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Lint ratchet misses derived corpus walkers
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: The adoption ratchet does not track corpus provenance through aliases or derived path variables, allowing raw glob, walk, or related traversal calls to bypass diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_5: Validated-run helpers do not prove prior safe-child validation
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Callers can pass the corpus root directly to validated-run walkers and scan outside validated run directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Classification discovery does not reject unsafe TSV paths
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-correctness
- **Severity**: major
- **Concern**: Classification discovery can return symlinked or non-regular TSV files, allowing scanners to read out-of-tree content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_10: Enumeration errors can be silently ignored
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `Path.glob` enumeration failures may not be reported, causing scanners to treat an unreadable corpus as containing zero runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_11: Recursive traversal can fail open
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Inaccessible descendants are silently skipped, allowing garbage collection to treat incompletely inspected runs as safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_12: Fluff harness lacks required corpus-policy coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The fluff harness lacks fixtures and golden assertions for manifest-only directories, symlinked runs, nested design layouts, and count stability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: Rejected-analysis lacks escaping-child regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Tests cover symlink skipping but not child directories that escape containment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_14: Lint tests lack raw-rglob rejection coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The planned positive test for rejecting raw `rglob` traversal is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_19: Safe walker does not handle symlink-loop resolution errors
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Runtime errors from path resolution can abort scanners instead of producing a structured warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_20: Ground-truth ended-at fallback changes prior semantics
- **Reviewer(s)**: dyn-dyn-corpus-policy
- **Severity**: major
- **Concern**: `continue_on_empty=True` consults `run-manifest.json` after a valid but empty preferred manifest, changing run-end ordering and ground-truth alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-corpus-policy: Call `run_ended_at` with `continue_on_empty=False` from `_ground_truth_run_ended_at`, or add a dedicated helper that matches the old per-candidate semantics (return `updated_at` from the preferred manifest, but do not consult `run-manifest.json` when the preferred object is valid and all three end-timestamp fields are empty). Add a regression test for an empty `{}` `manifest.json` plus populated `run-manifest.json` that asserts `None`, not an alternate-manifest timestamp.


### FINDING_22: Design enumeration bypasses shared manifest policy
- **Reviewer(s)**: dyn-dyn-corpus-policy
- **Severity**: major
- **Concern**: Design run enumeration parses `manifest.json` directly, so malformed or symlinked manifests receive different cutoff and version handling from implement paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-corpus-policy: Route design cutoff/version filtering through `manifest_started` and `manifest_larch_version` (or thin wrappers with the same `manifest_candidates` and fallback flags), and drop `_design_run_manifest` in favor of the shared helpers.

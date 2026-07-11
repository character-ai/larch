### FINDING_5: Snapshot validation does not establish a trusted, consistent snapshot contract
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Snapshot mode selection checks artifact presence but does not fully validate patch contents, patch applicability, required Git HEAD relationships, or downstream use of the validated data. Malformed, tampered, or stale snapshots can reach diff, LOC escalation, cleanup, restoration, or staging paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_15: [OUT_OF_SCOPE] Path-based chmod remains vulnerable to symlink replacement
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: Snapshot permission hardening uses pathname-based `chmod` operations after trusted publication and during recursive hardening. A same-UID symlink swap can redirect chmod to an external file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-artifact-trust: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Patch application uses path-based validation before `git apply`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: `_apply_patch_file` checks patch existence and regular-file status by pathname before invoking `git apply`. A replacement or symlink race can cause `git apply` to consume attacker-controlled content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-artifact-trust: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Stale disposition invalidation depends on error-message text
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: Stale disposition handling classifies `ShipError` instances by matching message substrings. Rewording an error can silently stop invalidation and leave stale disposition artifacts active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-artifact-trust: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Missing effective tmpdir can skip disposition validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: `require_pr_mutation_scope_disposition` returns early when the effective tmpdir is missing or not a directory. Ship-time validation can therefore be skipped even when gate-relevant artifacts are available through `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-artifact-trust: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Orphan disposition can affect link rendering without live coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: An orphan `scope-disposition.json` can still produce a `part-of` link kind without live coverage validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

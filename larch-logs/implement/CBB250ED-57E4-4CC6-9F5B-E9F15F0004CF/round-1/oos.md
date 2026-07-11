### FINDING_3: `disposition_link_kind` can trust orphaned disposition data
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `disposition_link_kind` can load a present `scope-disposition.json` and return `part-of` when live validated coverage is absent or fingerprint-mismatched. An orphan or stale disposition can therefore affect finalize or PR link rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Require live validated coverage before loading disposition for link-kind decisions, and reject present disposition when coverage is absent.
  - From cursor-specialist-edge-cases: Raise ShipError when disposition is present but trusted coverage is absent or fingerprint-mismatched.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Stale disposition routing depends on error-message substrings
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Stale disposition routing parses `ShipError` message substrings, so message rewording could break stale detection and invalidation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Use structured error codes instead of str(exc) substring tests


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Patch application lacks trusted no-follow validation
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-artifact-trust
- **Severity**: minor
- **Concern**: `_apply_patch_file` uses path-based file checks before invoking `git apply`, leaving a replacement race in which a symlinked or otherwise unsafe patch can be applied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Validate patches with trusted_file_present before apply
  - From dyn-dyn-artifact-trust: Re-open each patch through `_open_trusted_regular` (or equivalent) immediately before `git apply`, or copy patch bytes into a trusted temp file and apply from that descriptor-bound path.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: [OUT_OF_SCOPE] PR-body composition uses cwd instead of persisted root
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `compose_pr_body` uses `Path.cwd()` for `repo_root`, so an unusual cwd during ship can skew PR-body disposition rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Thread persisted implement repo root into compose_pr_body


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_4: [OUT_OF_SCOPE] Missing tmpdir can bypass ship-time disposition validation
- **Reviewer(s)**: dyn-dyn-artifact-trust
- **Severity**: major
- **Concern**: `require_pr_mutation_scope_disposition` returns early when `effective_tmpdir` is missing or not a directory, potentially skipping ship-time disposition validation even when gate-relevant artifacts exist elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-artifact-trust: Treat a non-directory tmpdir as an unsafe artifact state and fail closed (or require explicit `repo_root` + validated artifact paths) instead of silently bypassing the PR mutation gate.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### OOS_5: [OUT_OF_SCOPE] Planned consumer migrations and tests are incomplete
- **Reviewer(s)**: dyn-dyn-artifact-trust-codex
- **Severity**: major
- **Concern**: Several production consumer modules and plan-listed test modules were not updated, leaving portions of the trusted-artifact contract unimplemented and untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-artifact-trust-codex: Complete the planned consumer migrations and add the missing regression tests before merge.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true

### OOS_6: [OUT_OF_SCOPE] Snapshot permission hardening is vulnerable to symlink replacement
- **Reviewer(s)**: dyn-dyn-artifact-trust-codex
- **Severity**: minor
- **Concern**: `_harden_pre_coder_snapshot_perms` walks and chmods files through path-based operations. A symlink planted after the root check could cause permissions to be changed on an external same-UID file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-artifact-trust-codex: enumerate only validated contained regular files with no-follow metadata checks and chmod through validated descriptors or immediately revalidate the leaf before applying permissions.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_1: Preserve frozen-only step2-baseline coverage and add live-base coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The planned FakeRunner default change makes symbolic-ref and merge-base resolution succeed by default, so `test_compute_requires_step2_baseline` may succeed without `step2-baseline.txt` or fail with the wrong error. The test must continue to encode the missing-baseline requirement only for frozen fallback, while live-base resolution should be tested separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split coverage: (1) rewrite the test to force symbolic-ref failure (or equivalent frozen-fallback setup) before asserting step2-baseline is required; (2) add a live-base case showing step2-baseline.txt is not required when remote resolution succeeds. Add both to the plan test checklist.
  - From Cursor-Pragmatic: Extend the test-file audit beyond FakeRunner(diff_paths=...) call sites. Rewrite test_compute_requires_step2_baseline to assert step2 is required only on frozen-fallback (symbolic-ref failure) and add coverage that live-base resolution works without step2-baseline.txt.
  - From Cursor-Requirements: Add an explicit test-plan bullet to rewrite this test: configure symbolic-ref failure to enter frozen fallback, then assert step2-baseline is required; add a separate case where symbolic-ref succeeds but merge-base fails and assert loud ShipError instead of frozen fallback.


### FINDING_2: Define FakeRunner’s successful live-base default
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The plan’s FakeRunner contract is inconsistent: existing callers omit `merge_base`, but the detailed requirement says merge-base succeeds only when a SHA is configured. Those callers would unexpectedly enter the merge-base failure path instead of exercising committed-path attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify a non-empty successful default merge-base result for FakeRunner, or define an explicit failure sentinel. Keep failure tests opt-in.


### FINDING_7: Prevent stale sidecar coverage after a later revert
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Permanently trusting every plan path once observed in porcelain recreates churn-as-coverage. If a run observes and commits an edit, then later reverts it and leaves the tree clean, the sticky sidecar can still mark the path covered even though the final branch no longer contains the planned change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Persist verifiable path-state provenance, such as the observed file or deletion signature, and retain a sidecar path only while HEAD or the current worktree matches that observation. Add a regression that observes a fallback edit, commits it, reverts it, clears porcelain, and verifies recomputation removes coverage.



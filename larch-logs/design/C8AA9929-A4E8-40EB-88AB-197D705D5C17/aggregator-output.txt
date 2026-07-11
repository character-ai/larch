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

### FINDING_3: Keep fallback sidecar persistence in compute_coverage
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan requires plan-path-only sidecar persistence and unioning, but `touched_paths_since_baseline` has no plan context. Implementing those requirements there could thread plan state through the helper or persist unfiltered porcelain, expanding the API without changing coverage JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Move sidecar persistence into compute_coverage immediately after _firm_plan_paths and the plan_set intersection: on frozen fallback, intersect porcelain with plan_set, union with stored sidecar plan paths, write back the merged plan-only set, then build touched from that union. Keep touched_paths_since_baseline responsible only for raw committed/porcelain attribution and baseline mode selection.

### FINDING_4: Retain sidecar paths across later live-base recomputation
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: If an initial frozen-fallback computation writes the sidecar, a later fetch or rebase may make the remote symbolic ref resolve. If recomputation then ignores the sidecar and porcelain is clean, touched paths can be cleared after dispatcher commit, causing stale-coverage validation to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify that once the fallback sidecar exists in the implement tmpdir, every later recompute in that run unions sidecar plan paths with porcelain (plus live committed paths when trustworthy), even if symbolic-ref later succeeds. Add a regression test: frozen fallback compute, symref recovery, clean porcelain, record_disposition still matches persisted coverage.

### FINDING_5: Authenticate or safely initialize the fallback sidecar
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A trusted-tmpdir sidecar is path-safe but not necessarily author-authenticated. A pre-seeded sidecar containing all firm plan paths could cause the first frozen-fallback computation to mark unimplemented paths covered and bypass disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: On the first coverage computation, ignore and atomically replace any pre-existing sidecar using only current porcelain plan paths. On later recomputation, accept sidecar paths only when an existing larch-generated coverage artifact binds them to the prior fallback result; otherwise ignore them or fail closed. Add the pre-seeded-sidecar case to the mandated fallback tests.

### FINDING_6: Support phase-specific porcelain in the regression harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The required post-commit fallback regression needs porcelain to be non-empty during the first coverage computation and clean during recomputation, but the current FakeRunner returns fixed status output for every git status call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify that FakeRunner accept per-call or phase-specific porcelain output (or allow swapping runners between calls) so the post-commit sidecar-retention test can model uncommitted plan paths first and an empty status on recomputation.

### FINDING_7: Prevent stale sidecar coverage after a later revert
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Permanently trusting every plan path once observed in porcelain recreates churn-as-coverage. If a run observes and commits an edit, then later reverts it and leaves the tree clean, the sticky sidecar can still mark the path covered even though the final branch no longer contains the planned change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Persist verifiable path-state provenance, such as the observed file or deletion signature, and retain a sidecar path only while HEAD or the current worktree matches that observation. Add a regression that observes a fallback edit, commits it, reverts it, clears porcelain, and verifies recomputation removes coverage.

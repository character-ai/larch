### FINDING_1: FakeRunner must model successful live-base resolution by default
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Existing `diff_paths`-driven tests do not configure symbolic-ref results. If the extended `FakeRunner` defaults symbolic-ref to failure, those tests enter the frozen fallback path, lose committed diff attribution, and report incorrect touched counts or mask live-base regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan requirement: FakeRunner defaults symbolic-ref to a successful selected-remote HEAD (coordinated with merge_base), and only fallback-specific tests override it. Add one regression test that an unconfigured symbolic-ref failure changes touched attribution, and audit all existing FakeRunner(diff_paths=...) call sites.
  - From Cursor-Requirements: In the test plan, require FakeRunner to default successful refs/remotes/origin/HEAD to origin/main (and upstream when forked), default merge-base success when merge_base is set, and only use the conservative fallback path when tests explicitly disable symbolic-ref or merge-base. State that existing diff_paths call sites should keep working without per-test rewrites unless they target fallback behavior.


### FINDING_2: Define authoritative FORKED_TARGET precedence
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: minor
- **Concern**: The plan does not define deterministic precedence when `session-env.sh` and `ship-pr-state.sh` both exist with conflicting `FORKED_TARGET` values. Preferring stale session state can select `origin` instead of `upstream`, producing an incorrect merge base and committed-path attribution during later lifecycle recomputation. The accepted true token and key-level fallback behavior are also underspecified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define and implement an explicit lifecycle precedence, consistent with the repository's state readers: use the later authoritative ship-pr-state.sh value when present, otherwise session-env.sh. Add a conflict test proving the selected remote is deterministic
  - From Codex-Innovation: Use session-env.sh only when the later ship-pr-state.sh is absent. When both exist, make ship-pr-state.sh authoritative or reject conflicting values and fall back conservatively with a diagnostic
  - From Cursor-Pragmatic: Specify one order: read FORKED_TARGET from ship-pr-state.sh when present, else session-env.sh; default false; never os.environ. Mirror that rule in tests for early session-only and later both-files cases.
  - From Codex-Pragmatic: [No proposed resolution provided.]


### FINDING_3: Distinguish unresolved remote refs from merge-base failures
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan collapses symbolic-ref resolution failure and merge-base failure into the same working-tree-only fallback. If the remote default-branch ref resolves but `git merge-base` fails, silently under-counting committed coverage after a clean post-commit tree can produce a false partial-scope disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split outcomes: use working-tree-only attribution only when the default branch ref itself cannot be resolved; if the ref is valid but merge-base fails, fail coverage recompute loudly (ShipError / coverage-recompute-failed) instead of silently under-counting


### FINDING_4: Make frozen fallback tolerate invalid committed diff ranges
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: On the conservative frozen-fallback path, a post-Step-2 rebase or shallow clone can make `baseline..HEAD` invalid. If `touched_paths_since_baseline` raises before consulting porcelain, coverage and disposition fail even when working-tree status still contains the run's plan edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In touched_paths_since_baseline, when baseline provenance is frozen-fallback, skip git diff entirely or treat a non-zero diff as an empty committed set, then always consult porcelain. Add a unit test where merge-base/symbolic-ref fail, diff would error, and modified plan paths exist only in porcelain status_z.


### FINDING_5: Rewrite the fallback baseline regression test
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: minor
- **Concern**: The existing fallback regression test still expects `STEP2BASE..HEAD` committed-path attribution. The proposed frozen-fallback behavior removes or ignores that attribution, so the test must be updated rather than left to encode the old behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit plan step to rewrite or replace test_baseline_falls_back_to_step2_without_origin_main so fallback asserts no committed diff attribution (and working-tree-only paths when porcelain is non-empty)
  - From Cursor-Requirements: Update the test plan to rewrite test_baseline_falls_back_to_step2_without_origin_main to assert no baseline..HEAD diff on fallback, frozen SHA retained only for diagnostics, and touched paths sourced solely from porcelain status_z (including rename/copy cases called out elsewhere).


### FINDING_6: Preserve coverage across post-commit fallback recomputation
- **Reviewer(s)**: Cursor-dyn-Coverage Provenance Auditor
- **Severity**: major
- **Concern**: Frozen-fallback working-tree-only attribution is not monotone across recomputation. Step 2 can compute coverage while plan edits are uncommitted, but dispatcher commit and later `record_disposition` or ship validation can recompute against a clean tree and observe no touched paths. Strict persisted-versus-live coverage checks can then reject or invalidate a valid disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Coverage Provenance Auditor: On frozen fallback, keep touched-path attribution monotone across recomputes: pin first working-tree plan paths in an internal sidecar (plan step 7 allows internal provenance) and union them with later porcelain on recompute; or skip strict load_live_coverage equality when committed attribution is untrustworthy. Add a test that simulates dispatcher commit then scope-disposition record without an explicit coverage argument.


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



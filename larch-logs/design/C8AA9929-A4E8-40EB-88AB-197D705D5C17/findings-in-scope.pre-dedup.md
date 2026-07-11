### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/implement/test_scope_disposition.py:223-233
- **Concern**: Plan omits migrating test_compute_requires_step2_baseline for live-base FakeRunner defaults. Scenario: The plan makes FakeRunner default to successful symbolic-ref and merge-base resolution. test_compute_requires_step2_baseline omits step2-baseline.txt and expects ShipError("step2 baseline missing or unreadable"), but with live-base defaults compute_coverage succeeds and the test fails or loses the frozen-fallback-only contract.
- **Proposed resolution**: Split coverage: (1) rewrite the test to force symbolic-ref failure (or equivalent frozen-fallback setup) before asserting step2-baseline is required; (2) add a live-base case showing step2-baseline.txt is not required when remote resolution succeeds. Add both to the plan test checklist.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_scope_disposition.py
- **Concern**: Complete the FakeRunner default-live-base contract. Scenario: Although the plan says existing FakeRunner(diff_paths=...) tests must retain live-base behavior, its detailed test requirement says merge-base succeeds only when a SHA is configured. Existing callers shown in the repository omit merge_base, so they will enter the new loud merge-base-failure path instead of testing committed-path attribution. This leaves the existing coverage suite broken or unable to verify the live path.
- **Proposed resolution**: Specify a non-empty successful default merge-base result for FakeRunner, or define an explicit failure sentinel. Keep failure tests opt-in.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/scope_disposition.py:313-400
- **Concern**: Pin fallback sidecar read/write to compute_coverage after plan-path intersection. Scenario: Approach item 7 and the touched_paths_since_baseline bullets require persisting only plan paths and unioning them with porcelain plan paths, but touched_paths_since_baseline has no plan_file/plan_paths input today. An implementer following those bullets may thread plan context into touched_paths or persist unfiltered porcelain into the sidecar, adding surface area without changing coverage JSON.
- **Proposed resolution**: Move sidecar persistence into compute_coverage immediately after _firm_plan_paths and the plan_set intersection: on frozen fallback, intersect porcelain with plan_set, union with stored sidecar plan paths, write back the merged plan-only set, then build touched from that union. Keep touched_paths_since_baseline responsible only for raw committed/porcelain attribution and baseline mode selection.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/implement/test_scope_disposition.py:223-233
- **Concern**: Plan audit omits step2-required regression when live-base defaults succeed. Scenario: test_compute_requires_step2_baseline omits step2-baseline.txt and relies on merge-base failure to require step2. After FakeRunner defaults symbolic-ref and merge-base success, compute can succeed without step2 or raise a merge-base ShipError instead of step2-missing, so the test fails or stops encoding frozen-only step2 requirement.
- **Proposed resolution**: Extend the test-file audit beyond FakeRunner(diff_paths=...) call sites. Rewrite test_compute_requires_step2_baseline to assert step2 is required only on frozen-fallback (symbolic-ref failure) and add coverage that live-base resolution works without step2-baseline.txt.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/scope_disposition.py
- **Concern**: Frozen sidecar union is scoped only to the current frozen-fallback branch. Scenario: The plan unions the fallback sidecar only while symbolic-ref fallback is active. Mid-run fetch/rebase can make refs/remotes/<remote>/HEAD resolve after an earlier frozen compute wrote coverage and the sidecar. A later recompute that switches to live attribution and ignores the sidecar can clear touched paths after dispatcher commit and fail load_live_coverage stale checks.
- **Proposed resolution**: Specify that once the fallback sidecar exists in the implement tmpdir, every later recompute in that run unions sidecar plan paths with porcelain (plus live committed paths when trustworthy), even if symbolic-ref later succeeds. Add a regression test: frozen fallback compute, symref recovery, clean porcelain, record_disposition still matches persisted coverage.



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/scope_disposition.py:381-400
- **Concern**: The proposed fallback sidecar lacks a trusted initialization rule. Scenario: The implementer can infer the tmpdir from its manifest and plan paths and pre-create the sidecar with every firm plan path. On the first frozen-fallback computation, reading that file would mark unimplemented paths as covered and bypass disposition. A regular file under the trusted tmpdir is path-safe, but not author-authenticated.
- **Proposed resolution**: On the first coverage computation, ignore and atomically replace any pre-existing sidecar using only current porcelain plan paths. On later recomputation, accept sidecar paths only when an existing larch-generated coverage artifact binds them to the prior fallback result; otherwise ignore them or fail closed. Add the pre-seeded-sidecar case to the mandated fallback tests.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_scope_disposition.py:223-233
- **Concern**: Update test_compute_requires_step2_baseline for the new baseline-resolution split. Scenario: The plan makes FakeRunner default to successful symbolic-ref plus merge-base resolution. This test has no step2-baseline.txt and expects ShipError("step2 baseline missing or unreadable"). After the change it either succeeds without error or fails with a merge-base ShipError, so the regression no longer covers missing frozen-baseline handling.
- **Proposed resolution**: Add an explicit test-plan bullet to rewrite this test: configure symbolic-ref failure to enter frozen fallback, then assert step2-baseline is required; add a separate case where symbolic-ref succeeds but merge-base fails and assert loud ShipError instead of frozen fallback.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_scope_disposition.py:14-53
- **Concern**: Extend FakeRunner for per-call porcelain changes in the post-commit fallback regression. Scenario: The plan mandates a post-commit frozen-fallback regression that clears porcelain after the first coverage compute and recomputes via record_disposition. FakeRunner today returns a fixed status_z for every git status call, so the test cannot simulate dispatcher commit plus clean-tree recomputation.
- **Proposed resolution**: Specify that FakeRunner accept per-call or phase-specific porcelain output (or allow swapping runners between calls) so the post-commit sidecar-retention test can model uncommitted plan paths first and an empty status on recomputation.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:313-400
- **Concern**: The prior accepted monotone-fallback fix is incomplete because the proposed sidecar permanently trusts every plan path once observed in porcelain. Scenario: A later review or repair can revert an initially observed plan-path edit. After that revert is committed and the tree is clean, the sticky sidecar still marks the path covered, so disposition validation can pass although the final branch no longer contains the planned change. This recreates churn-as-coverage using stale run churn instead of upstream churn.
- **Proposed resolution**: Persist verifiable path-state provenance, such as the observed file or deletion signature, and retain a sidecar path only while HEAD or the current worktree matches that observation. Add a regression that observes a fallback edit, commits it, reverts it, clears porcelain, and verifies recomputation removes coverage.




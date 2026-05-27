## Proposed Design Outline

### Goals
- Mirror non-fixable bail behavior between `_verify_failed_jobs_locally` and `run_per_job_local_fix_loop` in `scripts/ship-pr.sh` (Item A).
- Correct two documentation drifts: postmerge-comment path drift (`ship-pr.sh:3169, :3231-3232`, Item B) and `SECURITY.md` defensive-branch invariant (Item C1).
- Close two harness gaps: detached/non-ancestor/non-linear HEAD branches in `lint-fix-loop.sh` (Item C2) and `__EMPTY__` mergeStateStatus recovery in `merge-pr.sh` (Item D3).
- Close two correctness gaps in `merge-pr.sh`: post-force-push BEHIND re-check (Item D1) and named retry constants for 4/3 asymmetry (Item D2).

### Non-goals
- No tmpdir file renames (Item B is comment-text-only, per user clarification).
- No new top-level `SECURITY.md` section; edits stay inside the existing "`lint-fix-loop.sh` coder-owned commits" paragraph.
- No new `MERGE_RESULT` values; D1 reuses existing `main_advanced`.
- No new `BAIL_REASON` tokens; A reuses existing `ci-local-unfixable:<list>` contract.
- No D2/D3 deferral — both included.

### Approach sketch
- A: Replace the `[[ "$class" == "fixable" ]] || continue` guard at `ship-pr.sh:1990` with the `case "$class" in fixable) ... ;; *) unfixable+=("$job_token") ;; esac` pattern from `:2087-2099`. Existing tail handler at `:2058-2069` already emits `BAIL_REASON=ci-local-unfixable:<sanitized>` and `exit 3`.
- B: Update comment text at `ship-pr.sh:3169` and `:3231-3232` to reference `$IMPLEMENT_TMPDIR/summary-final.md` (and note the `larch-logs/.../final-summary.md` mirror).
- C1: Add one sentence to `SECURITY.md`'s `lint-fix-loop.sh coder-owned commits` paragraph noting that the head-changed-after-dispatch defensive failure branches (detached HEAD, non-ancestor, non-linear, merge-commit) remain fail-closed.
- C2: Extend `scripts/test-lint-fix-loop.sh` with cases that exercise the four defensive failure branches at `lint-fix-loop.sh:379-393`.
- D1: Insert a BEHIND re-check at `merge-pr.sh:246` (immediately after `retry_pr_info_unknown_recovery 3`) mirroring the pre-force-push pattern at `:243`.
- D2: Add module-level constants `MERGE_PR_INITIAL_UNKNOWN_RETRIES=4` and `MERGE_PR_POST_PUSH_UNKNOWN_RETRIES=3` near top of `merge-pr.sh`; interpolate into existing call sites (`:149`, `:244`) and error messages (`:160`, `:248`).
- D3: Add `empty_state_recovers_clean` and `empty_state_recovers_behind` cases to `scripts/test-merge-pr.sh:386-420`, symmetric to existing G3/G4 but with `GH_MERGE_STATE=__EMPTY__`.

### Surfaces in scope
- `scripts/ship-pr.sh` (Items A, B)
- `scripts/merge-pr.sh` (Items D1, D2)
- `scripts/lint-fix-loop.sh` (Item C2 fixture preconditions — no production code change for C; harness lives in `scripts/test-lint-fix-loop.sh`)
- `scripts/test-merge-pr.sh` (Item D3)
- `scripts/test-lint-fix-loop.sh` (Item C2)
- `SECURITY.md` (Item C1)
- Sibling `.md` contract files for any `.sh` touched (per `script-md-siblings.md`)

### Open questions
- None.

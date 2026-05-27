# Round 1 — Scope / Requirements Resolutions

## Decision 1: Scope confirmation for the 4-item combine
- **Question**: Are all four items (A, B, C, D) in scope, including the nit-severity sub-items D2 and D3?
- **Resolution**: All four items in scope. D2 (named retry constants) and D3 (transient-empty CLEAN test) both included per Step 1c clarification. Item C contains C1 (SECURITY.md doc) and C2 (detached-HEAD harness). Item D contains D1 (BEHIND re-check), D2 (constants), D3 (CLEAN test).
- **Source**: user (Step 1c)

## Decision 2: Item B fix direction (postmerge comment path drift)
- **Question**: Fix the postmerge comment in `ship-pr.sh:3169` and `:3231-3232` only, or rename the tmpdir file from `summary-final.md` to `final-summary.md`?
- **Resolution**: Fix comment text only — surgical, minimum-change. Update the two comment sites to accurately describe `$IMPLEMENT_TMPDIR/summary-final.md` and clarify that `larch-logs/.../final-summary.md` is the run-log mirror produced by `write-final-report.sh` when not `--comment-only`.
- **Source**: user (Step 1c)

## Decision 3: Item A — exit format on non-fixable rows
- **Question**: What format should `_verify_failed_jobs_locally` use when bailing on non-fixable rows?
- **Resolution**: Mirror the existing `run_per_job_local_fix_loop` pattern at `scripts/ship-pr.sh:2087-2099`. Replace `[[ "$class" == "fixable" ]] || continue` with a `case "$class" in fixable) ... ;; *) unfixable+=("$job_token") ;; esac` block. Reuse the same end-of-function `unfixable` handler at lines 2058-2069 that writes `BAIL_FAILURE_DETAIL_LOG` and emits `BAIL_REASON=ci-local-unfixable:<sanitized>` then `exit 3`. No new code path is needed — the existing tail already handles this case once `unfixable[]` is populated.
- **Source**: codebase (`scripts/ship-pr.sh:1985-2069`, `:2087-2099`)

## Decision 4: Item C1 — SECURITY.md scope
- **Question**: What needs to be added to `SECURITY.md:63-172`? The lint-fix-loop commit-content forbidden-path invariant appears at line 204 already.
- **Resolution**: `SECURITY.md` line 204 already documents the commit-content forbidden-path enforcement ("Accepted committed content is checked against `.gitmodules` and discovered submodule paths..."). The nit gap is the **defensive failure branches** in the `head-changed-after-dispatch` path (detached HEAD, non-ancestor base, non-linear advancement, merge-commit). Add one sentence clarifying that those failure branches remain fail-closed (no commit accepted, no working-tree changes propagated).
- **Source**: codebase (`SECURITY.md:202-204`, `scripts/lint-fix-loop.sh:373-393`)

## Decision 5: Item C2 — harness coverage scope
- **Question**: Which failure branches of the post-dispatch HEAD check need harness coverage?
- **Resolution**: Add cases for the four currently uncovered failure paths: empty `current_head` (line 374-375 — already covered, do not duplicate); non-ancestor `baseline_head` (line 381-383); merge-commit (`current_second_parent` non-empty at line 388-390); branch-switch / non-ancestor parent (line 387-390 path where `current_parent != baseline_head`). Reuse the existing harness style in `scripts/test-lint-fix-loop.sh`.
- **Source**: codebase (`scripts/lint-fix-loop.sh:373-393`)

## Decision 6: Item D1 — Post-force-push BEHIND re-check location
- **Question**: Where to insert the missing BEHIND re-check after `retry_pr_info_unknown_recovery 3`?
- **Resolution**: Insert a BEHIND re-check immediately after the `retry_pr_info_unknown_recovery 3` call at `scripts/merge-pr.sh:244` and **before** the subsequent UNKNOWN check at line 246. Mirror the pre-force-push pattern at line 243-244 of the same script: `if [[ "$MERGE_STATE" == "BEHIND" ]]; then MERGE_RESULT="main_advanced"; ERROR=""; exit 0; fi`. This ensures post-recovery BEHIND short-circuits before CI checks mask main advancement.
- **Source**: codebase (`scripts/merge-pr.sh:240-252`)

## Decision 7: Item D2 — Constants placement and naming
- **Question**: Where and how should the named retry constants live?
- **Resolution**: Declare module-level constants near the top of `scripts/merge-pr.sh` (after the EXIT trap setup, before `refresh_pr_info()`). Names: `MERGE_PR_INITIAL_UNKNOWN_RETRIES=4` and `MERGE_PR_POST_PUSH_UNKNOWN_RETRIES=3`. Add a brief comment block documenting the asymmetry rationale: the initial check has higher retry budget because cold cache requires more propagation tolerance, while the post-push path retries are after a known recent write so 3 suffices. Update existing error messages (line 160 `"after 4 retries"`, line 248 `"after 3 retries post-force-push"`) to interpolate the constant value so the messages stay in sync if constants are later tuned.
- **Source**: codebase (`scripts/merge-pr.sh:86-160, 244-248`)

## Decision 8: Item D3 — `empty→CLEAN` symmetric test case
- **Question**: What test cases should be added to `scripts/test-merge-pr.sh` to cover the `__EMPTY__` recovery path?
- **Resolution**: Add `empty_state_recovers_clean` case symmetric to G3 (`unknown_state_recovers_clean`) but with `GH_MERGE_STATE=__EMPTY__` and `GH_VIEW_SECOND_MERGE_STATE=__EMPTY__`. Also add `empty_state_recovers_behind` symmetric to G4 with the same `__EMPTY__` initial state resolving to BEHIND. Use call number `GH_VIEW_FLIP_AT_CALL=3` consistent with G3/G4. Reuse the existing helper `run_case` and assertion patterns.
- **Source**: codebase (`scripts/test-merge-pr.sh:386-420`)

## Hard constraints (non-negotiable)
- `scripts/ship-pr.sh` is shipped behavior. Item A changes the bail behavior on non-fixable rows — the new `exit 3` path must produce the existing `BAIL_REASON=ci-local-unfixable:<sanitized>` and `BAIL_FAILURE_DETAIL_LOG=...` contract (no new ERROR semantics introduced).
- `scripts/merge-pr.sh` MERGE_RESULT contract (line 29) must not gain new values. Item D1 reuses the existing `main_advanced` value; Items D2-D3 do not affect MERGE_RESULT values.
- `SECURITY.md` edits stay in the existing "lint-fix-loop.sh coder-owned commits" paragraph; do not introduce a new top-level section.
- Test additions must be standalone (no new fixtures beyond env-vars on `run_case`) and must not alter existing G1/G2/G3/G4 assertions.

Resolved 8 decisions.

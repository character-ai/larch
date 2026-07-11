## Goal
Implement issue #6908: [IMPLEMENTING] [BUG] coverage artifact mismatch in teardown after inline ci-fix commit causes missing final report.

## Implementation Plan
## Plan

### Approach

- Keep `load_live_coverage(...)` strict and unchanged for all existing pre-merge callers.
- Treat only the exact stale-live-input failure — `ShipError("coverage artifact does not match live repository inputs")` — as recoverable in post-merge presentation paths.
- Re-raise every other `ShipError`, including partial, malformed, unsafe, missing, inconsistent, or untrusted coverage and disposition artifacts.
- In teardown, preserve the persisted `proceed-partial` decision after a stale-live mismatch by loading and validating the persisted coverage/disposition artifacts without recomputing live coverage. Only rename to `[DONE]` when that persisted disposition is not `"proceed-partial"`.
- Fail closed when recovery cannot load persisted coverage: if `load_coverage(tmpdir)` returns `None` after the exact stale-live mismatch, raise `ShipError` rather than defaulting to `"closes"`.
- In final-report rendering, omit only the optional plan-coverage summary for the exact stale-live mismatch. Do not suppress other validation failures.
- Preserve all pre-merge coverage gates, `disposition_deferred_inventory`, artifact schemas, and report grammar.

## Files to modify/create

### UPDATED: python/larch/state/finalize.py

- Add a narrow local predicate or helper that identifies only the known stale-live-coverage `ShipError` by its canonical message, without treating arbitrary `ShipError` values as recoverable.
- Refactor the done-rename eligibility branch so it:
  1. Calls `scope_disposition.disposition_link_kind(...)` normally.
  2. Re-raises any non-mismatch `ShipError`.
  3. On the exact live-input mismatch, loads persisted coverage with `scope_disposition.load_coverage(tmpdir)`.
  4. Raises `ShipError` if that recovery `load_coverage(tmpdir)` call returns `None`; do not infer `"closes"` without a validated persisted coverage artifact.
  5. Validates the persisted disposition with `scope_disposition.load_disposition(tmpdir, coverage=coverage)`.
  6. Uses `"part-of"` when the persisted record is `proceed-partial`; otherwise uses `"closes"`.
- Require the persisted recovery path to retain normal artifact validation. A missing, partial, malformed, unsafe, inconsistent, or mismatched persisted coverage/disposition artifact must still raise rather than silently selecting `"closes"`.
- Emit a concise breadcrumb only for the stale-live-mismatch recovery path. The breadcrumb must state that live coverage no longer matches repository inputs and that teardown is using the validated persisted disposition.
- Keep the disposition lookup behind the existing non-stalled, not-already-renamed, PR-or-design-only eligibility predicates.
- Preserve the existing stall rename path, successful live `"part-of"` behavior, sentinel creation, log flush, run deactivation, issue URL lookup, and cleanup ordering.

### UPDATED: python/larch/report/final_report.py

- Add the same narrow stale-live-mismatch identification at `_plan_coverage_summary_line(...)`.
- Wrap only `scope_disposition.load_live_coverage(...)`.
- Return `""` only when that call raises the exact `coverage artifact does not match live repository inputs` error.
- Re-raise all other `ShipError` values from live coverage validation.
- Keep the current post-load behavior unchanged: missing repository-root evidence, disposition-without-coverage, malformed disposition, and coverage/disposition mismatch errors remain fail-closed.
- Preserve successful coverage/disposition rendering unchanged.

### UPDATED: python/tests/state/test_finalize.py

- Add a teardown regression where `disposition_link_kind(...)` raises the exact stale-live-coverage mismatch and persisted coverage plus no partial disposition resolves to `"closes"`.
  - Assert the done rename is invoked.
  - Assert teardown reaches later terminal work and returns successfully.
  - Assert the stale-recovery breadcrumb is emitted.
- Add a regression where `disposition_link_kind(...)` raises the exact stale-live mismatch but persisted validated disposition is `proceed-partial`.
  - Assert teardown does not invoke the done rename.
  - Assert later teardown work still completes.
- Add a negative regression where `disposition_link_kind(...)` raises the exact stale-live mismatch but recovery `load_coverage(tmpdir)` returns `None`.
  - Assert `ShipError` propagates.
  - Assert the done rename and successful cleanup path are not reached.
- Add a negative regression where `disposition_link_kind(...)` raises a different `ShipError`, such as an invalid disposition or untrusted coverage error.
  - Assert the error propagates.
- Retain or add direct coverage that a normal successful `"part-of"` result continues to skip the done rename.
- Stub only unrelated teardown side effects as needed so assertions distinguish rename behavior, breadcrumb output, and post-rename cleanup without depending on external `gh` or git behavior.

### UPDATED: python/tests/report/test_final_report.py

- Add a focused helper test where persisted repository-root lookup succeeds and `load_live_coverage(...)` raises the exact stale-live-coverage mismatch.
  - Assert `_plan_coverage_summary_line(...)` returns `""`.
- Add a report-writer regression, if needed beyond the helper test, that verifies `write_final_report(...)` succeeds and writes `summary-final.md` without the plan-coverage line for that exact mismatch.
- Add a negative helper test where `load_live_coverage(...)` raises a different artifact-integrity `ShipError`.
  - Assert `_plan_coverage_summary_line(...)` propagates the error rather than returning `""`.
- Keep existing successful coverage rendering expectations unchanged.

## Edge cases

- No coverage artifact remains a normal empty coverage summary and `"closes"` link kind.
- A valid persisted `proceed-partial` disposition remains `"part-of"` even when live coverage is stale after a post-merge ci-fix commit.
- A stale live fingerprint with a valid persisted non-partial disposition permits the `[DONE]` rename and terminal cleanup.
- A stale live fingerprint during final-report rendering omits only the optional coverage summary line.
- A disposition artifact without trusted coverage, or any malformed/unsafe/partial/inconsistent persisted artifact, remains fail-closed in both teardown recovery and final-report rendering.
- If the exact stale-live mismatch occurs but `load_coverage(tmpdir)` returns `None` during teardown recovery, raise `ShipError` and block done rename and terminal cleanup.
- Stall teardown continues to use the stalled rename path without consulting coverage.
- Runs with `done_rename_applied` continue to skip disposition lookup.
- Unexpected programming errors and non-`ShipError` exceptions remain visible.

## Failure modes

- Broad `except ShipError` handling would hide artifact-integrity failures. Limit recovery to the exact canonical stale-live-input mismatch and test propagation of a different `ShipError`.
- Recovering to unconditional `"closes"` would discard validated `proceed-partial` state. Reconstruct the link kind from persisted coverage and disposition after the known mismatch.
- Treating recovery `load_coverage(tmpdir) is None` as `"closes"` would complete teardown without validated persisted evidence. Raise `ShipError` when recovery cannot load coverage.
- Loading persisted artifacts without passing coverage to `load_disposition(...)` would weaken fingerprint/coverage-file matching. Pass the loaded coverage to retain validation.
- Returning an empty report line for non-mismatch failures would weaken report integrity checks. Re-raise every other coverage-validation error.
- Moving disposition resolution outside the existing done-rename predicates could validate coverage for stalled or already-renamed runs. Keep the new logic inside the current branch.

## Testing strategy

- Run the focused state tests:
  - `python3 -m pytest python/tests/state/test_finalize.py`
- Run the focused report tests:
  - `python3 -m pytest python/tests/report/test_final_report.py`
- Run lint and type checks for the four changed Python files through the repository’s changed-file lint workflow.
- Verify these distinct outcomes:
  - Exact stale live-coverage mismatch with valid persisted non-partial state: final report writes, teardown completes, and done rename is attempted.
  - Exact stale live-coverage mismatch with valid persisted `proceed-partial`: final report writes, teardown completes, and done rename is skipped.
  - Exact stale live-coverage mismatch with missing recovery coverage (`load_coverage` returns `None`): teardown remains fail-closed; done rename and cleanup are blocked.
  - Non-mismatch coverage/disposition `ShipError`: teardown and report generation remain fail-closed.
  - Matching live coverage: normal coverage summary rendering and `"part-of"` behavior are unchanged.

## Scope controls

- Do not change `python/larch/implement/scope_disposition.py`, its `load_live_coverage(...)` strictness, or pre-merge callers.
- Do not add `skip_live_check`, post-merge mode flags, or any validation-bypass parameter.
- Do not recompute or rewrite coverage artifacts after ci-fix commits.
- Do not change PR-body or other pre-merge callers.
- Do not change report grammar or persisted artifact schemas.
- Do not broaden existing error handling outside the two post-merge presentation callers.

confidence: high

## Acceptance

- Run the focused state tests:
  - `python3 -m pytest python/tests/state/test_finalize.py`
- Run the focused report tests:
  - `python3 -m pytest python/tests/report/test_final_report.py`
- Run lint and type checks for the four changed Python files through the repository’s changed-file lint workflow.
- Verify these distinct outcomes:
  - Exact stale live-coverage mismatch with valid persisted non-partial state: final report writes, teardown completes, and done rename is attempted.
  - Exact stale live-coverage mismatch with valid persisted `proceed-partial`: final report writes, teardown completes, and done rename is skipped.
  - Exact stale live-coverage mismatch with missing recovery coverage (`load_coverage` returns `None`): teardown remains fail-closed; done rename and cleanup are blocked.
  - Non-mismatch coverage/disposition `ShipError`: teardown and report generation remain fail-closed.
  - Matching live coverage: normal coverage summary rendering and `"part-of"` behavior are unchanged.

diff_added: 110
diff_deleted: 12
mechanical_churn: false
diff_lines: 122

## Test plan
(no test plan section in plan-file)

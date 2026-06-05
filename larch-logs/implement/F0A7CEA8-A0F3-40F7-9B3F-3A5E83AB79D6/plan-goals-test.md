## Goal
Implement issue #3405: [IMPLEMENTING] [OOS] ci_monitor CI_FIX_REBASE_PENDING vs Python evaluate_failure divergence after cutover\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

### Summary

The bash `ship-pr.sh` keeps a persisted `CI_FIX_REBASE_PENDING` flag: when a CI fix is verified locally but the force-push races/fails, it remembers that and retries only the rebase+push on the next iteration (skipping the fix). The Python port `evaluate_failure` has no such state — a failed push returns `waterfall-failed`/"push failed", which `monitor()` maps to `Outcome.STALLED` (or `fix-exhausted` → `NEEDS_USER_INPUT` when a code fix was attempted).

This is an **intentional** non-port, not a parity gap. Bash is being retired (parity is a non-goal), the Python design is stateless (umbrella #3132: "no persisted state machine"), and rebase is migrating to merge-conflict-only, which removes the defer-rebase-on-behind path that produced the pending state. This plan records that intent in code, pins the end-to-end terminal outcome with a test, and notes the decision in the README. No runtime behavior changes.

### Files to modify/create

#### UPDATED: `python/ci_monitor.py`

Comment-only change. No logic change.

- At the push-failure return inside `run_ci_fix` — the `if not pushed:` branch that returns `FixResult(status="waterfall-failed", detail="push failed")` — add a short comment (about 4-6 lines) explaining that bash's `CI_FIX_REBASE_PENDING` pending-retry fast path is deliberately not ported here.
- Comment content: bash remembers a verified-but-unpushed fix and retries push-only; Python instead returns terminal and lets `evaluate_failure`'s outer waterfall re-attempt the full fix. Reasons: stateless design (#3132), rebase becoming merge-conflict-only, bash retired so no parity. Reference #3405.
- Refer to bash symbols by name (`CI_FIX_REBASE_PENDING`, `_stage_and_push_ci_fixes`), not file:line — follow the same symbol-not-line-number discipline as `.claude/rules/drift-prone-prose-in-docs.md` (that rule's `paths:` covers `docs/**`/`skills/**`/`scripts/**/*.md` but not `python/**`, so it is not auto-injected when editing `.py` files; apply the convention anyway for maintainability).

#### UPDATED: `python/test_ci_monitor.py`

Add one `monitor()`-level test pinning the push-failed terminal outcome.

- New test `test_monitor_push_failed_stalls` (or equivalent intent name).
- **Stub recipe (monitor-level)**: Start from `_status(status="fail")` (same scaffold as `test_monitor_fix_exhausted_needs_user_input` — `gather_status` extracts `failed_run_id` **999** from the failing-check link). Add `gh run view 999` stubs for `--log-failed` and `--json jobs`. Port the vendor-only push-failure delta/`git push` stubs from `test_evaluate_failure_vendor_only_push_failed_stalls`, remapping every `42` → `999` in `gh run view` tuple keys (that evaluate_failure test passes `run_id="42"` explicitly; `monitor()` derives the run id from status). Do **not** copy the evaluate_failure stub map verbatim — leaving `42` keys leaves the 999 stubs unused and the test errors or never reaches push failure.
- Drive `ci_monitor.monitor()` with failing, not-behind CI; vendor fixer produces a delta; `git push` returns rc=1.
- Assert `result.result.outcome == Outcome.STALLED`.
- Assert `monitor()` invoked `gh run view` for run **999** (guards stub-map / run-id drift).
- Docstring: cite #3405 and state the STALLED outcome is intentional — Python does not carry a `CI_FIX_REBASE_PENDING` rebase-pending retry.
- Non-redundant: existing tests pin `evaluate_failure`'s `FixResult.status` (`waterfall-failed` / `fix-exhausted`); no existing `monitor()` test pins the push-failed → `Outcome.STALLED` mapping (the only STALLED monitor test, `test_monitor_timeout_bail_stalled`, reaches STALLED via the iteration-cap bail path, not the push-failure path).

#### UPDATED: `python/README.md`

Add a short "Phase 6 scope note" subsection (mirror the existing "Phase 4 scope note" style).

- 4-6 lines: `ci_monitor.py` deliberately omits bash's `CI_FIX_REBASE_PENDING` pending-retry; the failed-push shape terminates as STALLED by design (stateless, rebase→merge-conflict-only, bash retired). Point at #3405.

### Approach

- Treat #3405 as a "make the intentional divergence explicit and pinned" task, not a behavior fix. The user confirmed: don't port the state machine, no bash parity, minimal Python modification.
- Anchor the code comment at the precise structural point where bash sets the pending flag (the `run_ci_fix` push-failure return), because that is where a future "restore parity" reader would otherwise reintroduce the state.
- Keep the test at `monitor()` level so it pins the end-to-end terminal outcome the OOS names ("STALLED (python)"), which is the gap in current coverage.
- For the new `monitor()` test: use `test_monitor_fix_exhausted_needs_user_input` as the `_status(status="fail")` + run-**999** `gh` scaffold and `test_evaluate_failure_vendor_only_push_failed_stalls` as the vendor push-failure behavior template — merge with **42→999** remapping in all `gh run view` stub keys.
- No sibling `.md` is required: `.claude/rules/script-md-siblings.md` scopes that rule to `scripts/` and `skills/*/scripts/`; `python/` is excluded.

### Edge cases

- Code-fix-attempted vs vendor-only push failure: when a code fix was attempted on a ready log, `evaluate_failure` returns `fix-exhausted` → `NEEDS_USER_INPUT` (already pinned by `test_evaluate_failure_push_failed_routes_fix_exhausted`). The new test targets the vendor-only path → `STALLED`. Keep the new test scoped to the STALLED shape; do not duplicate the `fix-exhausted` assertion.
- Outer-loop retry: a failed push is retried by `evaluate_failure`'s outer waterfall (full fix re-run), not by a push-only fast path. The comment must not imply Python gives up after a single push; it gives up the *pending-retry shortcut*, not the outer retries.
- Monitor stub run id: `_status(status="fail")` pins failed run **999**; evaluate_failure-level tests use explicit `run_id="42"`. Mixing conventions in a `monitor()` test leaves `gh` stubs unused.

### Failure modes

- Test-fixture drift: the new `monitor()` test stubs `git`/`gh` responses. If it under-specifies the stub map or keys `gh run view` to **42** while status supplies **999**, stubs go unused and the test errors or never exercises push failure. Mitigation: `_status(status="fail")` + `gh` stubs for run **999** (per `test_monitor_fix_exhausted_needs_user_input`), port vendor push stubs from `test_evaluate_failure_vendor_only_push_failed_stalls` with **42→999** remapping, assert `gh run view` for 999 ran, and assert the vendor launcher ran.
- Stale pin after the rebase migration: if the separate rebase-only-on-merge-conflict migration later changes this mapping, the pinned STALLED assertion will fail loudly — which is the intended early-warning signal, and the docstring's #3405 reference tells the next editor why it exists.

### Testing strategy

- Add the one `monitor()`-level test above; assert `Outcome.STALLED`.
- Run `make py-test` (pytest) and `make py-lint` (ruff/pylint/pyright) from the repo root. `make lint` does not run these, so run them explicitly.
- No live-path validation needed: `ci_monitor.py` is dev/CI-only until Phase 7 (`LARCH_SHIP_PR_IMPL=python`); a comment + test + README note has zero `/implement` runtime impact.

### Diff size estimate

Comment-only edit to `ci_monitor.py` (~6 lines), one new test in `test_ci_monitor.py` (~45 lines), and a short README note (~6 lines). Small, additive, no deletions.

## Acceptance

- [ ] `python/ci_monitor.py`: a comment at the `run_ci_fix` push-failure return (`if not pushed:` → `waterfall-failed`/"push failed") explains that bash's `CI_FIX_REBASE_PENDING` pending-retry is deliberately not ported (stateless design #3132, rebase→merge-conflict-only, bash retired). No logic change.
- [ ] `python/test_ci_monitor.py`: a new `monitor()`-level test asserts `result.result.outcome == Outcome.STALLED` for the vendor-only push-failed shape; uses `_status(status="fail")` (run 999) with vendor push-failure stubs remapped 42→999; asserts `gh run view` ran for run 999; docstring cites #3405 and the intentional non-port.
- [ ] `python/README.md`: a "Phase 6 scope note" records the deliberate omission of `CI_FIX_REBASE_PENDING` and the STALLED-by-design terminal outcome, pointing at #3405.
- [ ] `make py-test` and `make py-lint` pass from the repo root.
- [ ] No runtime behavior change in `ci_monitor.py`; no live `/implement` path impact (dev/CI-only until Phase 7).

diff_lines: 68

## Test plan
(no test plan section in plan-file)

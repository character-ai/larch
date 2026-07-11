# Discussion Round 1 — issue #6845

Fix the `/design` Step 5c exit-5 publish-failure **reporting/diagnostics path** so a
salvageable run is no longer reported as `unrecoverable` with no diagnostics. The
underlying publish work, the rc-4 fail-closed assessment gate, and the
persist-and-retry recovery all worked; only the diagnostics/reporting/classification
is broken. All five issue fix directions are in scope per operator.

## Decision 1: Failure class when plan already wrote
- **Question**: Fix direction 4 — change the reported class from `unrecoverable` to
  `recoverable` (rename + log-flush resume hint) for runs where `PLAN_WRITE_OK=true`?
  The classifier currently cannot see plan-write success.
- **Resolution**: Include it. Report `recoverable` with a resume hint when the plan
  write already succeeded; populate branch/PR/issue from known state.
- **Source**: user

## Decision 2: Salvage-success auto-amend
- **Question**: Fix direction 5 tail — amend/close the auto-filed failure issue when a
  later salvage in the same session succeeds?
- **Resolution**: Include it. When a salvage later succeeds in the same session,
  amend/close the auto-filed issue. (Exact detection hook is an implementation
  decision for Step 2b, not a scope fork.)
- **Source**: user

## Decision 3: State accuracy repair
- **Question**: Fix direction 3 — rewrite the result env on rc-5 paths, stop
  discarding `_write_result_env` errors, and emit phase-progress markers?
- **Resolution**: Include it. A crash must leave accurate state, not a stale
  refusal env.
- **Source**: user

## Hard constraints (codebase findings)
- **rc-4 fail-closed assessment gate (#6746/#6747) stays untouched.** It is working
  as designed; the documented persist-and-retry recovery must keep working. This fix
  changes only rc-5/terminal diagnostics and classification.
- **Result-env trust contract is preserved.** `.design-publish-result.env` is
  allowlisted, no CR/LF in values, no symlinks, under `DESIGN_TMPDIR`
  (`phase_driver_read_result_env` / `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`). Any new keys
  (`PUBLISH_RC_SOURCE`, phase-progress markers) join the allowlists; they do not
  bypass them. `_write_result_env` failures must surface, not be swallowed.
- **Bounded tails, scrubbed.** `design-publish-tail.failure.log` is already a
  sensitive-corpus source (`_corpus.py:160`); copied stdout/stderr tails must be
  size-bounded and flow through the same sensitive-corpus scrubbing before reaching
  the public auto-issue or run log.
- **Terminal-state tokens stay validated.** New outcome/site/trigger values
  introduced for `recoverable` routing must be valid stall-recovery tokens
  (`_tokens.py`) or the staging validator refuses.

## Non-goals
- Do NOT change `publish_core` retry semantics, the publish logic, or attempt-count
  caps.
- Do NOT change `/implement` `retry_policy` caps or auto-retry behavior — design
  terminal reports are operator-facing, not auto-retried.
- Do NOT touch the rc-4 refusal gates or the persist-and-retry recovery.
- Do NOT change the run-log flush PR machinery itself (it produced PR #6846 fine).

## Must-have requirements
1. On a terminal publish rc (5 and the `publish_rc not in {0,1,3,4}` leg), bounded
   tails of the `larch-publish-stdout.*`/`larch-publish-stderr.*` captures persist
   into `$DESIGN_TMPDIR` (so they flush) and the stderr tail is included in
   `design-publish-tail.failure.log` and the auto-issue failure-detail section.
2. `PUBLISH_RC_SOURCE=exception|returned` plus the first traceback line emitted from
   `_step5c_invoke_publish_core` (distinguishes an exception mapped to rc 5 from a
   returned rc 5).
3. `publish_core` emits phase-progress markers (post-plan-write, post-rename, and the
   log-publish leg) into the result env / a sidecar, rewrites the result env on every
   rc-5 path, and surfaces `_write_result_env` failures instead of discarding them.
4. The classifier gains a publish/rc-5/`publish-tail-failed` pattern (no longer falls
   through to `fallback`); when `PLAN_WRITE_OK=true`, the reported class is
   `recoverable` with a rename+log-flush resume hint, and branch/PR/issue fields are
   populated from known state.
5. When a salvage later succeeds in the same session, the auto-filed failure issue is
   amended/closed (Decision 2).

## Open implementation note (for Step 2b, not a scope fork)
The salvage-success detection hook is unresolved: the auto-issue is filed early in the
terminal path; salvage (central tail-publish upsert and/or a later approved outcome
for the same issue) can land minutes later. Step 2b picks the detection point(s) and
the amend/close shape.

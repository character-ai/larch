### FINDING_1: Step 5c retry references omit the fresh-attempt control
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Authoritative Step 5c retry documentation still invokes bare wrapper relaunches, so completed refusal results may be reattached instead of triggering fresh publishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED:` rows for the four reference files (or a single shared retry-authority file they import) and pin every Step 5c re-run path to the wrapper fresh-attempt flag; keep ordinary first entry on default reattachment.
  - From Cursor-Pragmatic: Update all retry owners, including `approval-gates.md`, `finalize-step5.md`, `decompose-panel.md`, and `validator-failure.md`, to pass the private retry control
  - From Cursor-Requirements: Add `### UPDATED:` rows for `skills/design/references/finalize-step5.md`, `skills/design/references/validator-failure.md` (autofix-ok and Fix-and-retry Step 5c paths), `skills/design/references/approval-gates.md`, and `skills/design/references/decompose-panel.md` (size Override) that pin the wrapper argv token and require it on every documented Step 5c re-run.

### FINDING_2: Step 5c child mode cannot publish adapter merge rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Child mode still uses `exec`, preventing post-Python publication of the Step 5c status envelope to the adapter merge environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace child `exec` with a normal Python invocation, then atomically publish `.design-step5c-status.env` (or equivalent rows) to the injected merge path before exiting; mirror the non-exec terminal-publish pattern planned for Step 3.

### FINDING_3: Step 5c publish-env failure lacks a terminal status envelope
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The `_step5c_safe_publish_env` failure branch can return without authoritative status rows, leaving the adapter with incomplete publish and plan-write results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the planned `design_step5c.py` terminal-envelope work to cover this branch: write a complete refusal/failure status envelope (including `PUBLISH_RC`, `PLAN_WRITE_OK`, `PUBLISH_OK`, `CLEANUP_ELIGIBLE=false`) before returning.

### FINDING_4: Session environment is not available during wrapper parent logic
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: When launchers provide only `--session-env-path`, wrapper parent logic may run before trusted session values are resolved, leaving `DESIGN_TMPDIR` and related routing variables unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Parse the trusted allowlisted session env once and export the validated child environment before daemon start, or pass equivalent explicit bindings to the child. Test launcher-style invocation with DESIGN_TMPDIR unset.
  - From Codex-Pragmatic: Add a shared trusted resolver before parent-only logic, or retain minimal parent rehydration for Steps 3 and 4
  - From Codex-Requirements: Add one trusted pre-wrapper rehydration point, such as the launcher, so parent-only logic receives validated session values before `bgjob adapt` runs.

### FINDING_5: Step 3 resume paths can reattach stale completed results
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Mid-loop Step 3 resumes can encounter an existing terminal result and have `bgjob adapt` reattach it instead of launching the requested fresh phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When `STEP3_REVIEW_HAS_RESUME_STATE=true`, delegate through `bgjob adapt` with `--replace-completed-result` (or an equivalent adapter flag). Keep default reattachment for ordinary duplicate invocations and reentry paths that already clear the result via `plan-review step3-state` / `_step3_clear_downstream_sentinels`. Extend `test-design-step3-review.sh` with a completed-result plus resume-argv case that must launch a new child.
  - From Cursor-Pragmatic: In design-step3-review.sh parent mode, when STEP3_REVIEW_HAS_RESUME_STATE=true pass --replace-completed-result to bgjob adapt (wrapper-private flag, not forwarded to plan-review run). Keep default reattach for duplicate ordinary invocations. Extend test-design-step3-review.sh and test-design-structure.sh to seed a terminal result env with NEXT_ACTION=gate-b, invoke with --starting-round and --phase awaiting-continuation, and assert adapt emits STARTED (fresh child) rather than DONE reattach.

### FINDING_6: Step 3 terminal child failures return the wrong status
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Step 3 child failure paths can publish routing rows but still exit nonzero, causing the orchestrator to ignore the valid `NEXT_ACTION` because it requires `BGJOB_RC=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin in `design-step3-review.sh` / `design-step3-review.md`: after atomically writing required terminal rows (including `NEXT_ACTION=final-summary:*` when applicable) to the adapter merge path, the child must exit 0. Reserve non-zero child rc for merge-publication failures only. Add harness coverage for missing-scope-anchor and panel-init-failed paths asserting `BGJOB_RC=0` plus the expected `NEXT_ACTION` in the bgjob result env.

### FINDING_7: Step 3 re-entry depends on undocumented sentinel clearing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Re-entry correctness depends on `design-step3-entry-state.sh` clearing the prior result before `bgjob adapt`; removing wrapper-local deletion without documenting this dependency risks stale reattachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one line to `design-step3-review.md` and `test-design-structure.sh`: reentry must still run `design-step3-entry-state.sh` (or equivalent sentinel clearing) before `bgjob adapt` so a prior terminal result cannot satisfy a fresh re-run review.

### FINDING_8: New harness is not registered across test and lint surfaces
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The planned harness may be skipped, omitted from Bash linting, or rejected as an unreachable skill script without repository registration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the harness to `.PHONY`, `scripts/residual-bash-paths.txt`, and the existing Makefile-only harness exclusions in `agent-lint.toml` 1. **[risk-integration]** Register the planned Step 4 harness across the repository’s test and lint surfaces. Without these entries, `make lint` or the harness target can fail, or the new adapter test can be silently skipped.

### FINDING_9: Step 3 runtime authority remains stale
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `plan-review-runtime.md` still describes wrapper-local lifecycle management and direct `bgjob start`, conflicting with the planned `bgjob adapt` ownership model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/plan-review-runtime.md` stating parent wrappers delegate to `bgjob adapt`, completed results reattach via adapt `DONE`, fresh launch clears `.completed/step-3` only through `--clear-on-fresh`, and orchestrator continuation still requires `bgjob wait` plus `bgjob/design-step3-review.result.env` parsing.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-design-step3b-tail.sh:1
- **Concern**: [SCOPE-REDUCTION] The plan adds the dedicated Step 4 harness previously classified out of scope. Scenario: This expands the firm diff and Makefile surface beyond the issue’s required structure and fence-shape verification
- **Proposed resolution**: Remove the new harness and Makefile target; keep the required existing harness updates

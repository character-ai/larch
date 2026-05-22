# scripts/lint-fix-loop.sh Contract

`scripts/lint-fix-loop.sh` is the `/implement` and `ship-pr.sh` check-failure
repair helper for Step 3, Step 5 post-review fixes, Step 6, ship-pr
`run_checks_phase`, and ship-pr CI failure recovery.

Flags:

- `--tmpdir IMPLEMENT_TMPDIR`
- `--site step3|step5|step6|ship-pr-ci-initial|ship-pr-ci-merge`
- `--checks-log REDACTED_LOG_FILE`

The checks log must be the redacted log emitted by
`scripts/run-relevant-checks-captured.sh`, not the raw log.

Output is `KEY=value` through `scripts/lib-quiet.sh`:

- `LINT_FIX_STATUS=applied|main-agent-required|failed|no-changes`
- `LINT_FIX_SITE=step3|step5|step6|ship-pr-ci-initial|ship-pr-ci-merge`
- `CODER_TOOL=codex|cursor` when an external coder ran
- `CODER_LOG_FILE=<path>` when an external coder ran
- `LINT_FIX_COMMIT_SHA=<sha>` when the helper committed fixes from a clean pre-dispatch baseline
- `LINT_FIX_RUN_DIR=<path>` for dispatch artifacts
- `FAILURE_REASON=<reason>` on internal helper failures

Behavior:

1. Read `CODEX_PRESENT` and `CURSOR_PRESENT` from
   `$IMPLEMENT_TMPDIR/session-env.sh` using `scripts/read-session-env-key.sh`.
2. If the redacted checks log is empty, emit `LINT_FIX_STATUS=no-changes` and
   exit 0.
3. If neither external coder is present, emit
   `LINT_FIX_STATUS=main-agent-required` and exit 0.
4. Compose a prompt that treats the checks log as untrusted command output and
   asks the external coder to make the minimum repository edits required for
   `scripts/relevant-checks.sh` to pass. The prompt forbids commits; the helper owns any
   allowed commit. Literal ````` fence lines in the log are sanitized before
   embedding.
5. Dispatch Cursor first via `scripts/run-external-agent.sh` when Cursor is
   present; if Cursor is absent or fails and Codex is present, dispatch Codex.
   Both `run_cursor()` and `run_codex()` acquire the
   per-tool KeyChain serial lock (`external_serial_lock_acquire` from
   `scripts/lib-cursor-launcher-common.sh` → `lib-external-launcher-common.sh`)
   immediately before each `run-external-agent.sh` call and release it
   asynchronously via `external_serial_lock_release_after`.
6. Before dispatch, capture the tracked/untracked dirty-tree baseline plus the
   current `HEAD`. After dispatch, fail closed if `HEAD` changed, then
   mechanically revert any `.gitmodules` or checked-out submodule-path edits
   before staging.
7. If dispatch succeeds but there are no post-dispatch paths beyond the
   baseline, emit
   `LINT_FIX_STATUS=no-changes`.
8. If dispatch succeeds and post-dispatch paths exist, emit
   `LINT_FIX_STATUS=applied`. Only when the pre-dispatch baseline was clean may
   the helper stage those delta paths and commit through
   `scripts/git-commit.sh --no-trailer` using
   `Apply relevant-checks fixes (Step 3)`, `(Step 5)`, or `(Step 6)`. If the
   commit path fails after staging, the helper must reset the staged delta
   paths before emitting failure.
9. If every available dispatch path fails, emit `LINT_FIX_STATUS=failed`,
   `FAILURE_REASON=dispatch-failed`, and exit 1.
10. If forbidden path edits are detected post-dispatch, revert them, emit
    `LINT_FIX_STATUS=failed`, and set
    `FAILURE_REASON=forbidden-path-violation`.

The `/implement` orchestrator consumes statuses as follows:

- `applied`: re-run `run-relevant-checks-captured.sh` and keep looping through
  the same step until checks are clean or the run stalls.
- `main-agent-required`: repair with main-agent Edit/Write, then re-run checks
  until clean.
- `no-changes`: re-run checks once so the captured helper remains the source of
  truth; if checks still fail, continue the same step's repair loop.
- `failed`: when `LINT_FIX_SITE=step5`, set `STALL_TRACKING=true` and route to
  Step 16 cleanup; when `LINT_FIX_SITE=step3|step6`, set
  `STALL_TRACKING=true` and route to Step 18 cleanup.

Harness: `scripts/test-lint-fix-loop.sh`.

The submodule-prohibition prompt block is extracted into `scripts/lib-submodule-prohibition.sh`; its harness is `scripts/test-lib-submodule-prohibition.sh`.

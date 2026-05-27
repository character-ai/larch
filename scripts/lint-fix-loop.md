# scripts/lint-fix-loop.sh Contract

`scripts/lint-fix-loop.sh` is the `/implement` and `ship-pr.sh` check-failure
repair helper for Step 3, Step 5 post-review fixes, Step 6, ship-pr
`run_checks_phase`, and ship-pr CI failure recovery.

Flags:

- `--tmpdir IMPLEMENT_TMPDIR`
- `--site step3|step5|step6|ship-pr-ci-initial|ship-pr-ci-merge|ship-pr-ci-per-job`
- `--checks-log REDACTED_LOG_FILE`
- `--target-cmd-args-file PATH` for `--site ship-pr-ci-per-job` only

The checks log must be the redacted log emitted by
`scripts/run-relevant-checks-captured.sh`, not the raw log.

Output is `KEY=value` through `scripts/lib-quiet.sh`:

- `LINT_FIX_STATUS=applied|main-agent-required|failed|no-changes`
- `LINT_FIX_SITE=step3|step5|step6|ship-pr-ci-initial|ship-pr-ci-merge|ship-pr-ci-per-job`
- `CODER_TOOL=codex|cursor` when an external coder ran
- `CODER_LOG_FILE=<path>` when an external coder ran
- `LINT_FIX_DELTA_PATHS_FILE=<path>` when `LINT_FIX_STATUS=applied`
- `LINT_FIX_COMMIT_SHA=<sha>` when the helper committed fixes from a clean
  pre-dispatch baseline or accepted a coder-owned commit
- `LINT_FIX_HEAD_CHANGED=true` when a coder-owned commit was accepted after
  dispatch
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
   For `--site ship-pr-ci-per-job`, the target command is displayed from
   `--target-cmd-args-file`: one argv token per line, leading/trailing
   whitespace stripped, control characters rejected. The joined display string
   is informational only; `ship-pr.sh` executes commands from its fixed
   case-statement dispatcher, not from this file.
5. Dispatch Codex first via `scripts/run-external-agent.sh` when Codex is
   present; if Codex is absent or fails and Cursor is present, dispatch Cursor.
   `run_codex()` runs `codex exec --json --output-last-message "$run_dir/codex.log" -- ...`,
   redirects JSONL stdout to the local-only `$run_dir/codex.events.jsonl`, and
   leaves wrapper diagnostics in `$run_dir/codex.wrapper.log` without JSONL
   bleed. Telemetry parse diagnostics land in the dedicated local-only
   `$run_dir/codex.telemetry.sidecar` so publishable wrapper logs stay free of
   parser spill. It parses that event stream best-effort into the sanitized
   token ledger raw bucket `codex_lint_fix`; telemetry failures never
   overwrite the Codex exit code, and the raw `.events.jsonl` artifact is not
   a committed run-log artifact.
   Both `run_cursor()` and `run_codex()` acquire the
   per-tool KeyChain serial lock (`external_serial_lock_acquire` from
   `scripts/lib-cursor-launcher-common.sh` → `lib-external-launcher-common.sh`)
   immediately before each `run-external-agent.sh` call and release it
   asynchronously via `external_serial_lock_release_after`.
6. Before dispatch, capture the tracked/untracked dirty-tree baseline, the
   current `HEAD`, and the symbolic branch name. After dispatch, unchanged
   `HEAD` follows the working-tree path: mechanically revert any `.gitmodules`
   or checked-out submodule-path edits before staging.
   If `HEAD` changed, accept the new commit only when all three invariants hold:
   the pre-dispatch baseline was clean, the symbolic branch is unchanged, and
   the baseline `HEAD` is an ancestor of the current `HEAD`. Detached `HEAD`,
   branch switches, history rewrites, and dirty-baseline `HEAD` movement still
   fail closed with `FAILURE_REASON=head-changed-after-dispatch`.
7. If dispatch succeeds but there are no post-dispatch paths beyond the
   baseline, emit
   `LINT_FIX_STATUS=no-changes`.
8. If dispatch succeeds and post-dispatch paths exist, or a guarded coder-owned
   commit was accepted, emit `LINT_FIX_STATUS=applied`. Only when the
   pre-dispatch baseline was clean may the helper stage working-tree delta paths
   and commit through
   `scripts/git-commit.sh --no-trailer` using
   `Apply relevant-checks fixes (Step 3)`, `(Step 5)`, or `(Step 6)`. If the
   commit path fails after staging, the helper must reset the staged delta
   paths before emitting failure. For accepted coder-owned commits,
   `LINT_FIX_DELTA_PATHS_FILE` is computed from
   `git diff --name-only <baseline_head>..<current_head>`, `LINT_FIX_COMMIT_SHA`
   is the current `HEAD`, and `LINT_FIX_HEAD_CHANGED=true` is emitted.
9. If every available dispatch path fails, emit `LINT_FIX_STATUS=failed`,
   `FAILURE_REASON=dispatch-failed`, and exit 1.
10. Forbidden paths use prefix semantics: a path equal to a forbidden entry or
    under that entry is forbidden. For accepted coder-owned commits, committed
    content is checked first; a forbidden committed path triggers
    `git reset --hard <baseline_head>` and
    `FAILURE_REASON=forbidden-path-violation`. The helper then still runs the
    working-tree forbidden-path revert, so residual uncommitted `.gitmodules` or
    submodule-path edits are reverted and reported with the same failure reason.

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

`ship-pr.sh:run_per_job_local_fix_loop` is the caller for
`--site ship-pr-ci-per-job`.

The submodule-prohibition prompt block is extracted into `scripts/lib-submodule-prohibition.sh`; its harness is `scripts/test-lib-submodule-prohibition.sh`.

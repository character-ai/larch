# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, version bump, PR body/create, CI polling/fix dispatch, merge, and postmerge finalization (local cleanup + verify-main). Teardown, token-report refresh, and final tracking-issue summary are owned by the prompt-side Step 18 orchestrator, which runs after ship-pr.sh exits with `PHASE=done`.

## Interface

```text
ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--auto-mode true|false] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--resume-phase PHASE]
```

`--no-logs-commit true` suppresses all `larch-log.sh commit` calls in the state machine (the pre-rebase flush in `run_rebase_rebump`, the ci-merge happy-path flush, and the postmerge manifest commit). Log files are still written to `$IMPLEMENT_TMPDIR/larch-logs/` for local inspection; they are simply not committed to the branch. The value is propagated into `finalize-state.sh` so `implement-finalize.sh teardown` also skips its commit. Default: `false`.

`--state-file` must live under `--implement-tmpdir`. If the state file does not exist, the script writes an initial uppercase-key state file atomically.

## State

`ship-pr-state.sh` is plain `KEY=value` text and is never sourced. Required keys include `PHASE`, branch/repo/issue identity, PR fields, bump fields, CI counters, checkpoint fields, and finalizer fields. Every non-comment line must match `^[A-Z_][A-Z0-9_]*=.*$`.

`MERGE_RESULT` is written to state by `run_ci_phase` the moment a merge succeeds (`merged` or `admin_merged`) or when CI reports the branch was already merged (`already_merged`). `scripts/refresh-run-logs.sh` reads this key as its fail-closed post-merge guard; when the key is absent the PR has not merged yet and the helper proceeds.

Checkpoint phases:

- `checks`
- `bump`
- `pr-prep`
- `pr-create`
- `ci-initial`
- `ci-merge`
- `evaluate-failure`
- `postmerge`
- `done`

The script also writes `$IMPLEMENT_TMPDIR/postbump-state.sh` before `implement-finalize.sh postbump` and `$IMPLEMENT_TMPDIR/finalize-state.sh` before `postmerge`.

## Exit Codes

- `0` means complete or a prompt-side checkpoint (`OOS_PENDING=true` or `CI_PASSED=true`).
- `3` means the CI loop needs user input. `BAIL_REASON` and `BAIL_NEEDS_USER_INPUT=true` are written to state.
- `4` means stalled cleanup. `STALL_TRACKING=true` and `STALL_STEP` are written to state.
- `5` means the prompt-side Rebase + Re-bump Sub-procedure must run. `RESUME_PHASE` and `CALLER_KIND` are written to state.
- `6` — transient network failure. Orchestrator retries the same `PHASE` after a short sleep. `BAIL_REASON` carries the underlying network-signature; `STALL_TRACKING=false` distinguishes it from `exit 4`.

## Helper Contracts

`ship-pr.sh` parses stdout envelopes from existing helpers rather than relying only on exit status:

- `run-relevant-checks-captured.sh` success requires `RELEVANT_CHECKS_OK=true`.
- `implement-finalize.sh postbump` uses the last `STATUS=` line.
- `create-pr.sh` emits `PR_NUMBER`, `PR_URL`, `PR_TITLE`, and `PR_STATUS`; existing PRs trigger `gh-pr-body-update.sh`.
- `ci-wait.sh` emits `ACTION`, counters, `FAILED_RUN_ID`, and `BAIL_REASON`.
- `merge-pr.sh` emits `MERGE_RESULT` and `ERROR`.
- Failing helper/tool invocations capture stdout/stderr into
  `$IMPLEMENT_TMPDIR/ship-pr-fail-<phase>-<n>.log` and call
  `append-tool-failure.sh --redact` before the existing retry/stall/continue
  decision. `ship-pr.sh` emits `FAILURE_DETAIL_LOG=<path>` for those
  invocations so callers can inspect the captured details without stdout
  replay. Logging failures are best-effort and do not change phase outcomes.

Transient network classification uses `is_transient_net_signature` from `scripts/lib-net.sh`, sourced fail-closed through the `LARCH_LIB_NET_LOADED` sentinel before any phase logic runs. Matching create-PR, rebase, merge, or CI-bail text exits `6` through `exit_transient_net`; non-matching failures continue through the normal stall or user-input paths.

## Invariants

- After `implement-finalize.sh postbump` completes with `STATUS=ok` or `STATUS=skipped`, `run_bump_phase` emits a human-readable breadcrumb line: `✅ 8: version bump — CURRENT → NEW (TYPE)` on a real bump, or `⏩ 8: version bump status=skip reason=<NONE|forked>` when the bump was skipped. The orchestrator MUST NOT re-emit these lines as text output (issue #1944). See NEVER #11 in `skills/implement/SKILL.md`.
- Postbump conflict preserves `CALLER_KIND=step8b_rebase`.
- `ci-initial` treats `ACTION=merge` as CI passed and exits `0`; `ci-merge` treats it as permission to call `merge-pr.sh`.
- `version_already_published` from `merge-pr.sh` is a recoverable version-race condition. `run_ci_phase` first checks `gh pr view <PR_NUMBER> --json state`; when GitHub reports `MERGED`, the script treats the result as `already_merged`, marks `PR_CLOSED=true`, and advances to `postmerge` without re-bumping. If the PR is not merged or the probe fails, it calls `run_rebase_rebump "$phase"` and returns 0 so the outer loop re-enters `ci-wait.sh`; the existing `REBASE_COUNT >= 20` guard in `ci-decide.sh` bounds the retry budget.
- After `apply-bump.sh` succeeds inside `run_rebase_rebump`, the PR title is updated via `gh pr edit --title "Bump version to <new-version>"` (best-effort, skipped when no PR yet) and the `version-bump-reasoning` larch-log batch is overwritten with the new reasoning file so the audit trail reflects the actually-landed version rather than the original race target.
- After argument validation, ship-pr.sh runs `export IMPLEMENT_TMPDIR` so child processes inherit the session tmpdir path for non-log behavior even when ship-pr.sh is invoked from a fresh shell where the orchestrator environment was not inherited. `larch-log.sh` receives its staging root explicitly via `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`.
- At the start of `ci-merge` phase (after the `REPO_UNAVAILABLE` early-return block), ship-pr.sh calls `larch-log.sh commit --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id <RUN_ID>` (best-effort) to flush pending larch-log writes before merge. This covers `version-bump-reasoning`, `oos-issues`, `run-statistics`, `token-report`, `timing-report`, and `execution-issues` batches written after the pre-bump log flush. The rebase-rebump sub-procedure step 1b performs the same flush on any rebase path; this covers the happy path where no rebase was needed. The commit is pushed so it lands in the PR before `merge-pr.sh` is called; push failure is non-fatal. This flush retains a direct push (rather than `--no-push`) because `merge-pr.sh` requires `local HEAD == remote PR headRefOid` and an unpushed local commit would fail that check. Flush errors surface to stderr (stderr is no longer suppressed) so diagnostic information is preserved.
- Fork mode skips bump application and uses direct `rebase-push.sh --base-remote upstream --base-ref main`.
- `run_evaluate_failure` retries the vendor fix locally up to 3 times before stalling. Each attempt calls the vendor tool and runs local checks; only when local checks pass does it commit and push to CI. `FIX_ATTEMPTS` is incremented once per successful push (not per local attempt).
- State writes use `tmp.$$` plus `mv`.
- The local execution-issue logger resolves the log root from the state file's
  `IMPLEMENT_TMPDIR` key when present, falling back to the validated
  `--implement-tmpdir` argument. The state file is parsed with `read_state`;
  it is never sourced.

## Postmerge Phase

`run_postmerge_phase` calls `implement-finalize.sh postmerge` (Steps 14+15: local cleanup and verify-main), then finalizes the larch-log manifest (`status=done`, `pr_number=N`) and commits+pushes the update to main (best-effort, errors swallowed). Before the final status update, it probes `$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/manifest.json`; when missing, it runs `larch-log.sh init` and tags the synthesized manifest with `status=partial` plus `recovery_reason=manifest_lost_mid_run` so a partial run-log directory is not committed without a manifest. This post-postmerge manifest flush runs inside the ship-pr.sh subprocess so the manifest is finalized even when the LLM session ends before prompt-side Step 18 teardown. This flush retains a direct push (rather than `--no-push`) because it is the last opportunity to persist the manifest to the remote when the LLM session ends before prompt-side Step 18. Token-report refresh, `larch:final-summary` upsert, session-transcript commit, and tmpdir teardown still run in the prompt-side Step 18 orchestrator; the teardown manifest update there is an idempotent no-op when ship-pr.sh already pushed the done manifest. `$IMPLEMENT_TMPDIR` remains intact for Step 18 to use.

## Log Refresh

`scripts/refresh-run-logs.sh` re-renders `token-report` and `timing-report` larch-log batches and commits the updated files before each push, so the PR's committed logs always reflect the most recent run state. It is called at three trigger points:

- **Trigger A** (`run_rebase_rebump`): after re-bump, before `git-force-push.sh`.
- **Trigger B** (`run_ci_fix_vendor`): after fix commit, before `git-push.sh`.
- **Trigger C** (`run_bump_phase`): after bump block, before `write_postbump_state`.

All three calls use `|| true` so refresh failure is non-fatal. The helper exits 0 with no commit when `MERGE_RESULT=merged|admin_merged` is in state, and also when the state file is missing (fail-closed).

## Harness

`scripts/test-ship-pr.sh` runs offline state/transition coverage with stubbed helpers. Its disposable repositories copy both `ship-pr.sh` and `lib-net.sh` so the sourced-library contract is exercised. It is wired through `make test-ship-pr`.

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, or state keys, update `skills/implement/SKILL.md`, `scripts/test-ship-pr.sh`, `scripts/test-implement-structure.sh`, and this file together.

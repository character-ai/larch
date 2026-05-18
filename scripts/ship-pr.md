# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, version bump, PR body/create, CI polling/fix dispatch, merge, and postmerge finalization (local cleanup + verify-main). Teardown, token-report refresh, and final tracking-issue summary are owned by the prompt-side Step 18 orchestrator, which runs after ship-pr.sh exits with `PHASE=done`.

## Interface

```text
ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--auto-mode true|false] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--resume-phase PHASE]
```

`--no-logs-commit true` is exported as `LARCH_NO_LOGS_COMMIT=true` so child lifecycle helpers suppress explicit larch-log commit calls. Log files are still written to `$IMPLEMENT_TMPDIR/larch-logs/` for local inspection; they are simply not committed to the branch by `ship-pr.sh` lifecycle flush points. Default: `false`.

`--state-file` must live under `--implement-tmpdir`. If the state file does not exist, the script writes an initial uppercase-key state file atomically.

## State

`ship-pr-state.sh` is plain `KEY=value` text and is never sourced. Required keys include `PHASE`, branch/repo/issue identity, PR fields, bump fields, CI counters, checkpoint fields, and finalizer fields. Every non-comment line must match `^[A-Z_][A-Z0-9_]*=.*$`.

`MERGE_RESULT` is written to state by `run_ci_phase` the moment a merge succeeds (`merged` or `admin_merged`), when CI reports the branch was already merged (`already_merged`), or when `merge-pr.sh` returns `version_already_published` and `gh pr view` confirms the PR is `MERGED` (also set to `already_merged`). Immediately before advancing to `postmerge`, the script also writes `$IMPLEMENT_TMPDIR/post-merge-sentinel`. `scripts/refresh-run-logs.sh` reads `MERGE_RESULT` as its fail-closed post-merge guard, while `scripts/larch-log-flush.sh` and `scripts/larch-log.sh commit` use the sentinel to suppress any remaining post-merge log commits.

On every merge-success path (`merged`, `admin_merged`, and all `already_merged` variants), `BAIL_REASON`, `STALL_TRACKING`, and `STALL_STEP` are cleared in state (`"" false ""` respectively) before advancing to `postmerge`. This prevents stale stall-state from a prior `ci-merge` failure from propagating into `$IMPLEMENT_TMPDIR/final-bail-reason.txt` and `$IMPLEMENT_TMPDIR/finalize-state.sh` via `write_finalize_state()`: `BAIL_REASON` is written to the former, while `STALL_TRACKING`/`STALL_STEP` are written to the latter. Leaving those stale values in place would otherwise cause `implement-finalize.sh postmerge` to skip local branch cleanup (via `bail_reason_nonempty()`) and `implement-finalize.sh teardown` to write a false stall sentinel.

The two `run_ci_phase` skip-paths that advance directly to `postmerge` without merging — the `REPO_UNAVAILABLE=true`/missing-`PR_NUMBER` else-branch and the skip-merge guard (`MERGE!=true`, `DRAFT=true`, or `FORKED_TARGET=true` during `ci-merge`) — also call `clear_stall_keys_for_postmerge()` before advancing. This is necessary because those branches also bypass the merge-success clears, and stale `BAIL_REASON`/`STALL_TRACKING`/`STALL_STEP` can persist there, especially after resuming from an earlier `ci-merge` stall.

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

The script also writes `$IMPLEMENT_TMPDIR/postbump-state.sh` before `implement-finalize.sh postbump` and `$IMPLEMENT_TMPDIR/finalize-state.sh` before `postmerge`. The finalize-state key order is shared with `scripts/restore-finalize-state.sh` through `scripts/lib-finalize-state-keys.sh`.

## Exit Codes

- `0` means complete or a prompt-side checkpoint (`OOS_PENDING=true`). `CI_PASSED=true` is internal state recorded when green CI is observed; it is not an exit-0 checkpoint because `ci-initial` now continues into `ci-merge` in the same invocation.
- `3` means the CI loop needs user input. `BAIL_REASON` and `BAIL_NEEDS_USER_INPUT=true` are written to state.
- `4` means stalled cleanup. `STALL_TRACKING=true` and `STALL_STEP` are written to state. When `STALL_STEP=12d` (merge-pr policy/admin/error branch), the script appends a "DO NOT improvise recovery" orchestrator directive to the `$fail_file` so any reader of the failure detail log sees the correct recovery path. Exception: `MERGE_RESULT=error` whose text matches "local HEAD … does not match PR head OID" is classified as recoverable divergence and routes to `run_rebase_rebump` instead of stalling.
- `5` means the prompt-side Rebase + Re-bump Sub-procedure must run. `RESUME_PHASE` and `CALLER_KIND` are written to state.
- `6` — transient network failure. Orchestrator retries the same `PHASE` after a short sleep. `BAIL_REASON` carries the underlying network-signature; `STALL_TRACKING=false` distinguishes it from `exit 4`.

## Helper Contracts

`ship-pr.sh` parses stdout envelopes from existing helpers rather than relying only on exit status:

- `run-relevant-checks-captured.sh` success requires `RELEVANT_CHECKS_OK=true`. When checks fail during `run_checks_phase`, the phase calls `scripts/lint-fix-loop.sh --site ship-pr-ci-initial` to dispatch a Codex/Cursor coder for repairs (up to 3 fix dispatches); every `LINT_FIX_STATUS=applied` is followed by a verification run, including after the third/final dispatch; on `failed`, `main-agent-required`, or a structural failure (no `REDACTED_LOG_FILE` in output), the phase falls back to `exit_stall 6`.
- `implement-finalize.sh postbump` uses the last `STATUS=` line.
- `create-pr.sh` emits `PR_NUMBER`, `PR_URL`, `PR_TITLE`, and `PR_STATUS`; existing PRs trigger `gh-pr-body-update.sh`.
- `ci-wait.sh` emits `ACTION`, counters, `FAILED_RUN_ID`, and `BAIL_REASON`.
- `merge-pr.sh` emits `MERGE_RESULT` and `ERROR`.
- `run_rebase_rebump` version-regression correction: after `classify-bump.sh` emits `NEW_VERSION`, the function reads `origin/main:.claude-plugin/plugin.json` and checks whether `NEW_VERSION < origin/main version` (semver). When true — the conflict resolver chose the branch's stale version instead of main's — `new_version` is recomputed as `BUMP_TYPE` applied to origin/main's version (e.g., `29.1.39 → 29.3.1` when origin/main is `29.3.0` and `BUMP_TYPE=PATCH`). The correction is recorded as a `WARN:` line in `$fail_file`. `apply-bump.sh` also rejects `NEW_VERSION < ORIGIN_VERSION` as a belt-and-suspenders guard.
- Failing helper/tool invocations capture stdout/stderr into
  `$IMPLEMENT_TMPDIR/ship-pr-fail-<phase>-<n>.log` and call
  `append-tool-failure.sh --redact` before the existing retry/stall/continue
  decision. `ship-pr.sh` emits `FAILURE_DETAIL_LOG=<path>` for those
  invocations so callers can inspect the captured details without stdout
  replay. Logging failures are best-effort and do not change phase outcomes.

Transient network classification uses `is_transient_net_signature` from `scripts/lib-net.sh`, sourced fail-closed through the `LARCH_LIB_NET_LOADED` sentinel before any phase logic runs. Matching create-PR, rebase, merge, or CI-bail text exits `6` through `exit_transient_net`; non-matching failures continue through the normal stall or user-input paths.

## Invariants

- `run_rebase_rebump` bounds infinite rebase storms from concurrent merges to main with `REBASE_COUNT >= 5`. On exhaustion it stalls with `STALL_STEP=10-max-retries` for `ci-initial` or `STALL_STEP=12-max-retries` for `ci-merge`. If `git symbolic-ref HEAD` fails before the rebase call, it stalls with `STALL_STEP=10-detached-head` or `STALL_STEP=12-detached-head` respectively.
- `run_evaluate_failure` retries `run_ci_fix_vendor` up to 5 times with jittered backoff (~2s/4s/8s/16s ±25%) between attempts, with a detached-HEAD check before each attempt. If `FAILED_RUN_ID` is empty it stalls immediately with the legacy phase token: `STALL_STEP=10` for `ci-initial`, `STALL_STEP=12c` for `ci-merge`. This missing-run-id path is the sole remaining legacy exception; retry exhaustion and detached-HEAD now use the hyphenated tokens listed above.
- `run_pr_create_phase` derives the PR title from the branch range (`merge-base..HEAD`, falling back to all of `HEAD` when `git merge-base` fails), skipping subjects whose prefix matches `^chore(larch-logs): flush` followed by a space (larch-log flush commits produced by `larch-log-flush.sh`). The first non-matching subject becomes the title; fallback is `"Implement requested changes"` when no non-flush commit exists in the range. After the PR is created (and its body updated when it already existed), the phase writes `pr_number` to the larch-log manifest via `larch-log.sh manifest --field pr_number=N` (which also bumps `updated_at`) and commits the updated manifest with `larch-log.sh commit` when `LARCH_NO_LOGS_COMMIT` is not `true`. Both calls are best-effort; failures are recorded under `Warnings`.
- After `implement-finalize.sh postbump` completes with `STATUS=ok` or `STATUS=skipped`, `run_bump_phase` emits a human-readable breadcrumb line: `✅ 8: version bump — CURRENT → NEW (TYPE)` on a real bump, or `⏩ 8: version bump status=skip reason=<NONE|forked>` when the bump was skipped. The orchestrator MUST NOT re-emit these lines as text output (issue #1944). See NEVER #11 in `skills/implement/SKILL.md`.
- Postbump conflict preserves `CALLER_KIND=step8b_rebase`.
- `ci-initial` treats `ACTION=merge` as CI passed, writes `CI_PASSED=true`, advances to `ci-merge`, and returns to the internal loop in the same `ship-pr.sh` invocation. `ci-merge` then treats `ACTION=merge` as permission to call `merge-pr.sh`.
- `version_already_published` from `merge-pr.sh` is a recoverable version-race condition. `run_ci_phase` first checks `gh pr view <PR_NUMBER> --json state`; when GitHub reports `MERGED`, the script treats the result as `already_merged`, marks `PR_CLOSED=true`, and advances to `postmerge` without re-bumping. If the PR is not merged or the probe fails, it calls `run_rebase_rebump "$phase"` and returns 0 so the outer loop re-enters `ci-wait.sh`; `run_rebase_rebump` itself now enforces the 5-attempt cap before stalling.
- Every merge-success branch writes `$IMPLEMENT_TMPDIR/post-merge-sentinel` before `advance_phase postmerge`, so postmerge and prompt-side teardown cannot create or push larch-log-only commits to main. Failure to write the sentinel stalls fail-closed instead of entering postmerge without the guard.
- After `apply-bump.sh` succeeds inside `run_rebase_rebump`, the PR title is updated via `gh pr edit --title "Bump version to <new-version>"` (best-effort, skipped when no PR yet) and the `version-bump-reasoning` larch-log batch is overwritten with the new reasoning file so the audit trail reflects the actually-landed version rather than the original race target.
- After argument validation, ship-pr.sh runs `export IMPLEMENT_TMPDIR` so child processes inherit the session tmpdir path for non-log behavior even when ship-pr.sh is invoked from a fresh shell where the orchestrator environment was not inherited. It also exports `LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"` so explicit log commit helpers invoked inside the subprocess tree can suppress best-effort log commits when requested.
- Fork mode skips bump application and uses direct `rebase-push.sh --base-remote upstream --base-ref main`.
- `run_evaluate_failure` downloads the failed run logs, then may attempt up to 5 vendor-fix-and-push retries in the current invocation, with jittered backoff between attempts. Any resulting local check failures route through `scripts/lint-fix-loop.sh` with `--site ship-pr-ci-initial` for `ci-initial` or `--site ship-pr-ci-merge` for `ci-merge`. The helper may dispatch up to 3 lint-fix repairs, with a verification run after each applied fix, before the current vendor attempt fails. `FIX_ATTEMPTS` is incremented once per successful push.
- Operator compatibility note: downstream automation that keyed only on legacy `STALL_STEP=10` or `STALL_STEP=12c` must also accept `10-max-retries`, `12-max-retries`, `10-detached-head`, and `12-detached-head`. `10` and `12c` remain the missing-`FAILED_RUN_ID` stall codes only.
- `run_ci_fix_vendor` and the conflict-resolution branch of `run_rebase_rebump` resolve the design plan via `resolve_plan_file()`, which reads `PLAN_FILE` from `$IMPLEMENT_TMPDIR/session-env.sh` without sourcing it, validates the path is under `$IMPLEMENT_TMPDIR` (rejects paths outside to prevent arbitrary local-file reads), and verifies the file exists. When a valid path is resolved, `--plan-file` is forwarded to the Cursor/Codex CI launcher so external agents preserve the design plan while fixing CI or resolving conflicts. Path violations and missing files are logged to `execution-issues.md` under `Warnings`.
- `run_ci_fix_vendor` runs `git add -u` before `git-commit.sh` when a dirty tree is detected. `git diff --quiet HEAD` detects both staged and unstaged changes, but `git-commit.sh` with no file arguments only commits staged ones; the `git add -u` step stages all tracked modified/deleted files to close the scope mismatch and prevent a dirty-tree stall on the next pass.
- State writes use `tmp.$$` plus `mv`.
- The local execution-issue logger resolves the log root from the state file's
  `IMPLEMENT_TMPDIR` key when present, falling back to the validated
  `--implement-tmpdir` argument. The state file is parsed with `read_state`;
  it is never sourced.

## Postmerge Phase

`run_postmerge_phase` calls `implement-finalize.sh postmerge` (Steps 14+15: local cleanup and verify-main), then finalizes the staged larch-log manifest (`status=done`, `pr_number=N`) best-effort. Before the final status update, it probes `$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/manifest.json`; when missing, it runs `larch-log.sh init` and tags the synthesized manifest with `status=partial` plus `recovery_reason=manifest_lost_mid_run` so partial run-log directories remain identifiable. It does not create a dedicated log-flush commit; log commits are produced by explicit lifecycle flush points before postmerge. Token-report refresh, `larch:final-summary` upsert, session-transcript capture, and tmpdir teardown still run in the prompt-side Step 18 orchestrator. `$IMPLEMENT_TMPDIR` remains intact for Step 18 to use.

## Log Refresh

`scripts/refresh-run-logs.sh` re-renders `token-report` and `timing-report` larch-log batches and commits the updated files before each push, so the PR's committed logs always reflect the most recent run state. It is called at three trigger points:

- **Trigger A** (`run_rebase_rebump`): after re-bump, before `git-force-push.sh`.
- **Trigger B** (`run_ci_fix_vendor`): after fix commit, before `git-push.sh`.
- **Trigger C** (`run_bump_phase`): after bump block, before `write_postbump_state`.

All three calls use `|| true` so refresh failure is non-fatal. The helper exits 0 with no commit when `MERGE_RESULT=merged|admin_merged|already_merged` is in state, and also when the state file is missing (fail-closed).

## Harness

`scripts/test-ship-pr.sh` runs offline state/transition coverage with stubbed helpers. Its disposable repositories copy `ship-pr.sh`, `lib-net.sh`, and `lib-finalize-state-keys.sh` so sourced-library contracts are exercised. It is wired through `make test-ship-pr`.

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, or state keys, update `skills/implement/SKILL.md`, `scripts/test-ship-pr.sh`, `scripts/test-restore-finalize-state.sh`, `scripts/test-implement-structure.sh`, and this file together.

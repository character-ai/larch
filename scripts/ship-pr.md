# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, version bump, PR body/create, CI polling/fix dispatch, merge, and postmerge finalization (local cleanup + verify-main). Prompt-side Step 18 still owns teardown, token-report refresh, and the remaining terminal safety-net work after `ship-pr.sh` exits with `PHASE=done`. On merged PR paths, `run_postmerge_phase` runs **before** that exit: it re-runs `write-final-report.sh` (full pass, not `--comment-only`) so `final-summary.md` and the `larch:final-summary` tracking-issue comment reflect `MERGE_RESULT`. No post-merge git commit is made (see `skills/implement/SKILL.md` NEVER #19).

## Interface

```text
ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--branch-name VALUE] [--expected-session-id VALUE] [--expected-tmpdir-basename-prefix VALUE] [--force-init-state true|false] [--issue-number VALUE] [--manifest-path VALUE] [--run-id VALUE] [--tool-label VALUE] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--resume-phase PHASE]
```

`--no-logs-commit true` is exported as `LARCH_NO_LOGS_COMMIT=true` so child lifecycle helpers suppress explicit larch-log commit calls. Log files are still written to `$IMPLEMENT_TMPDIR/larch-logs/` for local inspection; they are simply not committed to the branch by `ship-pr.sh` lifecycle flush points. Default: `false`.

`--state-file` must live under `--implement-tmpdir`. If the state file does not exist (or `--force-init-state true`), the script writes an initial uppercase-key state file atomically.

## State-File Argv Init

On cold start (no state file yet, or `--force-init-state true`), `ship-pr.sh` writes the state file itself via `write_initial_state()` before entering the main loop. Optional argv supplies caller-varying keys:

| Argv flag | State key |
| --- | --- |
| `--branch-name` | `BRANCH_NAME` |
| `--issue-number` | `ISSUE_NUMBER` |
| `--run-id` | `RUN_ID` |
| `--manifest-path` | `MANIFEST_PATH` |
| `--tool-label` | `TOOL_LABEL` |
| `--expected-session-id` | `EXPECTED_SESSION_ID` |
| `--expected-tmpdir-basename-prefix` | `EXPECTED_TMPDIR_BASENAME_PREFIX` |

`--force-init-state` accepts `true` or `false` (default `false`). When `true` and a state file already exists, `write_initial_state()` runs again and replaces the file (stalled-run cleanup); routine Step 8+ invocations omit this flag.

**Set vs omitted**: internally each per-key flag uses paired `INIT_*` / `INIT_*_SET` variables. If the flag appears in argv (including with an explicit empty value), that exact value is written to state. If the flag is omitted, the historical auto-derivation in `write_initial_state()` applies (`git` for `BRANCH_NAME`, env and tmpdir-derived defaults for the others).

**Resume precedence**: when the state file already exists, argv per-key values are ignored and on-disk state wins, unless `--force-init-state true`.

**`NO_LOGS_COMMIT` in state**: `write_initial_state()` also emits `NO_LOGS_COMMIT`, `IMPLEMENT_TMPDIR`, and `BAIL_FAILURE_DETAIL_LOG=` lines for heredoc parity. `ship-pr.sh` still treats `--no-logs-commit` and `--implement-tmpdir` argv as authoritative on every invocation (including resume); the state-file copies are informational.

**Backward compatibility**: callers that pre-compose `ship-pr-state.sh` and invoke `ship-pr.sh` without the new flags are unchanged — the writer is skipped when the file exists and `--force-init-state` is not `true`.

**Schema note**: `skills/implement/SKILL.md` echoes the full key list; `write_initial_state()` is the runtime source of truth. The `require_key` loop validates the full key set written by `write_initial_state()`, so mid-session `ship-pr.sh` upgrades against a state file produced by an older version may need `--force-init-state true` to regenerate the file. Drift-detection automation between the writer and docs is out of scope for issue #2742 (issue #2753).

## State

`ship-pr-state.sh` is plain `KEY=value` text and is never sourced. Required keys include `PHASE`, branch/repo/issue identity, PR fields, bump fields, CI counters, checkpoint fields, and finalizer fields. Every non-comment line must match `^[A-Z_][A-Z0-9_]*=.*$`.

`MERGE_RESULT` is written to state by `run_ci_phase` the moment a merge succeeds (`merged` or `admin_merged`), when CI reports the branch was already merged (`already_merged`), or when `merge-pr.sh` returns `version_already_published` and `gh pr view` confirms the PR is `MERGED` (also set to `already_merged`). Immediately before advancing to `postmerge`, the script also writes `$IMPLEMENT_TMPDIR/post-merge-sentinel`. `scripts/refresh-run-logs.sh` reads `MERGE_RESULT` as its fail-closed post-merge guard. `scripts/larch-log-flush.sh`, `scripts/refresh-run-logs.sh`, and ordinary `scripts/larch-log.sh commit` callers treat the sentinel plus default-branch cleanup as **hard stops** so prompt-side/teardown paths do not keep pushing larch-log-only commits after merge. No exception exists for `run_postmerge_phase` — the commit prohibition is unconditional (see `skills/implement/SKILL.md` NEVER #19).

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
- `3` means the CI loop needs user input or orchestrator follow-up. `BAIL_REASON` is written to state. Most exit-3 reasons also set `BAIL_NEEDS_USER_INPUT=true`. The **`first-fixer-non-health`** bail (Cursor CI-fix launcher reported `LAUNCHER_FAILURE_CLASS=other`) exits **`3`** but leaves **`BAIL_NEEDS_USER_INPUT=false`** so `/implement` Step 8+ can run the autonomous main-agent CI-fix sub-procedure in `skills/implement/SKILL.md` before any `AskUserQuestion` path.
- `4` means stalled cleanup. `STALL_TRACKING=true` and `STALL_STEP` are written to state. When `STALL_STEP=12d` (merge-pr policy/admin/error branch), the script appends a "DO NOT improvise recovery" orchestrator directive to the `$fail_file` so any reader of the failure detail log sees the correct recovery path. Exception: `MERGE_RESULT=error` whose text reports a local/PR-head OID mismatch is classified as recoverable divergence only when the reported PR head OID is still an ancestor of the current local `HEAD`; that case routes to `run_rebase_rebump` instead of stalling. Second exception: `MERGE_RESULT=admin_failed` whose `ERROR` text contains `"Base branch was modified"` is also classified as a recoverable race condition (main advanced between the last rebase and the merge attempt); that case also routes to `run_rebase_rebump` so the branch is rebased, re-bumped, and re-queued for CI rather than stalling at 12d. The rebase cap is 20 (raised from 5 to accommodate busy repos where main advances frequently). Same-version mechanical recovery and non-bump rebase conflicts are handled in-script (mechanical retries and `run_recovery_waterfall`); exhaustion surfaces here as `exit 4` with `RESUME_PHASE` / `CALLER_KIND` set where the state machine still needs an orchestrator resume (for example `RESUME_PHASE=ship-pr-rrr-phase14`).
- `5` — orchestrator-owned Rebase + Re-bump Sub-procedure handoff for postbump rebase conflicts. `run_bump_phase` emits this exit when `implement-finalize.sh postbump` returns `STATUS=conflict` with `RESUME_PHASE=force-push-gate` (origin/main advanced past the branch's bump base while the run was at the version-bump phase). State carries `RESUME_PHASE=force-push-gate` and `CALLER_KIND=step8b_rebase`; `STALL_TRACKING` stays `false`. The orchestrator's Exit 5 handler (see `skills/implement/SKILL.md`) reads those keys and invokes the Rebase + Re-bump Sub-procedure to drop the stale bump commit, re-rebase cleanly, re-classify against the refreshed `origin/main`, re-apply the bump, then re-invoke `ship-pr.sh --resume-phase force-push-gate`; on re-entry `run_bump_phase` runs again with a fresh classify/apply/check and `implement-finalize.sh postbump` hits the `.postbump-phase` checkpoint to do phase 4 (force-push) only. Fixed by issue #2707; before the fix this conflict was incorrectly routed to an inline force-push-gate handler that produced a false success and stalled at step 8b.
- `6` — transient network failure. Orchestrator retries the same `PHASE` after a short sleep. `BAIL_REASON` carries the underlying network-signature; `STALL_TRACKING=false` distinguishes it from `exit 4`.

## Helper Contracts

`ship-pr.sh` parses stdout envelopes from existing helpers rather than relying only on exit status:

- `run-relevant-checks-captured.sh` success is a clean envelope on exit `0`: `RELEVANT_CHECKS_OK=true` **or** `RELEVANT_CHECKS_SKIPPED=true` (same predicate as `is_relevant_checks_clean` in `ship-pr.sh`). When checks fail during `run_checks_phase`, the phase calls `scripts/lint-fix-loop.sh --site ship-pr-ci-initial` to dispatch a Codex/Cursor coder for repairs (up to 3 fix dispatches); every `LINT_FIX_STATUS=applied` is followed by a verification run, including after the third/final dispatch; on `failed`, `main-agent-required`, or a structural failure (no `REDACTED_LOG_FILE` in output), the phase falls back to `exit_stall 6`.
- `implement-finalize.sh postbump` uses the last `STATUS=` line.
- `create-pr.sh` emits `PR_NUMBER`, `PR_URL`, `PR_TITLE`, and `PR_STATUS`; existing PRs trigger `gh-pr-body-update.sh`.
- `ci-wait.sh` emits `ACTION`, counters, `FAILED_RUN_ID`, and `BAIL_REASON`. When `ci-decide.sh` hits the `FIX_ATTEMPTS >= 10` safety cap, the forwarded `BAIL_REASON` is the exact token **`fix-attempts-exhausted`**, which `needs_user_bail_reason` maps to exit **`3`** (operator input). That is orthogonal to autonomous vendor-fix exhaustion in `run_evaluate_failure`, which stalls with exit **`4`** and `STALL_STEP=10-max-retries` for `ci-initial`.
- `merge-pr.sh` emits `MERGE_RESULT` and `ERROR`.
- `run_rebase_rebump` version-regression correction: after `classify-bump.sh` emits `NEW_VERSION`, the function reads `origin/main:.claude-plugin/plugin.json` and checks whether `NEW_VERSION < origin/main version` (semver). When true — the conflict resolver chose the branch's stale version instead of main's — `new_version` is recomputed as `BUMP_TYPE` applied to origin/main's version (e.g., `29.1.39 → 29.3.1` when origin/main is `29.3.0` and `BUMP_TYPE=PATCH`). The correction is recorded as a `WARN:` line in `$fail_file`. `apply-bump.sh` also rejects `NEW_VERSION < ORIGIN_VERSION` as a belt-and-suspenders guard.
- Failing helper/tool invocations capture stdout/stderr into
  `$IMPLEMENT_TMPDIR/ship-pr-fail-<phase>-<n>.log` and call
  `append-tool-failure.sh --redact` before the existing retry/stall/continue
  decision. `ship-pr.sh` emits `FAILURE_DETAIL_LOG=<path>` for those
  invocations so callers can inspect the captured details without stdout
  replay. Logging failures are best-effort and do not change phase outcomes.

Transient network classification uses `is_transient_net_signature` from `scripts/lib-net.sh`, sourced fail-closed through the `LARCH_LIB_NET_LOADED` sentinel before any phase logic runs. Matching create-PR, rebase, merge, or CI-bail text exits `6` through `exit_transient_net`; non-matching failures continue through the normal stall or user-input paths.

## Recovery waterfall (`run_recovery_waterfall`)

Several failure classes attempt **three-tier** vendor recovery before the historical `exit_stall` handoff: `launch-cursor-ci.sh`, then `launch-codex-ci.sh`, then `launch-claude-ci.sh` (each tier runs only when the corresponding `cursor` / `codex` / `claude` binary exists on `PATH`). **`run_ci_fix_vendor` is special:** when the **first** tier (`cursor`) fails with `LAUNCHER_FAILURE_CLASS=other` (non-health launcher failure), `ship-pr.sh` records `BAIL_REASON=first-fixer-non-health`, skips Codex/Claude for that attempt, and returns early so `run_evaluate_failure` can exit **3** for the `/implement` Step 8+ autonomous path — health-class failures (`health`, missing class, `none` on non-zero exits misclassified as health, etc.) still fall through to Codex/Claude. Call sites include: checks log resolution failures and post-lint exhaustion in `run_checks_phase`, the OOS disposition gate in `run_pr_prep_phase`, `write-final-report.sh` / `create-pr.sh` failures in `run_pr_create_phase`, and **non-bump-only** `rebase-push.sh --keep-on-conflict` conflicts in `run_rebase_rebump`.

Each tier snapshots `HEAD` plus tracked/untracked dirty paths, runs the launcher (`--role fix` or `--role resolve-conflict`; the rebase path passes `--conflict-files` from `LARCH_WF_CONFLICT_CSV` when set) with optional `--failure-log` when the capture file already lives under `$IMPLEMENT_TMPDIR`, then runs a **phase-specific verifier** (relevant-checks capture for the checks phase via `verify_kind=checks-step6` / `run-relevant-checks-captured.sh`; **pr-prep** via `verify_kind=pr-prep-oos` by re-invoking `oos-disposition-gate.sh`, not the checks capture helper; `write-final-report.sh` / `create-pr.sh` probe, or `git rebase --continue` plus `_run_rebase_rebump_verify_plain_no_push`). Failed tiers roll back via `recovery_waterfall_paths_delta_revert` using `while IFS= read -r path` and quoted `git restore --staged -- "$path"` / `git checkout -- "$path"` / `rm -f -- "$path"` so paths with spaces or glob characters cannot word-split. When every tier fails, the caller `exit_stall`s with the same step tokens as before the waterfall.

`RESUME_PHASE=ship-pr-rrr-phase14` is **not** a no-op: resuming advances the state machine and re-enters `run_rebase_rebump` so the tail of the rebase/rebump procedure can finish after operator intervention.

## Invariants

- `run_rebase_rebump` bounds infinite rebase storms from concurrent merges to main with `REBASE_COUNT >= 5`. On exhaustion it stalls with `STALL_STEP=10-max-retries` for `ci-initial` or `STALL_STEP=12-max-retries` for `ci-merge`. If `git symbolic-ref HEAD` fails before the rebase call, it stalls with `STALL_STEP=10-detached-head` or `STALL_STEP=12-detached-head` respectively.
- `run_evaluate_failure` retries the vendor waterfall (`run_ci_fix_vendor`) up to **3** times with jittered backoff (~2s/4s ±25%; 8s/16s ladder entries exist for higher caps but are unused at `_max_fix=3`) between attempts. Each attempt first refreshes `gh-run-logs.sh` capture for the failed run id; when that helper exits **3** (run still in progress), the attempt **skips** `run_ci_fix_vendor` entirely and only applies backoff so CI can finish. When logs are available (`gh-run-logs` exit 0), `run_ci_fix_vendor` runs a **3-tier inner waterfall** (Cursor → Codex → Claude, one launch per tier) and pipes the captured log through `scripts/redact-secrets.sh` before passing **`--failure-log`** to each launcher — raw captures are never forwarded. A detached-HEAD check runs before each outer attempt. If `FAILED_RUN_ID` is empty it stalls immediately with the legacy phase token: `STALL_STEP=10` for `ci-initial`, `STALL_STEP=12c` for `ci-merge`. This missing-run-id path is the sole remaining legacy exception; retry exhaustion and detached-HEAD now use the hyphenated tokens listed above. Worst-case launcher volume per phase is **3 outer × 3 tiers = 9** `launch-*-ci.sh` calls (down from 5×3 single-vendor attempts = 15). Local check remediation routes through `scripts/lint-fix-loop.sh` with `--site ship-pr-ci-initial` or `--site ship-pr-ci-merge`; `FIX_ATTEMPTS` increments once per successful fix push.
- `run_pr_create_phase` derives the PR title from the branch range (`merge-base..HEAD`, falling back to all of `HEAD` when `git merge-base` fails), skipping subjects whose prefix matches `^chore(larch-logs): flush` followed by a space (larch-log flush commits produced by `larch-log-flush.sh`). The oldest non-matching subject becomes the title; when `ISSUE_NUMBER` is set in state, the title is prefixed with `Fixes #N:` followed by a space. Fallback is `"Implement requested changes"` when no non-flush commit exists in the range. Before `create-pr.sh`, the phase writes placeholder `final-summary.md` content; a failure there stalls PR creation. When that write succeeds, the phase commits the run-log tree via `larch-log.sh commit` when `LARCH_NO_LOGS_COMMIT` is not `true`, so `create-pr.sh`'s push carries the committed summary onto the remote PR tip. After the PR is created (and its body updated when it already existed), the phase re-runs `write-final-report.sh --comment-only` to refresh only the tracking-issue comment with the live PR URL. The pre-PR `larch-log.sh commit` and the post-create comment refresh are best-effort warnings only.
- After `implement-finalize.sh postbump` completes with `STATUS=ok` or `STATUS=skipped`, `run_bump_phase` emits a human-readable breadcrumb line: `✅ 8: version bump — CURRENT → NEW (TYPE)` on a real bump, or `⏩ 8: version bump status=skip reason=<NONE|forked>` when the bump was skipped. The orchestrator MUST NOT re-emit these lines as text output (issue #1944). See NEVER #11 in `skills/implement/SKILL.md`.
- **`bump-branch-guard` stall** — at the start of `run_bump_phase`, before classify/apply bump work, the script compares `read_state BRANCH_NAME` to the current symbolic branch from `git symbolic-ref -q --short HEAD` (empty when detached or not on a branch). If `BRANCH_NAME` is empty, the current name is empty, or the names differ, it records `STALL_STEP=bump-branch-guard`, `STALL_TRACKING=true`, and exits `4` with failure detail in the bump capture file. When `read_state BRANCH_NAME` is `main` or `master`, the same stall applies **unless** `read_state FORKED_TARGET` is `true` **and** the symbolic branch still matches `BRANCH_NAME` (forked upstream-target runs may legitimately use the default branch name while staying aligned with state; see `scripts/test-ship-pr.sh` `bump_forked_main_ok`). This runs on every `run_bump_phase` entry (including `--resume-phase bump` resumes) so a version bump cannot apply on the wrong branch.
- Postbump conflict preserves `CALLER_KIND=step8b_rebase` and `RESUME_PHASE=force-push-gate` in state, then exits 5 for the orchestrator's Exit 5 Rebase + Re-bump Sub-procedure handoff (see Exit Codes above and issue #2707). `_run_force_push_gate_mechanically` is no longer invoked from `run_bump_phase`'s `conflict)` branch — calling it before the sub-procedure drops the stale bump commit and re-rebases produces a false success (the absent-remote branch in `check-remote-branch.sh` clears the `.postbump-phase` checkpoint) and re-enters the same conflict on the next postbump call.
- `ci-initial` treats `ACTION=merge` as CI passed, writes `CI_PASSED=true`, advances to `ci-merge`, and returns to the internal loop in the same `ship-pr.sh` invocation. `ci-merge` then treats `ACTION=merge` as permission to call `merge-pr.sh`.
- `version_already_published` from `merge-pr.sh` is a recoverable version-race condition. `run_ci_phase` first checks `gh pr view <PR_NUMBER> --json state`; when GitHub reports `MERGED`, the script treats the result as `already_merged`, marks `PR_CLOSED=true`, and advances to `postmerge` without re-bumping. If the PR is not merged or the probe fails, it calls `run_rebase_rebump "$phase"` and returns 0 so the outer loop re-enters `ci-wait.sh`; `run_rebase_rebump` itself now enforces the 5-attempt cap before stalling.
- Every merge-success branch writes `$IMPLEMENT_TMPDIR/post-merge-sentinel` before `advance_phase postmerge`, so prompt-side teardown, `refresh-run-logs.sh`, and other incidental `larch-log.sh commit` paths cannot create or push larch-log-only commits to `main` / the default branch. No exception exists for `run_postmerge_phase`; the `larch-log.sh commit` rejection is unconditional after the sentinel is present (see `skills/implement/SKILL.md` NEVER #19). Failure to write the sentinel stalls fail-closed instead of entering postmerge without the guard.
- After `apply-bump.sh` succeeds inside `run_rebase_rebump`, the PR title is updated via `gh pr edit --title "Bump version to <new-version>"` (best-effort, skipped when no PR yet) and the `version-bump-reasoning` larch-log batch is overwritten with the new reasoning file so the audit trail reflects the actually-landed version rather than the original race target.
- After argument validation, ship-pr.sh runs `export IMPLEMENT_TMPDIR` so child processes inherit the session tmpdir path for non-log behavior even when ship-pr.sh is invoked from a fresh shell where the orchestrator environment was not inherited. It also exports `LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"` so explicit log commit helpers invoked inside the subprocess tree can suppress best-effort log commits when requested.
- Fork mode skips bump application and uses direct `rebase-push.sh --base-remote upstream --base-ref main`.
- Operator compatibility note: downstream automation that keyed only on legacy `STALL_STEP=10` or `STALL_STEP=12c` must also accept `10-max-retries`, `12-max-retries`, `10-detached-head`, and `12-detached-head`. `10` and `12c` remain the missing-`FAILED_RUN_ID` stall codes only.
- `run_ci_fix_vendor` and the conflict-resolution branch of `run_rebase_rebump` resolve the design plan via `resolve_plan_file()`, which prefers `PLAN_FILE` from `$IMPLEMENT_TMPDIR/session-env.sh` when set (read without sourcing), validates the path is under `$IMPLEMENT_TMPDIR` (rejects paths outside to prevent arbitrary local-file reads), and verifies the file exists. When `PLAN_FILE` is absent or invalid, the helper falls back to `$IMPLEMENT_TMPDIR/plan.txt` when that file exists. When a valid path is resolved, `--plan-file` is forwarded to the Cursor, Codex, and Claude CI launchers so external agents preserve the design plan while fixing CI or resolving conflicts. Path violations and missing files are logged to `execution-issues.md` under `Warnings`.
- `run_ci_fix_vendor` stages CI fix commits via `collect_ci_stage_paths` and `git add -- "${stage_paths[@]}"` (explicit paths from vendor dirty snapshots plus lint-fix deltas), not `git add -u`.
- State writes use `tmp.$$` plus `mv`.
- The local execution-issue logger resolves the log root from the state file's
  `IMPLEMENT_TMPDIR` key when present, falling back to the validated
  `--implement-tmpdir` argument. The state file is parsed with `read_state`;
  it is never sourced.

## Postmerge Phase

`run_postmerge_phase` calls `implement-finalize.sh postmerge` (Steps 14+15: local cleanup and verify-main), then finalizes the staged larch-log manifest (`status=done`, `pr_number=N`) best-effort. Before the final status update, it probes `$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/manifest.json`; when missing, it runs `larch-log.sh init` and tags the synthesized manifest with `status=partial` plus `recovery_reason=manifest_lost_mid_run` so partial run-log directories remain identifiable. **Fail-closed ordering**: the final `larch-log.sh manifest` (`status=done` + `pr_number`) must exit zero before `write-final-report.sh` runs. A non-zero manifest exit skips the report. Post-merge `write-final-report.sh` failures whose captured output matches `is_transient_net_signature` exit the phase with code `6` via `exit_transient_net` (same contract as pre-PR `run_pr_create_phase`). After the manifest reaches `status=done` and the report succeeds, `write-final-report.sh` (without `--comment-only`) updates `final-summary.md` for the merged outcome (`MERGE_RESULT` is already in `ship-pr-state.sh`) and upserts the tracking-issue final-summary comment. No post-merge `larch-log.sh commit` is performed (NEVER #19 in `skills/implement/SKILL.md`). Session-transcript capture is owned by Step 7a and earlier `scripts/refresh-run-logs.sh` retries before each push; Step 18 is reserved for prompt-side teardown and the remaining terminal refresh/safety-net work. `$IMPLEMENT_TMPDIR` remains intact for Step 18 to use.

Schema note: v2 flushed run snapshots often omit `pr_number` and `status` until merge. **`ship-pr.sh` postmerge is the intentional merge-time writer** of `status=done` and `pr_number` on the tmpdir manifest under `$IMPLEMENT_TMPDIR` when `PR_CLOSED=true` — do not assume those keys are absent from the postmerge tmpdir tree. Git-committed run-log snapshots on the branch (including historical tips) may still omit them: NEVER #19 forbids a post-merge `larch-log.sh commit`, so merge-finalized manifest keys are not published to the default branch via a post-merge log commit; rely on tmpdir manifests, `write-final-report.sh` output, or the tracking-issue comment when diagnosing merge completion.

## Log Refresh

`run_pr_create_phase` writes and commits the placeholder `final-summary.md`
before `create-pr.sh` so the remote PR tip includes the same run-log tree as
the local branch on the first push. After `PR_NUMBER`/`PR_URL` are persisted,
it re-runs `write-final-report.sh --comment-only` to refresh the tracking
comment via API only; that second pass does not commit or push.

`scripts/refresh-run-logs.sh` re-renders `token-report`, `timing-report`, and `session-transcript` before each push, then commits the updated run-log tree, so the PR's committed logs always reflect the most recent run state. It is called at three trigger points:

- **Trigger A** (`run_rebase_rebump`): after re-bump, before `git-force-push.sh`.
- **Trigger B** (`run_ci_fix_vendor`): after fix commit, before `git-push.sh`.
- **Trigger C** (`run_bump_phase`): after bump block, before `write_postbump_state`.

All three calls use `|| true` so refresh failure is non-fatal. The helper exits 0 with no commit when `MERGE_RESULT=merged|admin_merged|already_merged` is in state, and also when the state file is missing (fail-closed).

## Harness

`scripts/test-ship-pr.sh` runs offline state/transition coverage with stubbed helpers. Its disposable repositories copy `ship-pr.sh`, `lib-net.sh`, and `lib-finalize-state-keys.sh` so sourced-library contracts are exercised. It is wired through `make test-ship-pr-state`, `make test-ship-pr-postmerge`, and `make test-ship-pr-fix-loop`; running `bash scripts/test-ship-pr.sh` executes the full harness locally.

## Breadcrumb Stream

When `LARCH_QUIET_BREADCRUMBS=1` is exported (set by the `/implement` Step 8+ invocation in `skills/implement/SKILL.md`), `ship-pr.sh` emits single-line progress breadcrumbs to FD 3 (caller-visible stdout) at major phase boundaries and snag points via `emit_breadcrumb` from `lib-quiet.sh`:

- `→ ship-pr: <phase>` — positive phase-entry (checks, version bump, PR prep, opening PR, CI watch, postmerge)
- `→ ship-pr: PR #N opened` — after PR creation
- `→ ship-pr: CI green` — after CI passes in the initial phase
- `→ ship-pr: merged` — after the PR is merged
- `⚠ ship-pr: CI failed; dispatching fix` — on CI failure before vendor dispatch
- `⚠ ship-pr: rebase + re-bump` — on rebase + re-bump entry
- `⚠ ship-pr: merge conflict on rebase` — when a rebase fails with a non-transient conflict
- `⚠ ship-pr: transient network failure` — on every `exit_transient_net` call
- `⛔ ship-pr: stalled at step N` — on every `mark_stall` call (covers all `exit_stall` codes)

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, or state keys, update `skills/implement/SKILL.md`, `scripts/test-ship-pr.sh`, `scripts/test-restore-finalize-state.sh`, `scripts/test-implement-structure.sh`, and this file together.

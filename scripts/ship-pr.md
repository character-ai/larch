# ship-pr.sh

`scripts/ship-pr.sh` is the mechanical state machine for the post-review tail of `/implement`: relevant checks, postbump ship (force-push / run-log refresh — no per-PR version bump in Phase 1 of issue #3364), PR body/create, CI polling/fix dispatch, merge, and postmerge finalization (local cleanup + verify-main). Prompt-side Step 18 still owns teardown, token-report refresh, and the remaining terminal safety-net work after `ship-pr.sh` exits with `PHASE=done`. On merged PR paths, `run_postmerge_phase` runs **before** that exit: it re-runs `write-final-report.sh` (full pass, not `--comment-only`) so `final-summary.md` and the `larch:final-summary` tracking-issue comment reflect `MERGE_RESULT`. No post-merge git commit is made (see `skills/implement/SKILL.md` NEVER #19).

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

**Backward compatibility**: optional argv flags only apply when `ship-pr.sh` creates the state file on cold start (see the table above). Callers who **hand-compose** `ship-pr-state.sh`—minimal files or external tooling—must satisfy the same full key set enforced by the `require_key` loop as `write_initial_state()` emits, not merely the argv-shaped subset; compose against `write_initial_state()` / `skills/implement/SKILL.md` before first use, or pass `--force-init-state true` to regenerate when keys are missing (including after upgrading `ship-pr.sh` mid-run against a file written by an older version). When a state file **already exists** and `--force-init-state` is not `true`, the writer is skipped regardless of argv, so pre-composed on-disk state remains authoritative on resume.

**Schema note**: `skills/implement/SKILL.md` echoes the full key list; `write_initial_state()` is the runtime source of truth. The `require_key` loop validates the full key set written by `write_initial_state()` **before** the main loop consumes state, so the schema contract applies at hand-off and composition time—not only after mid-session binary upgrades. Mid-session `ship-pr.sh` upgrades against a state file produced by an older version may need `--force-init-state true` to regenerate the file. Drift-detection automation between the writer and docs is out of scope for issue #2742 (issue #2753).

## State

`ship-pr-state.sh` is plain `KEY=value` text and is never sourced. Required keys include `PHASE`, branch/repo/issue identity, PR fields, CI counters, checkpoint fields, and finalizer fields (Phase 1 #3364 removed `HAS_BUMP` / `BUMP_TYPE` / `NEW_VERSION` from the state file; `postbump-state.sh` still carries stub bump keys for `implement-finalize.sh postbump`). Every non-comment line must match `^[A-Z_][A-Z0-9_]*=.*$`.

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

## Errexit invariant

`ship-pr.sh` runs with `set -uo pipefail` (nounset and pipefail on; errexit intentionally off — no `set -e`) by design: helper outcomes are read from stdout envelopes and explicit `rc` captures. Any `set +e` … gate/helper block must **restore the prior errexit state** via the save/restore idiom (`case $- in *e*) had_errexit=1 ;; esac` before `set +e`, then `(( had_errexit )) && set -e` after `rc=$?`) — never an unconditional trailing `set -e`. Unconditional restore leaks errexit into later CI phases and can abort the script with a raw helper exit code outside the documented orchestrator table below.

## Exit Codes

- `0` means complete or a prompt-side checkpoint (`OOS_PENDING=true`). `CI_PASSED=true` is internal state recorded when green CI is observed; it is not an exit-0 checkpoint because `ci-initial` now continues into `ci-merge` in the same invocation.
- `3` means the CI loop needs user input or orchestrator follow-up. `BAIL_REASON` is written to state. Most exit-3 reasons also set `BAIL_NEEDS_USER_INPUT=true`. The **`first-fixer-non-health`** bail (first tier of the rotated CI-fix list reported `LAUNCHER_FAILURE_CLASS=other`; Codex on `start_attempt=0`) exits **`3`** but leaves **`BAIL_NEEDS_USER_INPUT=false`** so `/implement` Step 8+ can run the autonomous main-agent CI-fix sub-procedure in `skills/implement/SKILL.md` before any `AskUserQuestion` path.
- `4` means stalled cleanup. `STALL_TRACKING=true`, `STALL_STEP`, and `EXIT_CODE=4` are written to state (`EXIT_CODE` is the value `skills/implement/scripts/stall-recovery-report.sh` `classify` reads back when composing the public stall report — see #3096). When `STALL_STEP=12d` (merge-pr policy/admin/error branch), the script appends a "DO NOT improvise recovery" orchestrator directive to the `$fail_file` so any reader of the failure detail log sees the correct recovery path. Exception: `MERGE_RESULT=error` whose text reports a local/PR-head OID mismatch is classified as recoverable divergence only when the reported PR head OID is still an ancestor of the current local `HEAD`; that case routes to `run_rebase_rebump` instead of stalling. Second exception: `MERGE_RESULT=admin_failed` whose `ERROR` text contains `"Base branch was modified"` is also classified as a recoverable race condition (main advanced between the last rebase and the merge attempt); that case also routes to `run_rebase_rebump` so the branch is rebased and re-queued for CI rather than stalling at 12d. The rebase cap is 20 (raised from 5 to accommodate busy repos where main advances frequently). Non-bump rebase conflicts are handled in-script (mechanical retries and `run_recovery_waterfall`); exhaustion surfaces here as `exit 4` with `RESUME_PHASE` / `CALLER_KIND` set where the state machine still needs an orchestrator resume (for example `RESUME_PHASE=ship-pr-rrr-phase14`).
- `5` — **not emitted by `ship-pr.sh` after Phase 1 #3364.** Postbump rebase failures emit `STATUS=rebase-failed` from `implement-finalize.sh postbump`; `run_bump_phase` stalls at step `8b` via `exit 4` (no conflict checkpoint or Exit 5 handoff). Non-bump `run_rebase_rebump` conflict exhaustion sets `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, emits `CONFLICT_FILES`, and stalls with `exit 4`; the orchestrator runs `conflict-resolution.md` under the Exit 4 matrix in `skills/implement/SKILL.md` (not Exit 5).
- `6` — transient network failure. Orchestrator retries the same `PHASE` after a short sleep. `BAIL_REASON` carries the underlying network-signature; `STALL_TRACKING=false` distinguishes it from `exit 4`. `EXIT_CODE=6` is written to state so the public stall-recovery report records the actual transient-net exit code rather than defaulting to `0` (see #3096).
- `2` (from `die_usage`) — internal argument-validation error; `die_usage` fired because the `ship-pr.sh` invocation received invalid CLI arguments. This exit is outside the orchestrator table above; it signals a programming error in the caller's `Invoke:` block, not a runtime state-machine condition.

## Helper Contracts

`ship-pr.sh` parses stdout envelopes from existing helpers rather than relying only on exit status:

- `run-relevant-checks-captured.sh` success is a clean envelope on exit `0`: `RELEVANT_CHECKS_OK=true` **or** `RELEVANT_CHECKS_SKIPPED=true` (same predicate as `is_relevant_checks_clean` in `ship-pr.sh`). When checks fail during `run_checks_phase`, the phase calls `scripts/lint-fix-loop.sh --site ship-pr-ci-initial` to dispatch a Codex/Cursor coder for repairs (up to 3 fix dispatches); every `LINT_FIX_STATUS=applied` is followed by a verification run, including after the third/final dispatch; on `failed`, `main-agent-required`, or a structural failure (no `REDACTED_LOG_FILE` in output), the phase falls back to `exit_stall 6`.
- `ci-failed-jobs.sh` classifies failed remote CI jobs after `gh-run-logs.sh`
  succeeds. Fixable jobs are replayed locally by
  `run_per_job_local_fix_loop` and, after broad vendor CI fixes, by
  `_verify_failed_jobs_locally` through a fixed case-statement argv dispatcher;
  `lint-fix-loop.sh --site ship-pr-ci-per-job --target-cmd-args-file PATH`
  only receives a display copy of the argv tokens. There is no `eval` of job
  names or command strings from GitHub. A final verification sweep re-runs each
  formerly failed local equivalent before push. Jobs with no local equivalent,
  exhausted per-job repairs, or failed verification repairs exit `3` with
  `BAIL_REASON=ci-local-unfixable:<sanitized-comma-list>` and
  `BAIL_FAILURE_DETAIL_LOG` pointing at the detail file.
- `implement-finalize.sh postbump` uses the last `STATUS=` line.
- `create-pr.sh` emits `PR_NUMBER`, `PR_URL`, `PR_TITLE`, and `PR_STATUS`; existing PRs trigger `gh-pr-body-update.sh`.
- `ci-wait.sh` emits `ACTION`, counters, `FAILED_RUN_ID`, and `BAIL_REASON`. When `ci-decide.sh` hits the `FIX_ATTEMPTS >= 10` safety cap, the forwarded `BAIL_REASON` is the exact token **`fix-attempts-exhausted`**, which `needs_user_bail_reason` maps to exit **`3`** (operator input). That is orthogonal to autonomous vendor-fix exhaustion in `run_evaluate_failure`, which stalls with exit **`4`** and `STALL_STEP=10-max-retries` for `ci-initial`.
- `merge-pr.sh` emits `MERGE_RESULT` and `ERROR`.
- **Phase 1 #3364 — no per-PR bump/rebump in `ship-pr.sh`:** `run_bump_phase` no longer calls `classify-bump.sh`, `apply-bump.sh`, or `check-bump-version.sh`; it emits `⏩ 8: version bump status=skip reason=phase1-no-per-pr-bump` and still runs `refresh-run-logs.sh`, `write_postbump_state`, and `implement-finalize.sh postbump`. `run_rebase_rebump` / `_run_rebase_rebump_from_step3` perform CI-fix rebase + sync + force-push only (no `drop-bump-commit.sh`, changelog staging, or re-classify).
- **Pre-flush before rebase** (issue #2952 Bug B): `run_rebase_rebump` invokes `scripts/refresh-run-logs.sh` before `rebase-push.sh` so pending tracked `larch-logs/` writes are flushed first.
- **Pre-rebase tracked-leftover fixup** (issue #3209): after the pre-flush, when `git status --porcelain --untracked-files=no -- larch-logs/` is non-empty, `run_rebase_rebump` stages tracked changes under `larch-logs/` with `git add -u -- larch-logs/` and, when the index is non-empty, commits via `git-commit.sh` with subject `chore: pre-rebase working-tree fixup (#3209)`. A follow-up pass runs when `larch-logs/` porcelain remains. Failures are recorded as Warnings and are non-fatal.
- Failing helper/tool invocations capture stdout/stderr into
  `$IMPLEMENT_TMPDIR/ship-pr-fail-<phase>-<n>.log` and call
  `append-tool-failure.sh --redact` before the existing retry/stall/continue
  decision. `ship-pr.sh` emits `FAILURE_DETAIL_LOG=<path>` for those
  invocations so callers can inspect the captured details without stdout
  replay. Logging failures are best-effort and do not change phase outcomes.
  When `append-tool-failure.sh` or the session tmpdir is unavailable,
  `append_tool_failure_local` replays the capture to stderr line-by-line through
  `redact-secrets.sh` then `sanitize_diagnostic_line` (per-line; preserves LF
  boundaries).

Transient network classification uses `is_transient_net_signature` and `with_transient_retry` from `scripts/lib-net.sh`, sourced fail-closed through the `LARCH_LIB_NET_LOADED` sentinel before any phase logic runs. `ship_pr_with_transient_retry` re-runs the supplied envelope predicate against the final `fail_file` after the lifted helper returns so exhausted envelope-error responses still call `exit_transient_net` regardless of rc; matching create-PR, rebase, merge, or CI-bail text exits `6` through `exit_transient_net`; non-matching failures continue through the normal stall or user-input paths.

## Recovery waterfall (`run_recovery_waterfall`)

Several failure classes attempt **three-tier** vendor recovery before the historical `exit_stall` handoff: `launch-codex-ci.sh`, then `launch-cursor-ci.sh`, then `launch-claude-ci.sh` (each tier runs only when the corresponding `codex` / `cursor` / `claude` binary exists on `PATH`). **`run_ci_fix_vendor` is special:** when the **rotated first** tier (Codex on `start_attempt=0`) fails with `LAUNCHER_FAILURE_CLASS=other` (non-health launcher failure), `ship-pr.sh` records `BAIL_REASON=first-fixer-non-health`, skips the remaining tiers for that attempt, and returns early so `run_evaluate_failure` can exit **3** for the `/implement` Step 8+ autonomous path — health-class failures (`health`, missing class, `none` on non-zero exits misclassified as health, etc.) still fall through to the next tiers. Its fifth positional argument is the optional failed-jobs TSV from `ci-failed-jobs.sh`; when present, the winning vendor tier must pass `_verify_failed_jobs_locally` before `_stage_and_push_ci_fixes` can push. The verifier returns `2` for head-changed-after-dispatch and `4` for final sweep regression, and `run_ci_fix_vendor` preserves those codes for `run_evaluate_failure`. Call sites include: checks log resolution failures and post-lint exhaustion in `run_checks_phase`, the OOS disposition gate in `run_pr_prep_phase`, `write-final-report.sh` / `create-pr.sh` failures in `run_pr_create_phase`, and **non-bump-only** `rebase-push.sh --keep-on-conflict` conflicts in `run_rebase_rebump`.

On CI launcher or lint-fix failure, `ship-pr.sh` surfaces redacted stderr tails to chat via `_surface_ci_stderr_tail` / `_surface_lint_fix_stderr_tail` (reading `${stem}.stderr-tail` produced by `scripts/lib-failed-agent-stderr-tail.sh`). The CI fix-loop uses the per-tier `--output` stem (`$tier_out`); the recovery waterfall parses `LAUNCHER_EXIT` from launcher stdout and surfaces when shell rc, parsed launcher exit, or a non-empty `${output}.stderr-tail` indicates agent failure. `run_lint_fix_loop_capture` surfaces after `lint-fix-loop.sh` when rc or `LINT_FIX_STATUS` indicates failure, parsing `STDERR_TAIL_PATH` (fallback `CODER_LOG_FILE`).

Each tier snapshots `HEAD` plus tracked/untracked dirty paths, runs the launcher (`--role fix` or `--role resolve-conflict`; the rebase path passes `--conflict-files` from `LARCH_WF_CONFLICT_CSV` when set) with optional `--failure-log` when the capture file already lives under `$IMPLEMENT_TMPDIR`, then runs a **phase-specific verifier** (relevant-checks capture for the checks phase via `verify_kind=checks-step6` / `run-relevant-checks-captured.sh`; **pr-prep** via `verify_kind=pr-prep-oos` by re-invoking `oos-disposition-gate.sh`, not the checks capture helper; `write-final-report.sh` / `create-pr.sh` probe, or `git rebase --continue` plus `_run_rebase_rebump_verify_plain_no_push`). Failed tiers roll back via `recovery_waterfall_paths_delta_revert` using `while IFS= read -r path` and quoted `git restore --staged -- "$path"` / `git checkout -- "$path"` / `rm -f -- "$path"` so paths with spaces or glob characters cannot word-split. When every tier fails, the caller `exit_stall`s with the same step tokens as before the waterfall.

**Legacy inline conflict launcher (`run_rebase_rebump`):** when `skip_vendor` is false and the recovery waterfall did not already resolve the conflict, `run_rebase_rebump` uses a **single-shot** launcher (not the three-tier `run_recovery_waterfall`): `launch-codex-ci.sh --role resolve-conflict` when `codex` is on `PATH`, otherwise `launch-cursor-ci.sh` with the same role. There is no Claude tier and no per-tier rollback loop on this path — operators debugging inline rebase conflicts should expect Codex-first, Cursor-only fallback, not the rotated `run_ci_fix_vendor` order.

`RESUME_PHASE=ship-pr-rrr-phase14` is **not** a no-op: resuming advances the state machine and re-enters `run_rebase_rebump` so the tail of the CI-fix rebase procedure can finish after operator intervention.

## Invariants

- `run_rebase_rebump` bounds infinite rebase storms from concurrent merges to main with `REBASE_COUNT >= 5`. On exhaustion it stalls with `STALL_STEP=10-max-retries` for `ci-initial` or `STALL_STEP=12-max-retries` for `ci-merge`. If `git symbolic-ref HEAD` fails before the rebase call, it stalls with `STALL_STEP=10-detached-head` or `STALL_STEP=12-detached-head` respectively.
- `run_evaluate_failure` retries CI recovery up to **3** times with jittered backoff (~2s/4s ±25%; 8s/16s ladder entries exist for higher caps but are unused at `_max_fix=3`) between attempts. Each attempt first refreshes `gh-run-logs.sh` capture for the failed run id; when that helper exits **3** (run still in progress), the attempt skips fix dispatch entirely and only applies backoff so CI can finish. When logs are available (`gh-run-logs` exit 0), `ci-failed-jobs.sh` runs first. If it finds failed jobs with local equivalents, `run_per_job_local_fix_loop` runs those commands and the final verification sweep before `_stage_and_push_ci_fixes` performs token-record append, run-log refresh, staging, commit, and push. If the per-job repair path returns main-agent-required/dispatch/exhaustion, the same TSV is passed into `run_ci_fix_vendor`; both vendor call sites use an explicit capture-and-case pattern so return `2` maps to `exit_stall 10-head-changed` / `12-head-changed`, return `4` sets `per_job_verification_retry=true` for an outer retry without pushing, and return `0` is the only success path. If `ci-failed-jobs.sh` is unavailable or fails, ship-pr records a `Warnings` entry and falls back to the broader `run_ci_fix_vendor` path. `run_ci_fix_vendor` still runs a **3-tier inner waterfall** (Codex → Cursor → Claude, one launch per tier) and pipes the captured log through `scripts/redact-secrets.sh` before passing **`--failure-log`** to each launcher — raw captures are never forwarded. When no failed-jobs TSV is available, `_verify_failed_jobs_locally` emits a warning breadcrumb and preserves the historical relevant-checks-only gate. A detached-HEAD check runs before each outer attempt. If `FAILED_RUN_ID` is empty it stalls immediately with the legacy phase token: `STALL_STEP=10` for `ci-initial`, `STALL_STEP=12c` for `ci-merge`. This missing-run-id path is the sole remaining legacy exception; retry exhaustion and detached-HEAD now use the hyphenated tokens listed above. Worst-case broad-vendor launcher volume per phase is **3 outer × 3 tiers = 9** `launch-*-ci.sh` calls. Local check remediation routes through `scripts/lint-fix-loop.sh` with `--site ship-pr-ci-initial`, `--site ship-pr-ci-merge`, or `--site ship-pr-ci-per-job`; `_RCC_MAX_ITER` is now the actual inner-loop ceiling, clamps empty/non-numeric/zero values to `3`, caps oversized values at `6`, and defaults to `LARCH_CI_LOCAL_FIX_ITER:-6` for per-job and vendor verification flows. `FIX_ATTEMPTS` increments once per successful fix push.
- `run_pr_create_phase` derives the PR title from the branch range (`merge-base..HEAD`, falling back to all of `HEAD` when `git merge-base` fails), skipping subjects whose prefix matches `^chore(larch-logs): flush` followed by a space (larch-log flush commits produced by `larch-log-flush.sh`). The oldest non-matching subject becomes the title; when `ISSUE_NUMBER` is set in state, the title is prefixed with `Fixes #N:` followed by a space. Fallback is `"Implement requested changes"` when no non-flush commit exists in the range. Before `create-pr.sh`, the phase writes placeholder `final-summary.md` content; a failure there stalls PR creation. When that write succeeds, the phase commits the run-log tree via `larch-log.sh commit` when `LARCH_NO_LOGS_COMMIT` is not `true`, so `create-pr.sh`'s push carries the committed summary onto the remote PR tip. After the PR is created (and its body updated when it already existed), the phase re-runs `write-final-report.sh --comment-only` to refresh only the tracking-issue comment with the live PR URL. The pre-PR `larch-log.sh commit` and the post-create comment refresh are best-effort warnings only.
- After `implement-finalize.sh postbump` completes with `STATUS=ok` or `STATUS=skipped`, `run_bump_phase` emits `⏩ 8: version bump status=skip reason=phase1-no-per-pr-bump` (Phase 1 #3364). The orchestrator MUST NOT re-emit this line as text output (issue #1944). See **Phase 1 (#3364)** under **Verbosity Control** in `skills/implement/SKILL.md` (ship-pr substeps 8/8a/8b breadcrumbs are script-owned only).
- **`ship-branch-guard` stall** (`STALL_STEP=bump-branch-guard`) — at the start of `run_bump_phase`, before postbump work, the script compares `read_state BRANCH_NAME` to `git symbolic-ref -q --short HEAD`. Same rules as the historical bump-branch-guard (including forked `main`/`master` exception). Runs on every `run_bump_phase` entry, including `--resume-phase bump` tolerance resumes.
- Postbump `STATUS=rebase-failed` (and other non-ok postbump statuses) exit `4` at step `8b` (Phase 1 #3364); no Exit 5 / `step8b_rebase` handoff from `run_bump_phase`.
- `ci-initial` treats `ACTION=merge` as CI passed, writes `CI_PASSED=true`, advances to `ci-merge`, and returns to the internal loop in the same `ship-pr.sh` invocation. `ci-merge` then treats `ACTION=merge` as permission to call `merge-pr.sh`.
- `version_already_published` from `merge-pr.sh` is a recoverable version-race condition. `run_ci_phase` first checks `gh pr view <PR_NUMBER> --json state`; when GitHub reports `MERGED`, the script treats the result as `already_merged`, marks `PR_CLOSED=true`, and advances to `postmerge`. If the PR is not merged or the probe fails, it calls `run_rebase_rebump "$phase"` and returns 0 so the outer loop re-enters `ci-wait.sh`; `run_rebase_rebump` enforces the rebase cap before stalling.
- Every merge-success branch writes `$IMPLEMENT_TMPDIR/post-merge-sentinel` before `advance_phase postmerge`, so prompt-side teardown, `refresh-run-logs.sh`, and other incidental `larch-log.sh commit` paths cannot create or push larch-log-only commits to `main` / the default branch. No exception exists for `run_postmerge_phase`; the `larch-log.sh commit` rejection is unconditional after the sentinel is present (see `skills/implement/SKILL.md` NEVER #19). Failure to write the sentinel stalls fail-closed instead of entering postmerge without the guard.
- After argument validation, ship-pr.sh runs `export IMPLEMENT_TMPDIR` so child processes inherit the session tmpdir path for non-log behavior even when ship-pr.sh is invoked from a fresh shell where the orchestrator environment was not inherited. It also exports `LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"` so explicit log commit helpers invoked inside the subprocess tree can suppress best-effort log commits when requested.
- Fork mode uses direct `rebase-push.sh --base-remote upstream --base-ref main` inside `run_rebase_rebump` when CI-fix rebase runs on a fork target.
- Operator compatibility note: downstream automation that keyed only on legacy `STALL_STEP=10` or `STALL_STEP=12c` must also accept `10-max-retries`, `12-max-retries`, `10-detached-head`, and `12-detached-head`. `10` and `12c` remain the missing-`FAILED_RUN_ID` stall codes only.
- `run_ci_fix_vendor` and the conflict-resolution branch of `run_rebase_rebump` resolve the design plan via `resolve_plan_file()`, which prefers `PLAN_FILE` from `$IMPLEMENT_TMPDIR/session-env.sh` when set (read without sourcing), validates the path is under `$IMPLEMENT_TMPDIR` (rejects paths outside to prevent arbitrary local-file reads), and verifies the file exists. When `PLAN_FILE` is absent or invalid, the helper falls back to `$IMPLEMENT_TMPDIR/plan.txt` when that file exists. When a valid path is resolved, `--plan-file` is forwarded to the Cursor, Codex, and Claude CI launchers so external agents preserve the design plan while fixing CI or resolving conflicts. Path violations and missing files are logged to `execution-issues.md` under `Warnings`.
- `_stage_and_push_ci_fixes` is the shared CI-fix push path for both
  per-job-only repairs and `run_ci_fix_vendor`: it appends token records when
  present, stages explicit paths via `collect_ci_stage_paths`, commits
  `Fix CI failure` when needed, then calls `ci-behind-count.sh`. When behind,
  it reuses `run_rebase_rebump` with `defer-push` (fork-aware base remote/ref),
  refreshes the pre-push HEAD snapshot, re-verifies failed jobs and lint on the
  rebased tree, stages any post-rebase lint delta, refreshes run logs, and pushes
  via `git-force-push.sh` when a rebase occurred or `CI_FIX_REBASE_PENDING` is set
  after a failed post-rebase verify (retry uses force-with-lease); otherwise it
  uses plain `git-push.sh`.
- `run_ci_fix_vendor` rotates the codex→cursor→claude waterfall start tier per
  outer `_fix_attempt` (`start_attempt % 3`). The first-fixer-non-health shortcut
  keys off the first tier of the rotated list, not a fixed tier name.
- `run_rebase_rebump` accepts optional `defer-push` plus `base_remote` /
  `base_ref` arguments threaded into `rebase-push.sh` and `_run_rebase_rebump_from_step3`
  (skips `git-force-push.sh` when deferred).
- `run_ci_fix_vendor` stages CI fix commits via `_stage_and_push_ci_fixes` and `collect_ci_stage_paths` (explicit paths from vendor dirty snapshots plus lint-fix deltas), not `git add -u`.
- `_verify_failed_jobs_locally` is the vendor-path pre-push gate. It consumes the same TSV format as `run_per_job_local_fix_loop`, skips an absent or empty TSV with a warning breadcrumb, collects any non-fixable TSV row into the consolidated `ci-local-unfixable:<list>` bail, replays each fixable job locally, dispatches `lint-fix-loop.sh --site ship-pr-ci-per-job` for local failures, then performs a final cross-job sweep. It exits `3` directly for consolidated bails using the same `state_set_many BAIL_REASON ... BAIL_FAILURE_DETAIL_LOG ...` contract as `run_per_job_local_fix_loop`; callers only see return `0`, `2`, or `4`.
- State writes use `tmp.$$` plus `mv`.
- The local execution-issue logger resolves the log root from the state file's
  `IMPLEMENT_TMPDIR` key when present, falling back to the validated
  `--implement-tmpdir` argument. The state file is parsed with `read_state`;
  it is never sourced.

## Postmerge Phase

`run_postmerge_phase` calls `implement-finalize.sh postmerge` (Steps 14+15: local cleanup and verify-main), then finalizes the staged larch-log manifest (`status=done`, `pr_number=N`) best-effort. Before the final status update, it probes `$IMPLEMENT_TMPDIR/larch-logs/implement/<RUN_ID>/manifest.json`; when missing, it runs `larch-log.sh init` and tags the synthesized manifest with `status=partial` plus `recovery_reason=manifest_lost_mid_run` so partial run-log directories remain identifiable. **Fail-closed ordering**: the final `larch-log.sh manifest` (`status=done` + `pr_number`) must exit zero before `write-final-report.sh` runs. A non-zero manifest exit skips the report. Post-merge `write-final-report.sh` failures whose captured output matches `is_transient_net_signature` exit the phase with code `6` via `exit_transient_net` (same contract as pre-PR `run_pr_create_phase`). After the manifest reaches `status=done` and the report succeeds, `write-final-report.sh` (without `--comment-only`) updates tmpdir `summary-final.md`, mirrors the run-log `final-summary.md` for the merged outcome (`MERGE_RESULT` is already in `ship-pr-state.sh`), and upserts the tracking-issue final-summary comment. No post-merge `larch-log.sh commit` is performed (NEVER #19 in `skills/implement/SKILL.md`). Session-transcript capture is owned by Step 7a and earlier `scripts/refresh-run-logs.sh` retries before each push; Step 18 is reserved for prompt-side teardown and the remaining terminal refresh/safety-net work. `$IMPLEMENT_TMPDIR` remains intact for Step 18 to use.

Schema note: v2 flushed run snapshots often omit `pr_number` and `status` until merge. **`ship-pr.sh` postmerge is the intentional merge-time writer** of `status=done` and `pr_number` on the tmpdir manifest under `$IMPLEMENT_TMPDIR` when `PR_CLOSED=true` — do not assume those keys are absent from the postmerge tmpdir tree. Git-committed run-log snapshots on the branch (including historical tips) may still omit them: NEVER #19 forbids a post-merge `larch-log.sh commit`, so merge-finalized manifest keys are not published to the default branch via a post-merge log commit; rely on tmpdir manifests, `write-final-report.sh` output, or the tracking-issue comment when diagnosing merge completion.

## Log Refresh

`run_pr_create_phase` writes and commits the placeholder `final-summary.md`
before `create-pr.sh` so the remote PR tip includes the same run-log tree as
the local branch on the first push. After `PR_NUMBER`/`PR_URL` are persisted,
it re-runs `write-final-report.sh --comment-only` to refresh the tracking
comment via API only; that second pass does not commit or push.

`scripts/refresh-run-logs.sh` re-renders `token-report`, `timing-report`, and `session-transcript` before each push, then commits the updated run-log tree, so the PR's committed logs always reflect the most recent run state. It is called at three trigger points:

- **Trigger A** (`run_rebase_rebump`): after rebase sync, before `git-force-push.sh`.
- **Trigger B** (`run_ci_fix_vendor`): after fix commit, before `git-push.sh`.
- **Trigger C** (`run_bump_phase`): before `write_postbump_state` (postbump ship path).

All three calls use `|| true` so refresh failure is non-fatal. The helper exits 0 with no commit when `MERGE_RESULT=merged|admin_merged|already_merged` is in state, and also when the state file is missing (fail-closed).

## Breadcrumb Stream

`ship-pr.sh` emits single-line progress diagnostics at major phase boundaries and snag points via `larch_err` from `lib-quiet.sh` (operator-visible stderr after quiet init, mirrored into the quiet log with the standard streaming secret scrubber):

- `→ ship-pr: <phase>` — positive phase-entry (checks, ship/postbump, PR prep, opening PR, CI watch, postmerge)
- `→ ship-pr: PR #N opened` — after PR creation
- `→ ship-pr: CI green` — after CI passes in the initial phase
- `→ ship-pr: merged` — after the PR is merged
- `⚠ ship-pr: CI failed; dispatching fix` — on CI failure before vendor dispatch
- `⚠ ship-pr: rebase (CI-fix, no re-bump)` — on CI-fix rebase entry (`run_rebase_rebump`)
- `⚠ ship-pr: merge conflict on rebase` — when a rebase fails with a non-transient conflict
- `⚠ ship-pr: transient network failure` — on every `exit_transient_net` call
- `⛔ ship-pr: stalled at step N` — on every `mark_stall` call (covers all `exit_stall` codes)

`ship-pr.sh` is a long-running orchestrator entrypoint; nested synchronous
`ci-wait.sh` invocations run in the foreground inside the ship-pr process tree
(breadcrumbs Stages 3–4 removed paired-PID barriers).

## Edit In Sync

When changing phase names, exit-code meaning, helper stdout parsing, state keys, or rebase/re-bump behavior, update `skills/implement/SKILL.md`, `scripts/test-restore-finalize-state.sh`, `scripts/test-implement-structure.sh`, `scripts/commit-changelog.md`, `scripts/drop-bump-commit.md`, `skills/implement/references/rebase-rebump-subprocedure.md`, and this file together. Script edits also follow `.claude/rules/script-md-siblings.md`: keep sibling `.md` files in sync with behavior changes.

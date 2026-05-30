# test-ship-pr.sh

Offline harness for `scripts/ship-pr.sh`.

It copies the state-machine script into disposable git repositories with stubbed sibling helpers and exercises:

- state-file syntax validation with uppercase keys
- exit `4` on relevant-checks failure
- stdout stays capped on verbose relevant-checks failure, while
  `FAILURE_DETAIL_LOG` points at the captured diagnostics
- exit `5` on postbump conflict with `CALLER_KIND=step8b_rebase`
- exit `5` on same-version bump race with `CALLER_KIND=step8_apply_bump_same_version`
- same-invocation `ci-initial` `ACTION=merge` continuation into `ci-merge`, with `PHASE=done` after postmerge
- exit `3` user-input bail routing
- `version_already_published` from `merge-pr.sh` short-circuits to
  postmerge when `gh pr view` reports `MERGED`, and still falls through to
  `run_rebase_rebump` when the PR is not merged
- exit `0` for `postmerge` phase with `PHASE=done` written and `tracking-issue-summary.sh` skipped
- postmerge manifest recovery when the run-log directory exists but `manifest.json` is missing
- design-plan forwarding from `session-env.sh` to CI-fix and rebase-conflict vendor launchers
- `--no-logs-commit` is exported as `LARCH_NO_LOGS_COMMIT` for child lifecycle helpers invoked by `ship-pr.sh`
- inner local fix loop: exit `0` when first 2 vendor attempts fail but the 3rd succeeds; exit `4` (stall) when all 5 vendor attempts fail
- CI vendor verification after per-job fallback:
  `vendor_verify_local_pass`, `vendor_verify_local_exhausts`,
  `vendor_verify_nonfixable_direct`, `vendor_verify_head_changed`,
  `vendor_verify_sweep_regression`,
  `vendor_verify_empty_tsv`, and
  `vendor_verify_rc2_on_gh_logs_failed_branch`
- `_RCC_MAX_ITER` budget behavior:
  `rcc_max_iter_honored` and `rcc_max_iter_invalid_env_clamp`
- transient-network routing through `scripts/lib-net.sh`: matching create-PR, merge, CI-bail, and rebase signatures exit `6`, while non-network errors stall normally
- OID-mismatch `MERGE_RESULT=error` ("local HEAD does not match PR head OID") routes to `run_rebase_rebump` and exits `0` with `PHASE=done`, rather than stalling at `STALL_STEP=12d`
- argv-init cold start writes the seven per-key state fields plus `BAIL_FAILURE_DETAIL_LOG`, `NO_LOGS_COMMIT`, and `IMPLEMENT_TMPDIR` when no state file exists (`BRANCH_NAME` matches the disposable-repo checkout so bump-branch-guard stays green; `ISSUE_NUMBER` carries an `=` to exercise `cut -d= -f2-` extraction)
- argv-init resume leaves `RUN_ID` unchanged when `--run-id` disagrees with on-disk state (avoids bump-branch-guard mismatch while still proving argv is ignored)
- argv-init `--force-init-state true` rewrites state from argv (`RUN_ID`); CR/LF in any per-key argv value is rejected with exit `2` and a flag-specific stderr message
- `append_tool_failure_local` fallback relay when `append-tool-failure.sh` is not executable: forces the in-process path via `chmod -x`, feeds a fixture log with BEL/ESC bytes, captures merged `2>&1`, and asserts printable text survives while BEL and ESC are stripped

Wired as `make test-ship-pr`.

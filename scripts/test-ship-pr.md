# test-ship-pr.sh

Offline harness for `scripts/ship-pr.sh`.

It copies the state-machine script into disposable git repositories with stubbed sibling helpers and exercises:

- state-file syntax validation with uppercase keys
- exit `4` on relevant-checks failure
- stdout stays capped on verbose relevant-checks failure, while
  `FAILURE_DETAIL_LOG` points at the captured diagnostics
- exit `5` on postbump conflict with `CALLER_KIND=step8b_rebase`
- exit `5` on same-version bump race with `CALLER_KIND=step8b_same_version`
- same-invocation `ci-initial` `ACTION=merge` continuation into `ci-merge`, with `PHASE=done` after postmerge
- exit `3` user-input bail routing
- `version_already_published` from `merge-pr.sh` short-circuits to
  postmerge when `gh pr view` reports `MERGED`, and still falls through to
  `run_rebase_rebump` when the PR is not merged
- exit `0` for `postmerge` phase with `PHASE=done` written and `tracking-issue-summary.sh` skipped
- postmerge manifest recovery when the run-log directory exists but `manifest.json` is missing
- design-plan forwarding from `session-env.sh` to CI-fix and rebase-conflict vendor launchers
- `--no-logs-commit` is exported as `LARCH_NO_LOGS_COMMIT` for child lifecycle helpers invoked by `ship-pr.sh`
- inner local fix loop: exit `0` when first 2 of 3 attempts fail but 3rd succeeds; exit `4` (stall) when all 3 fail
- transient-network routing through `scripts/lib-net.sh`: matching create-PR, merge, CI-bail, and rebase signatures exit `6`, while non-network errors stall normally

Wired as `make test-ship-pr`.

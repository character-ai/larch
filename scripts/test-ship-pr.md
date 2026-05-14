# test-ship-pr.sh

Offline harness for `scripts/ship-pr.sh`.

It copies the state-machine script into disposable git repositories with stubbed sibling helpers and exercises:

- state-file syntax validation with uppercase keys
- exit `4` on relevant-checks failure
- stdout stays capped on verbose relevant-checks failure, while
  `FAILURE_DETAIL_LOG` points at the captured diagnostics
- exit `5` on postbump conflict with `CALLER_KIND=step8b_rebase`
- exit `5` on same-version bump race with `CALLER_KIND=step8b_same_version`
- exit `0` checkpoint for `ci-initial` `ACTION=merge`
- exit `3` user-input bail routing
- `version_already_published` from `merge-pr.sh` short-circuits to
  postmerge when `gh pr view` reports `MERGED`, and still falls through to
  `run_rebase_rebump` when the PR is not merged
- exit `0` for `postmerge` phase with `PHASE=done` written and `tracking-issue-summary.sh` skipped
- postmerge manifest recovery when the run-log directory exists but `manifest.json` is missing
- `--no-logs-commit true` suppresses `larch-log.sh commit` in `run_rebase_rebump`, `run_ci_phase` (ci-merge pre-merge flush), and `run_postmerge_phase`; `--no-logs-commit false` (default) calls it in all three sites
- inner local fix loop: exit `0` when first 2 of 3 attempts fail but 3rd succeeds; exit `4` (stall) when all 3 fail
- transient-network routing through `scripts/lib-net.sh`: matching create-PR, merge, CI-bail, and rebase signatures exit `6`, while non-network errors stall normally

Wired as `make test-ship-pr`.

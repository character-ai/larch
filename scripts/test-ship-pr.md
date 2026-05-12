# test-ship-pr.sh

Offline harness for `scripts/ship-pr.sh`.

It copies the state-machine script into disposable git repositories with stubbed sibling helpers and exercises:

- state-file syntax validation with uppercase keys
- exit `4` on relevant-checks failure
- exit `5` on postbump conflict with `CALLER_KIND=step8b_rebase`
- exit `5` on same-version bump race with `CALLER_KIND=step8b_same_version`
- exit `0` checkpoint for `ci-initial` `ACTION=merge`
- exit `3` user-input bail routing
- exit `0` for `postmerge` phase with `PHASE=done` written and `tracking-issue-summary.sh` called

Wired as `make test-ship-pr`.

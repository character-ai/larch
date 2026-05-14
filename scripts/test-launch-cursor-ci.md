# test-launch-cursor-ci.sh

Argv and sidecar harness for `scripts/launch-cursor-ci.sh`.

Coverage:

- invalid role rejection
- relative output rejection
- relative `--plan-file` rejection and launcher support check
- unsupported output character rejection
- literal `cursor-ci-fix` timing allow-list coverage
- `append-token-record.sh` normalization of Cursor token sidecars

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.

Wired as `make test-launch-cursor-ci`.

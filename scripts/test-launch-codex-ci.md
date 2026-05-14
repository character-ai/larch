# test-launch-codex-ci.sh

Argv and sidecar harness for `scripts/launch-codex-ci.sh`.

Coverage:

- invalid role rejection
- relative output rejection
- unsupported output character rejection
- literal `codex-ci-fix` timing allow-list coverage
- `append-token-record.sh` normalization of Codex token sidecars

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.

Wired as `make test-launch-codex-ci`.

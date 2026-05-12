# test-launch-codex-ci.sh

Argv and sidecar harness for `scripts/launch-codex-ci.sh`.

Coverage:

- invalid role rejection
- relative output rejection
- unsupported output character rejection
- literal `codex-ci-fix` timing allow-list coverage
- `append-token-record.sh` normalization of Codex token sidecars

Wired as `make test-launch-codex-ci`.

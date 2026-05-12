# test-launch-cursor-ci.sh

Argv and sidecar harness for `scripts/launch-cursor-ci.sh`.

Coverage:

- invalid role rejection
- relative output rejection
- unsupported output character rejection
- literal `cursor-ci-fix` timing allow-list coverage
- `append-token-record.sh` normalization of Cursor token sidecars

Wired as `make test-launch-cursor-ci`.

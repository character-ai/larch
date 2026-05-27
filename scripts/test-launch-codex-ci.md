# test-launch-codex-ci.sh

Argv and sidecar harness for `scripts/launch-codex-ci.sh`.

Coverage:

- invalid role rejection
- relative output rejection
- relative `--plan-file` rejection and launcher support check
- unsupported output character rejection
- literal `codex-ci-fix` timing allow-list coverage
- `append-token-record.sh` normalization of Codex per-bucket token sidecars
- runtime Codex `--json` usage capture into `${OUTPUT}.events.jsonl`
- fail-closed empty token-record behavior when no usage event is emitted
- stderr-routed auth failure classification
- fix-role prompt includes literal `topology.tsv` when the shared CI-fix patterns file exists; non-fix roles omit it
- asserts the rendered `${OUT_FIX}.prompt` (fix-role) contains the persistent-interactive-subprocess prohibition (issue #2991). The check runs against the prompt actually written to disk by `scripts/launch-codex-ci.sh`, not against the source script.

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.

Wired as `make test-launch-codex-ci`.

# emit-tally.sh Contract

`skills/review/scripts/emit-tally.sh` writes review summary artifacts for a round.

It writes `review-round-summary.md`, `review-summary.json` with `schema_version=1`, and `rejected-findings.md`. It also invokes `skills/shared/scripts/oos-serialize.sh` for accepted OOS serialization and copies summary files to parent tmpdirs when `--session-env-path` or `--implement-tmpdir` is provided.

Stdout is `KEY=value` only: `EMIT_OK`, `ROUND_SUMMARY_FILE`, and `REVIEW_SUMMARY_FILE`.

Harness: `skills/review/scripts/test-emit-tally.sh`, wired through `make test-emit-tally`.

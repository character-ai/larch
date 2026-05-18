# emit-tally.sh Contract

`skills/review/scripts/emit-tally.sh` writes review summary artifacts for a round.

It writes `review-round-summary.md`, `review-summary.json` with `schema_version=1`, and `rejected-findings.md`. Accepted and rejected totals come from the summary counters in `review-tally.env`, and the compact rejected listing includes only `FINDING_*_OUTCOME=rejected` entries (not neutral or exonerated findings). It also invokes `skills/shared/scripts/oos-serialize.sh` for accepted OOS serialization and copies summary files to parent tmpdirs when `--session-env-path` or `--implement-tmpdir` is provided.

Stdout is `KEY=value` only: `EMIT_OK`, `ROUND_SUMMARY_FILE`, and `REVIEW_SUMMARY_FILE`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-emit-tally.sh`, wired through `make test-emit-tally`.

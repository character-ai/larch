# log-phase.sh Contract

`skills/review/scripts/log-phase.sh` wraps `scripts/larch-log.sh` for review batches.

Review uses flat batch slugs under `larch-logs/review/<RUN_ID>/`; phase names are encoded in slugs such as `review-context` and `review-panel-manifest`, not in subdirectories.

Allowed batches: `review-context`, `review-panel-manifest`, `review-findings`, `review-tally`, and `review-round-summary`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-log-phase.sh`, wired through `make test-log-phase`.

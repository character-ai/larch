# log-phase.sh Contract

`skills/review/scripts/log-phase.sh` wraps `scripts/larch-log.sh` for review batches.

Review uses flat batch slugs under `larch-logs/review/<RUN_ID>/`; phase names are encoded in slugs such as `review-context` and `review-panel-manifest`, not in subdirectories.

Allowed batches: `review-context`, `review-panel-manifest`, `review-findings`, `review-tally`, `review-scout-manifest`, and `review-round-summary`.

`review-scout-manifest` is a replace-mode JSON object batch. The wrapper writes it only when dynamic-archetype scout status is available, with fields for `status`, `dynamic_slots`, `manifest_path`, and `yield_tsv_path`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-log-phase.sh`, wired through `make test-log-phase`.

# test-larch-logs-batches.sh contract

Regression harness for `scripts/larch-log-batches.sh`. It pins the canonical
batch order, validates each row's extension, mode, and sanitizer enum, and
exercises the `plan-goals` sanitizer through `scripts/larch-log.sh`.

Update alongside `scripts/larch-log-batches.sh`.

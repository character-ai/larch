# test-larch-logs-batches.sh contract

Regression harness for `scripts/larch-log-batches.sh`. It pins the canonical
batch order, validates each row's extension, mode, and sanitizer enum, and
exercises the `plan-goals` sanitizer through `scripts/larch-log.sh`.

It also exercises the `json-lines` sanitizer through
`lib-larch-log.sh`: valid single-line JSON, empty files, and multi-line NDJSON
pass; plain text and mixed JSON/plain-text payloads fail with the expected
`ERROR=` envelope.

Update alongside `scripts/larch-log-batches.sh`.

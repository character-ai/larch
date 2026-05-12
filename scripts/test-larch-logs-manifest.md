# test-larch-logs-manifest.sh contract

Regression harness for the `larch-log.sh init` manifest schema. It uses a
temporary `LARCH_LOG_ROOT`, verifies required fields, checks retry idempotency,
and asserts atomic temp files are not left behind.

The main router contract lives in `scripts/larch-log.md`.

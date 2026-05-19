# test-lib-external-launcher-common.sh

Offline unit-test harness for `scripts/lib-external-launcher-common.sh`.

Primary contract: `scripts/lib-external-launcher-common.md`.

Covers `external_is_transient_infra_failure` — all decision branches exercised by the current helper: missing output file, unknown tool, exit-code allowlist (codex 5/7, cursor 4/8), non-empty output file, and the happy path returning 0.

Run via `bash scripts/test-lib-external-launcher-common.sh` or `make test`.

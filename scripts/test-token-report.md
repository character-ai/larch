# test-token-report.sh

**Purpose**: Offline regression harness for `scripts/token-report.sh`.

It uses fixture ledger + Claude transcript JSONL files to assert terse output, the full markdown multi-table shape, per-vendor headings, dropped legacy columns, the anchored old `| N/A |` cell-shape check, grand-total counts derived from fixture vendor content, `--output`, graceful unavailable output, and idempotent `## Token Report` sentinel replacement after repeated refreshes. It also covers pipe-and-newline injection fixtures for table-cell sanitization (including the unknown-vendor heading path: `vendor_label`'s raw fallback routes through `md_cell` so an arbitrary vendor name with `|` or newline cannot break the heading line or inject a fake row separator) and smoke-tests an oversized existing `token-report.md` fixture with per-heading verification so sentinel replacement remains parser-safe.

Additional coverage for `LARCH_DEBUG_TOKEN_REPORT` (closes #1466 sub-item A): the harness loops over the full truthy allowlist documented in `scripts/token-report.sh` (`1`, `true`/`TRUE`/`True`, `yes`/`YES`/`Yes`, `on`/`ON`/`On`) and asserts each enables the jq-stderr capture path on render failure (the unavailable message gains a `(jq stderr at <path>)` suffix and the captured file is non-empty); it asserts an explicit list of negative / unset spellings (`0`, `false`/`FALSE`, `no`/`NO`, `off`/`OFF`, `disabled`, empty, unset — the unset case uses `env -u` so the harness is hermetic against a caller-set value) keeps the path silent (no path suffix); and that a successful render with debug enabled removes its stderr temp file so `$TMPDIR` does not accumulate empty files (verified via an isolated per-test `TMPDIR` to avoid flakiness from parallel jobs touching the system `/tmp`).

Run via `make test-token-report` or the shard that includes it.

Update this harness when report columns, sentinel comments, source-resolution test hooks, or failure-mode wording changes.

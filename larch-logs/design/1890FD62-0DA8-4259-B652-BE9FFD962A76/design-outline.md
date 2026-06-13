## Proposed Design Outline

### Goals
- Fix silent token-record failures in three distinct paths: drafter copy, lint-fix NDJSON, and unknown-TOOL split.
- Add missing harness mapping (`lint-fix-loop.sh`) and research-phase Codex sidecar ingestion instructions.
- Eliminate the hardcoded rate-value second authority in the snapshot test.

### Non-goals
- Do not change the cost-reporting schema or add new token-record fields.
- Do not refactor how `token-report.ndjson` or the active ledger work at a structural level.
- Do not port Bash `ship-pr.sh` recovery ingestion to Python separately (covered by the `checks.py` fix).

### Approach sketch
- `launch-codex-drafter.sh`: replace `2>/dev/null || true` after the `cp` with a stderr warning via `larch_err`.
- `python/tokens.py`: add a `print(…, file=sys.stderr)` warning in `record_vendor_from_sidecar` when vendor is `"unknown"` (after parse, before early-return).
- `python/checks.py`: add `token append-record` subprocess call in `_run_codex` after the existing `record-vendor` call; thread `implement_tmpdir` from `run_lint_fix`.
- `scripts/relevant-checks.sh`: add a `case` arm mapping `scripts/lint-fix-loop.sh` to `test-lint-fix-loop`.
- `python/test_report_tokens_cost.py`: rewrite `test_display_rates_shipped_defaults_snapshot` to reference `DEFAULT_RATE_TABLE_PER_M` and `DEFAULT_VENDOR_MODEL` instead of literal values.
- `skills/research/references/research-phase.md`: after `collect-agent-results.sh` settles, add explicit per-lane ingestion instructions for each `STATUS=OK` Codex lane (both `token append-record` and `record-vendor-sidecar`).

### Surfaces in scope
- `scripts/launch-codex-drafter.sh` (Item 1)
- `python/tokens.py` (Item 3)
- `python/checks.py` (Items 4 + 7)
- `scripts/relevant-checks.sh` (Item 5)
- `python/test_report_tokens_cost.py` (Item 2)
- `skills/research/references/research-phase.md` (Item 6)

### Open questions
- None.

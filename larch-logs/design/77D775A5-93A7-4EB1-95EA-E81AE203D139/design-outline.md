## Proposed Design Outline

### Goals
- Fix `dedup_tier_a_report()` in `python/larch/state/_report.py` to translate the cross-repo helper's raw `FILE_FAILURE_REPORT_STATUS`/`_URL`/`_FALLBACK_REASON` output into `STALL_RECOVERY_REPORT_*` before emitting, matching the documented contract in `python/stall-recovery-report.md`.
- Add regression coverage that exercises the real translation seam (mocked shell subprocess with realistic stdout), closing the gap that let this ship.

### Non-goals
- No change to `scripts/file-failure-report-cross-repo.sh` — its `FILE_FAILURE_REPORT_*` output contract is correct and already relied on by the Tier B path.
- No change to `design_terminal.py`'s consumer logic — it already reads the correct `STALL_RECOVERY_REPORT_STATUS` key; only the producer was wrong.
- No broader refactor of `stall_recovery.py` / `_report.py` beyond this call site.

### Approach sketch
- In `dedup_tier_a_report()`, after writing the shell helper's raw stdout to `out`, call `normalize_file_failure_report_env()` on it instead of `_emit_env_file(out)` — mirroring the sibling `_emit_chat_print_filing_status` pattern already in the same file.
- `normalize_file_failure_report_env` already lives in `_normalize.py` and is already imported into `_report.py`; no new import or CLI surface needed.
- Add a test in `python/tests/state/test_stall_recovery.py` that mocks the cross-repo helper subprocess to emit realistic `FILE_FAILURE_REPORT_STATUS=...` stdout, then asserts `dedup_tier_a_report_main` emits the translated `STALL_RECOVERY_REPORT_STATUS`.
- Fixing this shared function repairs both `/design`'s auto-bug-filer and `/implement`'s native terminal-failure/escalation-success reporting flow, which calls the same `dedup-tier-a-report` subcommand directly.

### Surfaces in scope
- `python/larch/state/_report.py`
- `python/tests/state/test_stall_recovery.py`

### Open questions
- None.

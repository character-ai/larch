### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:316-319
- **Concern**: Central ship-state reader `read_state_kv` is omitted from the migration set while Step 8 Bash and `ship_state.py` move to explicit last-match policy (G-IO-1). Scenario: `_read_state_kv` still calls `larch_io.read_kv(..., first_match=True)`; `ship_resume.py`, `ship.py`, `run_log_flush.py`, and `ship_state.py` itself still call `run_logs.read_state_kv` for `RESUME_PHASE`, `PHASE`, and related keys, so duplicate rows in `ship-pr-state.sh` resolve first in Python and last in migrated Bash/ship_state paths
- **Proposed resolution**: Add `### UPDATED: python/larch/report/run_log_batch.py` and `python/tests/report/test_run_logs.py` to route `_read_state_kv`/`read_state_kv` through explicit last-match codec reads aligned with Step 8 and `ship_state`; replace remaining `run_logs.read_state_kv` call sites in `ship_state.py` that the plan targets for last-match

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_core.py:211-246
- **Concern**: `design_core` plan bullets conflict: replace multi-key scans yet preserve last-non-empty semantics that standard `last`/`all` policies do not express (G-IO-1). Scenario: `design_terminal.py` and `design_lifecycle.py` depend on `_read_env_value_last` and `_read_env_values`, which skip empty overwrites; migrating those call sites to bare `read_kv`/`read_kvs` with `policy=last` changes finalize and compose-env outcomes when env files contain blank placeholder rows before the final value
- **Proposed resolution**: Keep `_read_env_value_last` and `_read_env_values` as named codec-backed wrappers (or add explicit codec flags such as skip-empty-overwrites) and pin the behavior in `design_terminal` or `design_step_log` tests with duplicate and empty-row fixtures

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ship_pr.py:54-61; python/larch/implement/dispatch_ship.py:526-539
- **Concern**: G-IO-1/G-Wire-3: Plan leaves live ship wire-file readers outside the codec. Scenario: Ship failure detection and the Phase 14 recovery-skip gate retain independent duplicate, trimming, and error semantics after the codec migration.
- **Proposed resolution**: Add both readers to the migration, preserve their current last- or first-wins and trimming behavior explicitly, and add focused regression cases.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-deny-run-in-background.sh:74
- **Concern**: Missing fail-closed `kv get` failure coverage. Scenario: After the planned replacement, a broken or unavailable Python CLI can yield no `CLONE_PATH`; treating that as no matching registry permits a background Bash despite an active same-clone daemon.
- **Proposed resolution**: Add the hook harness to the plan and assert that a failing `kv get` with a valid matching registry still exits 0 and emits a denial.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_core.py:215-246
- **Concern**: `design_core` last/non-empty helpers lack pinned caller tests after codec migration. Scenario: The plan replaces `_read_env_value_last` and `_read_env_values` with typed `first`/`last`/`all` reads while preserving non-empty fallback, but `_read_env_value_last` keeps the last non-empty value (not the last line) and `_read_env_values` ignores empty updates for known keys. No `### UPDATED:` test file targets these helpers; only router and step-log tests are listed. `design_terminal.py` and `design_lifecycle.py` consume them on finalize/terminal paths, so a bare `last` policy can change outcomes without a failing test.
- **Proposed resolution**: Add an explicit codec contract or thin wrapper for last-non-empty/multi-key merge, and add duplicate/empty-value fixtures in `python/tests/design/test_design_lifecycle.py` or a focused `test_design_core.py` that pin current semantics at exported helper boundaries.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_helpers.py:337-338
- **Concern**: Ship route-exit still reads `ship-pr-state.sh` first-match while the plan migrates writers and other readers to last-match. Scenario: The plan migrates `ship_state.py`, `ship.py`, and `step-8-ship.sh` to explicit last-match reads, but leaves `dispatch_helpers._read_kv_file` hardcoded to `first_match=True`. `dispatch_ship.py` uses it for `RESUME_PHASE`, `CALLER_KIND`, `CONFLICT_FILES`, and bulk state snapshots on the same state file. Duplicate keys already last-win in `ship_state.py`; route-exit can therefore resume or branch on stale first rows after this migration.
- **Proposed resolution**: Add `dispatch_helpers.py` and/or `dispatch_ship.py` to the firm plan set with explicit last-match codec reads (and allowlist where needed), plus a duplicate-key fixture in `python/tests/implement/test_ship.py` or dispatch coverage that asserts route-exit agrees with migrated state readers.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-deny-run-in-background.sh:74
- **Concern**: A missing Python or failed `kv get` can bypass the active-bgjob denial. Scenario: The proposed `kv get` replacement yields an empty `CLONE_PATH` on CLI failure, so a valid background Bash request with an active registry entry can be allowed instead of denied.
- **Proposed resolution**: Add fail-closed handling for CLI resolution or read failure when registry entries exist, and extend `scripts/test-hook-deny-run-in-background.sh` with a missing-Python or failing-`kv get` case that asserts exit-0 denial.

---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: `read_state_kv` omitted from last-match migration
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Central ship-state reader `read_state_kv` is omitted from the migration set while Step 8 Bash and `ship_state.py` move to explicit last-match policy (G-IO-1). `_read_state_kv` still calls `larch_io.read_kv(..., first_match=True)`; `ship_resume.py`, `ship.py`, `run_log_flush.py`, and `ship_state.py` still call `run_logs.read_state_kv` for `RESUME_PHASE`, `PHASE`, and related keys, so duplicate rows in `ship-pr-state.sh` resolve first in Python and last in migrated Bash/ship_state paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/report/run_log_batch.py` and `python/tests/report/test_run_logs.py` to route `_read_state_kv`/`read_state_kv` through explicit last-match codec reads aligned with Step 8 and `ship_state`; replace remaining `run_logs.read_state_kv` call sites in `ship_state.py` that the plan targets for last-match


### [Plan Review] FINDING_2

### FINDING_2: `design_core` last-non-empty semantics conflict with bare codec policies
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: `design_core` plan bullets conflict: replace multi-key scans yet preserve last-non-empty semantics that standard `last`/`all` policies do not express (G-IO-1). `design_terminal.py` and `design_lifecycle.py` depend on `_read_env_value_last` and `_read_env_values`, which skip empty overwrites; migrating those call sites to bare `read_kv`/`read_kvs` with `policy=last` changes finalize and compose-env outcomes when env files contain blank placeholder rows before the final value. The plan replaces these helpers with typed `first`/`last`/`all` reads while preserving non-empty fallback, but `_read_env_value_last` keeps the last non-empty value (not the last line) and `_read_env_values` ignores empty updates for known keys. No `### UPDATED:` test file targets these helpers; only router and step-log tests are listed, so a bare `last` policy can change outcomes on finalize/terminal paths without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep `_read_env_value_last` and `_read_env_values` as named codec-backed wrappers (or add explicit codec flags such as skip-empty-overwrites) and pin the behavior in `design_terminal` or `design_step_log` tests with duplicate and empty-row fixtures
  - From Cursor-Requirements: Add an explicit codec contract or thin wrapper for last-non-empty/multi-key merge, and add duplicate/empty-value fixtures in `python/tests/design/test_design_lifecycle.py` or a focused `test_design_core.py` that pin current semantics at exported helper boundaries


### [Plan Review] FINDING_3

### FINDING_3: Ship wire-file readers left outside codec migration
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: G-IO-1/G-Wire-3: Plan leaves live ship wire-file readers outside the codec. Ship failure detection and the Phase 14 recovery-skip gate retain independent duplicate, trimming, and error semantics after the codec migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add both readers to the migration, preserve their current last- or first-wins and trimming behavior explicitly, and add focused regression cases.


### [Plan Review] FINDING_5

### FINDING_5: `dispatch_helpers` route-exit still uses first-match on ship state
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Ship route-exit still reads `ship-pr-state.sh` first-match while the plan migrates writers and other readers to last-match. The plan migrates `ship_state.py`, `ship.py`, and `step-8-ship.sh` to explicit last-match reads, but leaves `dispatch_helpers._read_kv_file` hardcoded to `first_match=True`. `dispatch_ship.py` uses it for `RESUME_PHASE`, `CALLER_KIND`, `CONFLICT_FILES`, and bulk state snapshots on the same state file. Duplicate keys already last-win in `ship_state.py`; route-exit can therefore resume or branch on stale first rows after this migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `dispatch_helpers.py` and/or `dispatch_ship.py` to the firm plan set with explicit last-match codec reads (and allowlist where needed), plus a duplicate-key fixture in `python/tests/implement/test_ship.py` or dispatch coverage that asserts route-exit agrees with migrated state readers.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: Makefile:47-88
- **Concern**: [SCOPE-REDUCTION] Separate focused lint and test Make targets are convenience scope. Scenario: The direct `python3 python/cli.py lint kv-codec` command, focused pytest invocation, and `py-lint-checks-fast` integration already make the feature runnable and enforced. Extra aliases enlarge the Makefile and maintenance surface.
- **Proposed resolution**: Retain the fast-lint integration and guarded baseline regeneration, but omit new standalone focused lint and test targets.


---LARCH-REJECTED-END---

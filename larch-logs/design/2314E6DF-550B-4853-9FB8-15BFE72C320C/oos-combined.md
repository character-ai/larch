### rebase.py: port driver-owned refresh-run-logs + larch-logs pre-drop fixup
- **Description**: `refresh-run-logs` and pre-drop `larch-logs/` fixup omitted (driver-owned). Scenario: Dirty tracked `larch-logs/` can make `drop_bump_commit` return `DROPPED=false` and `Stalled` before rebase — bash runs `refresh-run-logs.sh` and scoped fixup first.
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: future ship.py driver / rebase.py pre-drop guard
- **Phase**: design

### rebase.py: add defer_push / HAS_BUMP inputs for run_rebase_rebump parity
- **Description**: No `defer_push` / `HAS_BUMP` inputs on the rebase entry point. Scenario: Bash `run_rebase_rebump` skips push when `defer_push` and skips classify/apply when `HAS_BUMP=false`; the Python port currently has no equivalent inputs.
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/rebase.py `rebase_and_rebump` signature
- **Phase**: design

### rebase.py: reconcile version-regression guard base with apply_bump origin/main hardcode
- **Description**: Version-regression guard uses `base_remote`/`base_ref` but `apply_bump` still hardcodes `origin/main`. Scenario: Fork/upstream bases can disagree with apply_bump's origin/main fetch and guards (python/version_bump.py ~566-578).
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/rebase.py re-bump path + python/version_bump.py apply_bump
- **Phase**: design

### OOS_1:
- **Description**: `refresh-run-logs` and pre-drop `larch-logs/` fixup omitted (driver-owned). Scenario: Dirty tracked `larch-logs/` can make `drop_bump_commit` return `DROPPED=false` and `Stalled` before rebase — bash runs `refresh-run-logs.sh` and scoped fixup first
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:22-28 / Approach
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3309
### OOS_2:
- **Description**: No `defer_push` / `HAS_BUMP` inputs. Scenario: Bash `run_rebase_rebump` skips push when `defer_push` and skips classify/apply when `HAS_BUMP=false`
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:18-20 (`rebase_and_rebump` API)
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3310
### OOS_3:
- **Description**: Version-regression guard uses base_remote/base_ref but apply_bump still hardcodes origin/main. Scenario: Fork/upstream bases can disagree with apply_bump’s origin/main fetch and guards (python/version_bump.py ~566-578)
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:56-60
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3311

### OOS_1: [OUT_OF_SCOPE] No plan step for `test_merge_bash_parity.py` after `merge-pr.sh` deletion
- **Description**: [OUT_OF_SCOPE] No plan step for `test_merge_bash_parity.py` after `merge-pr.sh` deletion. Scenario: After deletion the module's `skipif(not MERGE_SH.is_file())` tests silently stop running; cross-shell merge parity is no longer exercised (Python `test_merge.py` remains)
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_merge_bash_parity.py:28-86
- **Phase**: design



### OOS_2: `conflict-resolution.md` still names `rebase-push.sh` in many load/Phase-1 paths; the plan only lists Phase 4 `--continue` fence rewrites
- **Description**: `conflict-resolution.md` still names `rebase-push.sh` in many load/Phase-1 paths; the plan only lists Phase 4 `--continue` fence rewrites. Scenario: Generic reference sweeps may miss this file until `make lint-retired-scripts` fails late in the run
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/conflict-resolution.md:3-21
- **Phase**: design




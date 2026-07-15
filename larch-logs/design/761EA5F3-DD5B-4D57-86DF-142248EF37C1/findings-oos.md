### OOS_1: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.
- **Description**: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.. Scenario: The plan allows lane-local adapters duplicating `launch-codex-exec` hook wiring; that works but repeats logic already proven in `_drafter.launch_codex_exec_main`.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_drafter.py:464-537
- **Phase**: design


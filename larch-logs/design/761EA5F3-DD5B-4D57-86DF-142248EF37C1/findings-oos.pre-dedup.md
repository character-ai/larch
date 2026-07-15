### OOS_1: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.
- **Description**: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.. Scenario: The plan allows lane-local adapters duplicating `launch-codex-exec` hook wiring; that works but repeats logic already proven in `_drafter.launch_codex_exec_main`.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_drafter.py:464-537
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Update the stale "Production launchers must not import this module yet" banner once `checks_lint_fix` imports `_vendor`.
- **Description**: [OUT_OF_SCOPE] Update the stale "Production launchers must not import this module yet" banner once `checks_lint_fix` imports `_vendor`.. Scenario: The module docstring will contradict production usage after this piece lands; it does not affect runtime behavior.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/agents/_vendor.py:1-7
- **Phase**: design




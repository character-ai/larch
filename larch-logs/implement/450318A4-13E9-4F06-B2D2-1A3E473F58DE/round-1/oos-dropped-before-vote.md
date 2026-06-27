### OOS_1: [OUT_OF_SCOPE] Discarded `_launchable_base_tools_for_slot` call in plan-review dispatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `_launchable_base_tools_for_slot` is invoked with `no_fallback=True` but its return value is discarded. Manifest `prompt_files` keys may drift from launchable tools without any test failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Assert manifest prompt_files keys match launchable tools or remove the dead call.


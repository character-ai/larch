### OOS_1: [OUT_OF_SCOPE] Tests do not exercise heartbeat thread lifecycle under blocking lint-fix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-heartbeat-concurrency-output.txt
- **Severity**: nit
- **Concern**: Existing tests stub lint-fix as instantaneous or call the heartbeat helper directly with a fake `Event`, avoiding real thread timing and wiring under a slow blocking `run_lint_fix`. Regressions in periodic emission, stop/join ordering, post-completion emissions, or cleanup during long lint-fix runs may not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test with blocking fake run_lint_fix asserting STATUS=lint-fix-running on stderr before completion.
  - From dyn-dyn-heartbeat-concurrency-output.txt: Add a test that monkeypatches `run_lint_fix` to block for several seconds (or until an event), asserts periodic stderr lines during the block, asserts no heartbeat after unblock + completion, and covers the `except OSError` path still joining cleanly.



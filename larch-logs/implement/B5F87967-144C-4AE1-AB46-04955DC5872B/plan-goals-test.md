## Goal
Implement issue #5298: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Tests do not exercise heartbeat thread lifecycle under blocking lint-fix.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: cursor-specialist-correctness-output.txt, dyn-dyn-heartbeat-concurrency-output.txt

**Phase**: implement

**Vote tally**: N/A


## Description

Existing tests stub lint-fix as instantaneous or call the heartbeat helper directly with a fake `Event`, avoiding real thread timing and wiring under a slow blocking `run_lint_fix`. Regressions in periodic emission, stop/join ordering, post-completion emissions, or cleanup during long lint-fix runs may not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test with blocking fake run_lint_fix asserting STATUS=lint-fix-running on stderr before completion.
  - From dyn-dyn-heartbeat-concurrency-output.txt: Add a test that monkeypatches `run_lint_fix` to block for several seconds (or until an event), asserts periodic stderr lines during the block, asserts no heartbeat after unblock + completion, and covers the `except OSError` path still joining cleanly.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)

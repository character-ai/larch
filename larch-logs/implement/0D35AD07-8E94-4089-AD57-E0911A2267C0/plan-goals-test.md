## Goal
Add NEVER #13 to skills/implement/SKILL.md prohibiting orchestrator from writing finalize-state.sh

## Implementation Plan

Add NEVER #13 to skills/implement/SKILL.md after NEVER #12, and cross-reference it from the Step 18 teardown block.

### Files to modify
- skills/implement/SKILL.md

### Changes
1. Insert NEVER #13 after NEVER #12 (line 58): prohibit the orchestrator from writing/recreating $IMPLEMENT_TMPDIR/finalize-state.sh. The new rule states: the file is atomically written by ship-pr.sh's write_finalize_state() during postmerge and contains all 20 required keys; the teardown command reads it; the orchestrator must not reconstruct it; if teardown fails with "state-file missing required key", surface the error and stop.

2. Add a cross-reference note before the implement-finalize.sh teardown bash block in Step 18 (around line 1898), warning the orchestrator not to write finalize-state.sh before calling teardown.


## Test plan
- /relevant-checks (pre-commit + agent-lint)

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Clamp-specific prompt blocking still uses generic recovery text
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: When clamp state is armed, `UserPromptSubmit` still routes through the generic prompt-block path, so operators can be told to clear the wrong recovery files and leave the clamp flag behind, which makes the next Stop hook block again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Also gate UserPromptSubmit on task_output_clamp_armed or treat either sidecar as armed; use the clamp-specific block message when the clamp sidecar is present.
  - From cursor-specialist-edge-cases: In UserPromptSubmit, check task_output_clamp_armed before json_block_prompt and emit json_block_task_output_clamp; add harness coverage from a real bg-poll deny.
  - From codex-specialist-edge-cases: When UserPromptSubmit sees the clamp flag, emit json_block_task_output_clamp, or add no-progress-task-output-clamped to the generic recovery text plus its tests and docs.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: End-to-end bridge coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The cross-hook bridge path from the third denied read to the Stop-side block is not exercised end to end, so a wiring bug could still ship with unit tests green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one harness case chaining bg-poll-guard third deny → no-progress Stop block with clamp-specific JSON


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: bg-wait re-arm does not assert bridge sidecars
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The Python bg-wait re-arm path only checks read counters; it does not verify that bridge sidecars are seeded and cleared when the marker context arms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Seed bridge sidecars before _bg_wait_marker_context and assert they are cleared at arm time


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Clamp-sidecar write failure can fail open
- **Reviewer(s)**: dyn-dyn-hook-bridge
- **Severity**: major
- **Concern**: `arm_no_progress_task_output_clamp` can deny reads even if the clamp sidecar write fails, so the orchestrator is blocked without a durable bridge signal and the next notification turn falls back to the generic threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-bridge: If the clamp sidecar write fails, either fail closed (do not deny without a provably armed bridge), or retry once and log a loud stderr diagnostic; at minimum, do not `return 0` from `arm_no_progress_task_output_clamp` without setting an alternate durable arm signal that `hook-no-progress-guard.sh` can read.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_9: Bridge cleanup leaves stale clamp sidecars behind
- **Reviewer(s)**: dyn-dyn-hook-bridge
- **Severity**: minor
- **Concern**: Bridge-state cleanup can leave a stale clamp sidecar behind, and symlinked bridge files are handled inconsistently, so later prompts can still hit the generic breaker even after the bridge-specific Stop path is gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-bridge: In `clear_no_progress_task_output_clamp` / `reset_task_output_read_state`, always remove the full no-progress sidecar set when clearing bridge state (including the symlink else-branch at `scripts/hook-bg-poll-guard.sh:651-653`), and reject or unlink symlinked bridge files before arming, matching the regular-file checks used elsewhere.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0


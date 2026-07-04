# Review Round 2

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Detached marker epoch is reset during signal cleanup
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Signal-restored marker writes on Step 5 and Step 3 can overwrite the original DETACHED_AT_EPOCH, which restarts the 7200s orphan timer after interrupted reattach or cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pass saved DETACHED_AT_EPOCH as fourth arg to _step5_write_detached_marker from cleanup
  - From codex-specialist-correctness: Preserve the original DETACHED_AT_EPOCH through every signal-restored marker write for Step 5 and Step 3.
  - From codex-specialist-edge-cases: Preserve original marker fields in reattach-scoped globals and restore them from the signal cleanup; add signal-during-reattach tests.
  - From codex-specialist-testing: Pass the stored detach epoch into this marker rewrite and cover the path in the wrapper harness.


### FINDING_3: normalize-status failure envelopes disable stall tracking
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: normalize-status failure envelopes still set STALL_TRACKING=false, so terminal Step 5 stalls can bypass stall tracking and downstream Step 18 recovery/rename handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Set stall_tracking=True on all terminal normalize_status failure paths
  - From cursor-specialist-edge-cases: Set stall_tracking=True on all normalize-status failure envelopes and add pytest assertions
  - From codex-specialist-edge-cases: Emit STALL_TRACKING=true for normalization failure envelopes or omit it to use the default true path; add negative-path tests.
  - From codex-specialist-testing: Emit STALL_TRACKING=true for normalization failure envelopes and add negative-path tests.



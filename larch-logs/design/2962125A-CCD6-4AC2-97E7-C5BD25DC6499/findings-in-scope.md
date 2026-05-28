### FINDING_1: B-1 fixture cannot drive two reuse-copy failures
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned Item B-1 scenario needs two phase-2 reuse-copy failures, but the existing `cp` stub only supports one `CP_STUB_FAIL_TARGET_CONTAINS` substring and fails only the first matching copy. As written, the harness cannot reliably produce `PHASE2_RELAUNCH_COUNT=2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Revise the plan to include the tiny cp-stub change needed for exactly two planned copy failures, then use that explicit knob in the B-1 scenario.
  - From Cursor-Edge: Revise B-1 to induce two `reuse_slot_result` failures (e.g. second fall-through via deleted/stale reuse source, or a minimal stub change such as a second-fail budget); drop the plural “two TARGET_CONTAINS triggers” wording
  - From Codex-Edge, Cursor-Innovation, Codex-Innovation: Extend the stub minimally to support two explicit fail target substrings or revise the fixture to include that stub change in the plan
  - From Cursor-Pragmatic, Codex-Pragmatic: Add the minimum stub change to support a fail limit or two target substrings, then use it in the new scenario and assert the cp counter equals 2
  - From Cursor-Requirements, Codex-Requirements: Update the plan to extend the cp stub minimally for this harness, such as a comma/newline list of target substrings or a fail-count setting, then assert the counter saw two failed reuse copies

### FINDING_2: COMBINED_FALLBACK_COUNT absent-KV fallback is disabled
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: `COMBINED_FALLBACK_COUNT` is initialized to `"0"`, so when panel stdout has `FALLBACK_COUNT` above the threshold but omits `COMBINED_FALLBACK_COUNT`, the existing numeric guard treats the value as present and never falls back to `FALLBACK_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Initialize `COMBINED_FALLBACK_COUNT=""` (mirror `dispatch-plan-review-panel.sh` / `decompose-panel-dispatch.sh`) so the existing `''|*[!0-9]*)` guard defaults to `$FALLBACK_COUNT`

### FINDING_3: Zero-finding exit bypasses degraded-panel calculation
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The zero-finding short-circuit still reports `DEGRADED_PANEL=0`, bypassing the proposed final `COMBINED_FALLBACK_COUNT` comparison. A no-finding round with excessive phase-2 relaunches could therefore report a non-degraded panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Compute the panel degradation value before the zero-finding short-circuit or use DEGRADED_ROUND there instead of hardcoded 0

### FINDING_4: Design-consumer tests do not prove COMBINED_FALLBACK_COUNT behavior
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-consumer-stub-completeness, Codex-dyn-consumer-stub-completeness
- **Severity**: important
- **Concern**: The plan changes design consumers to parse and compare `COMBINED_FALLBACK_COUNT`, but the listed harness coverage still exercises only `FALLBACK_COUNT` or the compatibility fallback path. A regression back to `FALLBACK_COUNT` comparisons could pass the existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add targeted assertions in the existing design harnesses with FALLBACK_COUNT=0 and COMBINED_FALLBACK_COUNT above half, covering dispatch-plan-review-panel, decompose-panel-dispatch, and plan-review-loop without adding new harness files
  - From Cursor-dyn-consumer-stub-completeness, Codex-dyn-consumer-stub-completeness: Add the affected harness files to the UPDATED list; update their dispatcher-output stubs to emit PHASE2_RELAUNCH_COUNT and COMBINED_FALLBACK_COUNT via W_STUB_* defaults, and add or adjust one degradation threshold case where FALLBACK_COUNT stays below half but COMBINED_FALLBACK_COUNT crosses it.

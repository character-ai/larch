### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:127-159
- **Concern**: [SCOPE-REDUCTION] Wrapper-level Step 5c harness keeps rc branch-contract coverage after the shell file becomes a thin delegator. Scenario: Keeping rc 0/1/2/3/4 behavior tests in skills/design/scripts/test-design-step5c.sh forces the wrapper harness to duplicate or fake Python step5c_core orchestration even though python/test_design_lifecycle.py already covers those paths
- **Proposed resolution**: Narrow test-design-step5c.sh to thin-wrapper delegation, root derivation, and argv forwarding; keep publish rc, marker, status-env, cleanup, and sentinel branch tests in python/test_design_lifecycle.py




### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step5c_core (planned)
- **Concern**: Plan mandates `.completed/step-5c-terminal` in a `finally` block for abort exits; current bash omits it on publish-tail abort. Scenario: `design-step5c.sh` exits at lines 203-216 before `write_step5c_wrapper_sentinel`; premature-notification recovery that probes only `step-5c-terminal` may treat a failed-publish-tail abort differently than today
- **Proposed resolution**: Match current bash: write `step-5c-terminal` only on the normal completion path unless SKILL recovery is updated and tested for abort parity




### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:2350-2357
- **Concern**: Stale-env avoidance for publish rc 1/3/4 must bypass an existing `.design-publish-result.env`, not rely on `_read_result_pairs` alone. Scenario: If the primary file exists with stale success rows, `_read_result_pairs` returns them and never consults captured stdout; only a guaranteed-absent primary matches bash lines 235-247
- **Proposed resolution**: For rc 1/3/4, point the primary input at a non-existent temp path (as bash does) before calling the allowlisted reader; keep stdout capture as fallback




### [Plan Review] FINDING_17

### FINDING_17:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:185-192
- **Concern**: [SCOPE-REDUCTION] Run-log and flags docs updates are outside the G6.4 runtime scope. Scenario: The binding scope is the Step 5c entrypoint, CLI row, wrapper, and tests; editing docs/run-logs.md and skills/design/references/flags.md adds churn that the feature can ship without
- **Proposed resolution**: Drop those docs edits unless a structure check requires exact entrypoint text; keep only runtime wrapper/CLI/tests and directly consumed Step 5c contract docs




### [Plan Review] FINDING_21

### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-design-step5c.sh:33-132
- **Concern**: [SCOPE-REDUCTION] Wrapper harness keeps publish-tail rc-path coverage after the wrapper becomes a thin exec delegator. Scenario: The current harness stubs design publish. After Step 5c calls publish in-process, preserving rc2, rc4, and stale-env behavior in the shell wrapper test forces brittle fake internals and duplicates python/test_design_lifecycle.py coverage.
- **Proposed resolution**: Reduce the shell harness to thin-wrapper delegation, argv, root-derivation, and pass-through rc checks. Keep publish-tail rc-path coverage in python/test_design_lifecycle.py.





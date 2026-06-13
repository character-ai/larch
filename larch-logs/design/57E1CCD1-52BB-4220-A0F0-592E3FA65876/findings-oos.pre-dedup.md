### OOS_1:
- **Description**: Prompt-side stdout delimiter parsing is brittle compared to a wrapper-written result env. Scenario: The orchestrator must LLM-parse combined stdout; a mistaken grep outside the delimiter region could misroute despite fail-safe, adding long-term maintenance surface
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:172-181
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Outer Bash timeout bump to 2100000 ms is not required by the issue acceptance criteria. Scenario: The issue only requires folding prelude plus internal postplan delegation; internal drafter launch timeout stays 1800 s either way
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:161-164
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Missing-row fail-safe runs a second retained terminal postplan fence on the drafter-success path. Scenario: Acceptance calls for one Bash call through postplan on success; a silent second postplan can re-validate and rewrite sentinels after a partial internal handoff
- **Reviewer**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:183-192
- **Phase**: design

### OOS_3:
- **Description**: [SCOPE-REDUCTION] Planned rc 10/12/13/drift regressions largely duplicate existing merged-mode coverage in the same harness. Scenario: Issue acceptance only requires extending this harness, not re-asserting cases already covered around lines 442-734
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-postplan-emit.sh:379-392
- **Phase**: design


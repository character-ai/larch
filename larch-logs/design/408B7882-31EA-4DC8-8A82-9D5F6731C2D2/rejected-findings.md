### [Plan Review] FINDING_19

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-lint-fix-loop.sh:124-142
- **Concern**: Case 1 exercises default `step3` site, not the failing `ship-pr-ci-per-job` site. Scenario: The bug trace is per-job CI (`--site ship-pr-ci-per-job`); unit coverage of applied+HEAD_CHANGED may not exercise per-job prompt/argv wiring
- **Proposed resolution**: Add a case (or extend case 6) with `write_wrapper_commit_head` and `ship-pr-ci-per-job` asserting the same applied envelope


### [Plan Review] FINDING_20

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/lint-fix-loop.md:19-25
- **Concern**: Output contract section not fully specified for new semantics. Scenario: Plan updates behavior prose but does not call out adding `LINT_FIX_HEAD_CHANGED=true` to the KEY list or revising `LINT_FIX_COMMIT_SHA` (line 23: “helper committed … clean baseline”) for coder-owned commits
- **Proposed resolution**: In the same PR, extend the contract bullets: document `LINT_FIX_HEAD_CHANGED` and state `LINT_FIX_COMMIT_SHA` is emitted for helper-owned or coder-owned commits on the head-changed path



### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:42-53
- **Concern**: Real generator flag parsing and prompt base selection are untested. Scenario: The plan adds --base-remote/--base-ref and changes generate-code-flow-diagram.sh:58, but explicitly skips updating the existing direct generator harness. The step-7a harness uses a stub generator, so it cannot catch a typo in the real parser or a prompt diff still using origin/main.
- **Proposed resolution**: Extend test-generate-code-flow-diagram.sh to capture the prompt file from the launch stub and assert a run with --base-remote upstream --base-ref main lists files relative to upstream/main; also assert defaults still preserve origin/main behavior.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:45-62
- **Concern**: Plan skips the existing real generator harness while changing generate-code-flow-diagram.sh argv parsing and prompt base selection. Scenario: step-7a tests stub the generator, so a broken --base-remote parser or a prompt that still diffs origin/main can pass all proposed tests
- **Proposed resolution**: Update test-generate-code-flow-diagram.sh to invoke the real helper with default and upstream/main flags, have the launch stub capture/read --prompt-file, and assert the Changed files section reflects the selected base; update test-generate-code-flow-diagram.md



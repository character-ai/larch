### OOS_1: Dependency wiring still bypasses the triage apply authorization boundary
- **Description**: Dependency wiring still bypasses the triage apply authorization boundary. Scenario: The plan authorizes mutation only through python/cli.py triage apply --operator-invoked, then separately invokes /block-issue, whose issue_block entrypoints have no operator-invoked or check_live_mutation_auth gate. A replayed or manual block-issue call can still wire edges outside the triage contract.
- **Reviewer**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/triage/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Structural harness does not pin triage SKILL.md frontmatter hooks and allowed-tools
- **Description**: Structural harness does not pin triage SKILL.md frontmatter hooks and allowed-tools. Scenario: test-bug-structure.sh pins argument-hint, Write-hook matcher, and deny-edit-write activation sentinels. The triage harness list omits equivalent frontmatter contract checks, so a regression can drop the scratch-only Write boundary while tests still pass.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/test-triage-structure.sh
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Mechanical --report-only refusal is still orchestrator-only
- **Description**: Mechanical --report-only refusal is still orchestrator-only. Scenario: FINDING_22 noted report-only depends on the skill never calling triage apply. The plan still allows a stray apply invocation to mutate GitHub even when the operator passed --report-only.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/triage.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


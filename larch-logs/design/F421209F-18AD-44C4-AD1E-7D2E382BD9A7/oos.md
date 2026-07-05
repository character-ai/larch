### OOS_1: Normative exit-matrix docs omit the new sentinel gate
- **Description**: Normative exit-matrix docs omit the new sentinel gate. Scenario: SKILL.md will gate ci-fix/reship, but ship-pr-exit-matrix.md and ship-pr-ci-fix.md still say NEXT_ACTION=continue alone authorizes repair
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-39
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: Shell timeout dedup has no dedicated regression test
- **Description**: Shell timeout dedup has no dedicated regression test. Scenario: The plan adds a Python TIMEOUT_S assert in test_run_step_checks_main but does not exercise run-step-checks.sh, so a broken inline Python one-liner could desync the live shell marker
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:76
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


### OOS_1: `--step17-emitted` harness comments still describe post-emission suppression
- **Description**: `--step17-emitted` harness comments still describe post-emission suppression. Scenario: The wrapper test still documents `--step17-emitted true` as “already emitted” suppression. After the cache-then-emit contract, that comment and assertions will mislead maintainers even if orchestrator-only prose changes.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/scripts/test-step-18.sh:241-245
- **Phase**: design




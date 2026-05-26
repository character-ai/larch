### OOS_1:
- **Description**: [OUT_OF_SCOPE] Adjacent harness doc remains stale and partly inaccurate after the proposed docs/linting.md-only change. Scenario: The markdown case ledger still lists 19 cases, omits rebase-unexpected-rc and quiet-diagram-skip-contract, and says diagram-failure-sanitizer suppresses summary upsert even though the harness asserts the comment is posted. Downstream readers can still get stale Step 7a coverage from the sibling doc.
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.md:7-25, skills/implement/scripts/test-step-7a.sh:413-422, skills/implement/scripts/test-step-7a.sh:512-539
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Companion harness documentation still enumerates 19 cases and omits `rebase-unexpected-rc` plus `quiet-diagram-skip-contract` from skills/implement/scripts/test-step-7a.sh:512-540. Scenario: Even after the inventory row is fixed, adjacent harness docs remain stale and can mislead future reviewers about Step 7a regression coverage
- **Reviewer**: Codex-Edge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step-7a.md:5-25
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] Sibling harness contract enumerates the old case set and omits `rebase-unexpected-rc` plus `quiet-diagram-skip-contract`. Scenario: After this PR updates `docs/linting.md`, the adjacent harness contract remains stale and can mislead future Step 7a changes
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step-7a.md:5-25
- **Phase**: design


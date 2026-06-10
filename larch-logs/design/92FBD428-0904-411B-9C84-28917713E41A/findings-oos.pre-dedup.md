### OOS_1:
- **Description**: Contract doc still documents four-archetype threshold math and security in coverage gate. Scenario: Stale docs mislead future edits but do not break runtime when manifest-driven path is used
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.md:25,59
- **Phase**: design

### OOS_2:
- **Description**: Harness contract doc still cites STATIC_SLOT_COUNT=8. Scenario: Documentation drift only; test-dispatch-panel.sh updates are planned but sibling .md is not
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-dispatch-panel.md:9-10
- **Phase**: design

### OOS_1:
- **Description**: Copying full reviewer-security.md bullet list duplicates a kept agent file. Scenario: Issue combines lenses but verbatim duplication increases drift surface when security agent evolves
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/reviewer-edge-cases.md:26-32
- **Phase**: design

### OOS_1:
- **Description**: dispatch-panel.md still states "8 rows" / "4 rows" after archetype removal. Scenario: Stale numeric row counts remain after archetypes shrink; does not break runtime because dispatch-panel.sh emits STATIC_SLOT_COUNT
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/review/scripts/dispatch-panel.md:7-7
- **Phase**: design

### OOS_2:
- **Description**: Default INTENDED_SLOTS remains 4. Scenario: Production review-core passes STATIC_SLOT_COUNT from dispatch; only direct/harness callers without --intended-slots see the stale default
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/review/scripts/check-reviewer-failure-threshold.sh:18-18
- **Phase**: design


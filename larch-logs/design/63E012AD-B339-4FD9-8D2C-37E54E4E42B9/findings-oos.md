### OOS_1: Gate C persist fail-closed is prompt-only with no fence-shape regression
- **Description**: Gate C persist fail-closed is prompt-only with no fence-shape regression. Scenario: The plan updates `approval-gates.md` but adds no harness grep or fixture asserting `persist-design-assessment` or the `**⚠ 4b: architectural-guideline assessment persistence failed**` contract. A later edit could drop persist or fail-open Gate C without CI signal.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-step3-orchestrator-fence.sh
- **Phase**: design




### OOS_1:
- **Description**: Post-pack estimated spread check is simpler than the max_target>ideal+threshold/2 heuristic. Scenario: The heuristic can warn when estimated spread would pass, or stay silent when LPT spread fails without a dominant singleton; it is an indirect proxy for the ≤15s gate
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py:343-345
- **Phase**: design


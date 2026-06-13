### OOS_1:
- **Description**: Post-pack estimated spread check is simpler than the max_target>ideal+threshold/2 heuristic. Scenario: The heuristic can warn when estimated spread would pass, or stay silent when LPT spread fails without a dominant singleton; it is an indirect proxy for the ≤15s gate
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py:343-345
- **Phase**: design

### OOS_2:
- **Description**: importlib load of rebalance.py runs module-level git rev-parse bootstrap. Scenario: Tests inherit the script’s import-time git subprocess side effect; fine in-repo but couples unit tests to git cwd like the script itself
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: python/test_rebalance_script.py:69-77
- **Phase**: design


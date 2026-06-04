### OOS_1:
- **Description**: Python _oos_gate only checks tmpdir/oos-accepted-design.md, not design-export/ or DESIGN_TMPDIR. Scenario: Accepted OOS only under design-export/oos-accepted-design.md can pass bash OOS_PENDING yet Python LARCH_SHIP_PR_IMPL=python never surfaces oos-filing
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:129-137
- **Phase**: design


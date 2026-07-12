### OOS_2: Duplicate round parser outside scanner repoint list
- **Description**: Duplicate round parser outside scanner repoint list. Scenario: `tokens.py` still owns `_round_num_from_path` for panel artifact sizing; it does not walk the committed corpus. Unifying it is consistency-only, not required for the stated scanner contract.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/report/tokens.py:351-358
- **Phase**: design


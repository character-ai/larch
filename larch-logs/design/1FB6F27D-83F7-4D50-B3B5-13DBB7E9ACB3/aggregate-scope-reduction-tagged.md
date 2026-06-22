### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_types.py:33-37 python/review_aggregate.py:246-248
- **Concern**: [SCOPE-REDUCTION] Finding.title is specified without a parse contract and callers today use raw blocks only. Scenario: Implementers may invent title parsing or ship a dead field; aggregate still derives IDs via _finding_id_from_block separately, adding churn without acceptance benefit
- **Proposed resolution**: Omit Finding.title from the frozen dataclass unless a caller needs it; document that parse_findings sets finding_id from the heading token and stores the raw heading line inside block

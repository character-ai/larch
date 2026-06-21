### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:168 and python/oos_filer.py:274-276
- **Concern**: [SCOPE-REDUCTION] _bare_oos_item_suffix is listed as a new helper in both analyze_issues.py and oos_filer.py. Scenario: oos_filer already has _bare_oos_suffix (OOS-only); the plan adds a widened suffix helper in two inventories without requiring a single import path, inviting divergent regex behavior between filing joins and analyze joins
- **Proposed resolution**: Define the widened matcher once in oos_filer.py (extend or replace _bare_oos_suffix), import it from analyze_issues.py, and drop the duplicate entry from the analyze_issues helper list

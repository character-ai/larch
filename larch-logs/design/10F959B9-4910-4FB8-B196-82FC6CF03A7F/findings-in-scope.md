### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:27-29
- **Concern**: In scope neutral penalty wording is ambiguous against the scope=in_scope TSV column and progress_report._classification_row_in_scope. Scenario: An implementer may gate the -0.25 penalty on scope==in_scope or _classification_row_in_scope. Rows with empty or drifted scope on FINDING_* would skip the neutral penalty while accepted_points_from_classification_row still applies severity weighting (only scope=oos is excluded), reintroducing a costless middle for some neutrals
- **Proposed resolution**: In python/voting.py specify neutral penalty uses the same OOS exclusion as accepted_points_from_classification_row: penalize unless scope=oos when the scope column exists, or legacy finding_id starts with OOS_ when it does not; add neutral_points_from_classification_row beside accepted_points_from_classification_row; explicitly forbid using progress_report._classification_row_in_scope




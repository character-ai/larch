### OOS_1: [SCOPE-REDUCTION] `Finding.title` duplicates data already on the heading line inside `block`
- **Description**: [SCOPE-REDUCTION] `Finding.title` duplicates data already on the heading line inside `block`. Scenario: The issue asks for a minimal typed finding; a separate `title` field adds parse logic and drift risk versus `_finding_id_from_block` with no wire-format benefit
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/review_types.py:33-36
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] `_count_findings` need not call full `parse_findings` block splitting
- **Description**: [SCOPE-REDUCTION] `_count_findings` need not call full `parse_findings` block splitting. Scenario: Line-count semantics only need `^### FINDING_[0-9]+:` matches; full block parsing is heavier and invites boundary drift versus today's one-line scan
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:207-210
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] oos._iter_finding_blocks duplicates FINDING_N block scanning
- **Description**: [OUT_OF_SCOPE] oos._iter_finding_blocks duplicates FINDING_N block scanning. Scenario: Issue acceptance names only review_and_fix/review_aggregate for the shared parser; leaving oos.py on a local scan is consistent with minimum-change scope
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/oos.py:64-79
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] plan_review_round still uses its own FINDING_N block regex outside adoption scope
- **Description**: [OUT_OF_SCOPE] plan_review_round still uses its own FINDING_N block regex outside adoption scope. Scenario: Plan-review paths are out of this issue's stated parser adoption surface; consolidating them would expand diff beyond acceptance
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/plan_review_round.py:336
- **Phase**: design




### OOS_1: Run-log difficulty metadata can still report `round_cap: 3` from raw records
- **Description**: Run-log difficulty metadata can still report `round_cap: 3` from raw records. Scenario: `write_implement_round_meta` reads `record["round_cap"]` directly and never applies the planned `_resolution_from_data` clamp, so committed `round-meta.json` can show `ceiling_in_effect: 3` after runtime enforcement is 2.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:1717-1727
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] effective_authorized_cap still contains escalation-gated round-3 authorization logic
- **Description**: [OUT_OF_SCOPE] effective_authorized_cap still contains escalation-gated round-3 authorization logic. Scenario: Once HARD tier_ceiling is 2, the raw_cap > ROUND_THREE_AUTHORIZATION_CAP branch is dead but remains as misleading policy surface for future edits
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_common.py:155-157
- **Phase**: design




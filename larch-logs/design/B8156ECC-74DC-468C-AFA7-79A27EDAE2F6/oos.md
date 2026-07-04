### FINDING_2: Separate persisted round_cap preservation from runtime clamping in difficulty tests
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The difficulty calibration tests mix two different contracts: on-disk merge preservation must keep stale `round_cap: 3`, while runtime resolution should clamp to 2. Rewriting every `round_cap: 3` expectation to `2` would erase regression coverage for stale persisted records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A split the test update: keep merge-on-disk assertions at `round_cap: 3` (or add a comment that disk may stay stale), and add a separate `resolve_panel_tier` / `_resolution_from_data` test proving a stored `round_cap: 3` resolves to `2` at runtime.
  - From Cursor-Innovation: Split the test work: keep merge preservation asserting on-disk `round_cap: 3` survives `write-record`; add or extend a resolution test that loads the same fixture and asserts `resolve_panel_tier(...).round_cap == 2` (and `tier_ceiling(HARD) == 2`). Update only assertions that truly track runtime cap emission, not disk preservation.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Run-log difficulty metadata can still report `round_cap: 3` from raw records
- **Description**: Run-log difficulty metadata can still report `round_cap: 3` from raw records. Scenario: `write_implement_round_meta` reads `record["round_cap"]` directly and never applies the planned `_resolution_from_data` clamp, so committed `round-meta.json` can show `ceiling_in_effect: 3` after runtime enforcement is 2.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:1717-1727
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] effective_authorized_cap still contains escalation-gated round-3 authorization logic
- **Description**: [OUT_OF_SCOPE] effective_authorized_cap still contains escalation-gated round-3 authorization logic. Scenario: Once HARD tier_ceiling is 2, the raw_cap > ROUND_THREE_AUTHORIZATION_CAP branch is dead but remains as misleading policy surface for future edits
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_common.py:155-157
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


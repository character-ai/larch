### OOS_2:
- **Description**: [OUT_OF_SCOPE] Rich header tracks plan-review-slots only, not plan-voter-slots. Scenario: During the voting sub-phase the latest artifact is often plan-voter-slots.ndjson.output-files while the timing label stays design Step 3 — plan review. The report can show N/N reviewers returned and omit voter progress, matching the user's shallow hook snapshot.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/progress_report.py (planned _render_design_plan_review)
- **Phase**: design


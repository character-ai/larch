### OOS_1:
- **Description**: Main-agent apply path still produces no chartable vendor row. Scenario: When both external coders fail, apply_findings_with_coder returns main-agent-required and fixes are applied later without any type=vendor row; the round can still accept findings and commit, reproducing an unexplained post-vote gap on degraded hosts
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:1362-1364
- **Phase**: design


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_2:
- **Description**: Apply label mapping is duplicated in Bash awk and Python progress_report. Scenario: Kind-to-codex/apply and cursor/apply mapping lives in two places; future label tweaks can drift between live p charts and final renderer
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/progress_report.py:496-515
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected


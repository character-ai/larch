### OOS_1: Main-agent apply path produces no chartable Gantt vendor row
- **Description**: Main-agent apply path still produces no chartable vendor row. Scenario: When both external coders fail, apply_findings_with_coder returns main-agent-required and fixes are applied later without any type=vendor row; the round can still accept findings and commit, reproducing an unexplained post-vote gap on degraded hosts
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:1362-1364
- **Phase**: design

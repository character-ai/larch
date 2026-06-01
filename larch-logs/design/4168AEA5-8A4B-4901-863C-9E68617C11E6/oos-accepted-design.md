### OOS_2:
- **Description**: link_pr_closes lives in tracking_issue.py but Closes #N is composed in ship-pr pr-body assembly (scripts/ship-pr.sh:1535) and tracking-issue-write.sh has no Closes helper. Scenario: Duplicate or dead API surface in the 8-module bundle
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/tracking_issue.py:26
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3326

### OOS_1:
- **Description**: push.py adds fork-aware origin vs upstream remotes; git-push.sh is plain git push (scripts/git-push.sh:44). Scenario: Extra remote logic is untested scope beyond the stated port unless Phase 7 needs it
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/push.py:32
- **Phase**: design

### OOS_2:
- **Description**: link_pr_closes lives in tracking_issue.py but Closes #N is composed in ship-pr pr-body assembly (scripts/ship-pr.sh:1535) and tracking-issue-write.sh has no Closes helper. Scenario: Duplicate or dead API surface in the 8-module bundle
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/tracking_issue.py:26
- **Phase**: design


### OOS_1:
- **Description**: Open-issue-only signature scan can re-file after the matching upstream issue is closed. Scenario: Closed regressions may spawn duplicate upstream issues instead of +1 comments on the original
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/file-failure-report-cross-repo.sh:114-116
- **Phase**: design

### OOS_1:
- **Description**: SECURITY.md is in Files to modify/create but absent from scope-files.txt. Scenario: Classification: scope-files gap not plan creep. Issue requirement 6 and approved-outline Surfaces both require SECURITY.md cross-repo filing documentation. SECURITY.md:64-74 still states Tier B prints through chat only and must be updated for Part 2.
- **Reviewer**: Cursor-dyn-scope-delta
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:472-485
- **Phase**: design


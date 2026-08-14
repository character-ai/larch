<!-- in-scope:start -->
### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: high
- **Focus area**: correctness
- **Location**: plan.txt:9
- **Concern**: Persist the phase. Scenario: a resume sees stale state
- **Proposed resolution**: write the phase before continuation



<!-- in-scope:end -->
<!-- out-of-scope:start -->
### OOS_1: Split the migration
- **Description**: Split the migration. Scenario: requires a separate leaf
- **Reviewer**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: docs/migration.md
- **Phase**: design



### OOS_2: Add a follow-up test
- **Description**: Add a follow-up test. Scenario: needs an integration fixture
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: testing
- **Location**: python/tests/review/test_plan_review.py
- **Phase**: design



### OOS_3: Clarify the changelog
- **Description**: Clarify the changelog. Scenario: release notes are owned elsewhere
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: documentation
- **Location**: CHANGELOG.md
- **Phase**: design



### OOS_4: Add release note
- **Description**: Add release note. Scenario: belongs to a later release
- **Reviewer**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: release
- **Location**: docs/release.md
- **Phase**: design



<!-- out-of-scope:end -->

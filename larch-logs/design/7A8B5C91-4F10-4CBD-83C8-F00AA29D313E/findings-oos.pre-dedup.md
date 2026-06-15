### OOS_1:
- **Description**: [OUT_OF_SCOPE] Sibling contract still lists 2-post-dispatch as a direct phantom-probe-with-warn consumer. Scenario: After Step 2 moves to step-2-post-dispatch.sh the standalone wrapper doc remains wrong; future edits may re-wire the old two-call path
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/phantom-probe-with-warn.md:3
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Wrapper inlines git symbolic-ref instead of delegating to scripts/git-current-branch.sh. Scenario: Duplicates the approved branch-read surface Step 1 already uses; future git-current-branch.sh contract changes can desync post-dispatch vs BRANCH_NAME capture
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-2-post-dispatch.sh:26-28
- **Phase**: design


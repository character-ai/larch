### OOS_1: [SCOPE-REDUCTION] Map declared invalid implement context to `NeedsUserInput` instead of uncaught `ShipError` in gh/pr wrappers
- **Description**: [SCOPE-REDUCTION] Map declared invalid implement context to `NeedsUserInput` instead of uncaught `ShipError` in gh/pr wrappers. Scenario: Plan mandates `ShipError` for invalid declared tmpdir; `pr_edit_body_file` catches only `NeedsUserInput`, so invalid-context failures may surface as generic errors rather than the existing `EXIT_NEEDS_USER_INPUT` / no-mutation refusal contract
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/git/gh.py:1921-1928
- **Phase**: design




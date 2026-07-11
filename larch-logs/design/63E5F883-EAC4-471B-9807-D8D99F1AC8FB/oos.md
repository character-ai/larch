### FINDING_4: Snapshot validation does not define lifecycle rules for mutable attempt artifacts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The snapshot contract does not distinguish immutable pre-coder artifacts from attempt artifacts intentionally created or replaced during the lifecycle. Revalidating the complete root may reject legitimate attempt artifacts, while accepting arbitrary root changes would weaken tamper detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Define separate validation rules for immutable pre-coder artifacts and mutable attempt artifacts. Authenticate each attempt artifact set after writing it and return an updated validated record, then require cleanup and staging to validate that exact attempt record while still rejecting changes to the pre-coder set.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Map declared invalid implement context to `NeedsUserInput` instead of uncaught `ShipError` in gh/pr wrappers
- **Description**: [SCOPE-REDUCTION] Map declared invalid implement context to `NeedsUserInput` instead of uncaught `ShipError` in gh/pr wrappers. Scenario: Plan mandates `ShipError` for invalid declared tmpdir; `pr_edit_body_file` catches only `NeedsUserInput`, so invalid-context failures may surface as generic errors rather than the existing `EXIT_NEEDS_USER_INPUT` / no-mutation refusal contract
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/git/gh.py:1921-1928
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


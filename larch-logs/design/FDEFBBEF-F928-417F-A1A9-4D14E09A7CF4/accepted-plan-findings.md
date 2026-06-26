### FINDING_1: Empty `fixture_plan` fallback targets non-existent committed plan artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The manifest and replay steps allow empty `fixture_plan` with fallback to committed `larch-logs/implement/<RUN_ID>/` plan artifacts, but the repo ships zero `plan.txt` under implement run logs (and committed logs expose `plan-goals-test.md`, not production-shaped `plan.txt`). An implementer can leave `fixture_plan` empty expecting run-log discovery; replay cannot load valid plan context, `dispatch-voters` runs without the bounded plan the historical vote used, and before/after acceptance comparison is invalid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require every manifest row to name a committed `fixture_plan` path (under `python/test_fixtures/plan-fidelity-calibration/plans/`) or hard-fail reconstruction; drop the larch-logs empty fallback from the manifest column contract and MAY_UPDATE steps
  - From Cursor-Innovation: Require non-empty `fixture_plan` for every manifest row (committed path under `python/test_fixtures/plan-fidelity-calibration/plans/`). Drop the empty fallback to `larch-logs/implement/<RUN_ID>/`; hard-fail manifest validation when `fixture_plan` is missing.
  - From Cursor-Pragmatic: Name the committed artifact explicitly as plan-goals-test.md (or require non-empty fixture_plan for every manifest row). Add a helper step to extract the Implementation Plan body when using plan-goals-test.md, and hard-fail when no readable plan fixture exists.
  - From Cursor-Requirements: Require non-empty fixture_plan for every manifest row (committed under python/test_fixtures/plan-fidelity-calibration/plans/). Require non-empty fixture_diff when the source run used diff context in production. Add NEW fixture dirs for plans/ and diffs/ in Files to modify/create. Remove empty fallback to larch-logs plan/diff artifacts or hard-fail manifest rows with empty paths



### FINDING_1: Plan-review fixture is outside the design temporary directory
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan-review smoke harness passes `--feature-file` from `$TMP` without staging it under `design_tmpdir`. `render plan-review` rejects feature-file paths outside `DESIGN_TMPDIR`, so the invocation exits with status 2 before rendering the prompt or exercising the new assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Copy or write the `[BUG]` feature fixture into `$design_tmpdir` (for example `feature-description.txt`) before `render plan-review`, mirroring the existing `plan.txt` copy; pass that in-tree path to `--feature-file`
  - From Cursor-Requirements: Copy or create the [BUG] feature fixture under $design_tmpdir (for example cp "$feature_file" "$design_tmpdir/feature-description.txt") and pass --feature-file "$design_tmpdir/feature-description.txt" in the render plan-review invocation, matching how plan.txt is staged and how python/tests/rendering/test_rendering.py and plan_review_panel.py supply feature files


### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-prompt-template-invariants.sh:256-267
- **Concern**: Plan-review smoke passes --feature-file from $TMP without copying it under DESIGN_TMPDIR. Scenario: `render plan-review` requires `--feature-file` to resolve under `--design-tmpdir` (`rendering.py` `_validate_design_prompt_file`); the harness keeps `feature_file="$TMP/feature.txt"` while `design_tmpdir="$TMP/design-tmpdir"`, so the updated smoke invocation exits 2 before any new assert_contains pins run
- **Proposed resolution**: Copy or write the `[BUG]` feature fixture into `$design_tmpdir` (for example `feature-description.txt`) before `render plan-review`, mirroring the existing `plan.txt` copy; pass that in-tree path to `--feature-file`



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-prompt-template-invariants.sh:256-267
- **Concern**: Plan-review harness passes --feature-file from $TMP root without copying it under design_tmpdir. Scenario: render plan-review rejects --feature-file paths outside DESIGN_TMPDIR via _validate_design_prompt_file, so the planned smoke call exits 2 before any prompt is rendered; acceptance criterion 2 and the round-1 [BUG]+recovery-surface fixture fix stay unexercised
- **Proposed resolution**: Copy or create the [BUG] feature fixture under $design_tmpdir (for example cp "$feature_file" "$design_tmpdir/feature-description.txt") and pass --feature-file "$design_tmpdir/feature-description.txt" in the render plan-review invocation, matching how plan.txt is staged and how python/tests/rendering/test_rendering.py and plan_review_panel.py supply feature files




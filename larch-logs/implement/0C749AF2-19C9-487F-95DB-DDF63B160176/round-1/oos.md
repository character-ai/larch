### FINDING_7: [OUT_OF_SCOPE] Moderate Cursor default test duplicates the routing matrix
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The standalone Moderate Cursor default test duplicates the cursor/MODERATE row in the routing matrix and adds redundant maintenance surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Tests hardcode the Moderate Cursor model literal
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Tests duplicate `grok-4.5` instead of referencing the configuration map, allowing configuration and test literals to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE] in parametrization
  - From cursor-specialist-edge-cases: Use config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[MODERATE] in the assertion
  - From codex-specialist-edge-cases: Reference the corresponding configuration constant if the test should validate routing rather than pin the literal.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Existing Cursor launcher argv test does not assert the model
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `test_cursor_launcher_builds_agent_argv` does not assert the model argument, so default-path launcher model regressions remain undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Assert --model when extending launcher coverage


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Cursor difficulty-record test lacks Moderate rater-model coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: There is no write-record test for the Cursor MODERATE rater model, so a `--rater-model` argv wiring bug could pass resolver-only tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add cursor MODERATE _write_step2_difficulty_record case


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Cursor launcher difficulty forwarding is tested only for MODERATE
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test_launcher_args_forwards_cursor_difficulty` covers only MODERATE and does not exercise the other difficulty tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optionally parametrize TRIVIAL/MODERATE/HARD for symmetry with plan wording.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Launcher override-to-usage-sidecar coverage is absent
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Override precedence is covered in unit and dispatch tests, but there is no launcher integration test confirming that an override is also reflected in the recorded usage sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add optional test with LARCH_CURSOR_MODEL set at MODERATE asserting recorded usage model is the override.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Unrelated run-log flush is bundled with the test commit
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The `chore(larch-logs)` flush is unrelated to the test change and adds CI noise when validating the feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Keep test-only commits separate from log flushes.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

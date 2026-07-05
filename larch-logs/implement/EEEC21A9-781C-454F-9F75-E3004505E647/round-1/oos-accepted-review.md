### OOS_1: display_text dedupe can collapse distinct execution issues
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Final-report merging keys off `display_text`, so distinct execution issues that truncate to the same text can be counted as one and under-report the total.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Dedupe on `dedupe_key` with `display_text` fallback and add a truncation-collision fixture.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (latent-rerouted)

### OOS_2: Symlinked phase14 flag exclusion lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: There is no regression for a symlinked allowlisted phase14 flag, so a symlink could be misread or mishandled without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test with a symlinked phase14 flag and assert skip is denied and rebase runs.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_3: Sentinel write failure on continue/conflict-fix lacks a regression
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: There is no test for `.ship-pre-fix-rebase-ok` write failure on the continue/conflict-fix path, so a future error-handling regression could still emit `NEXT_ACTION=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Monkeypatch `_ship_pre_fix_write_ok_sentinel` to raise; assert rc != 0 and no `NEXT_ACTION=` in stdout.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Pause-save copies can skip symlinked `.completed` children
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: When `include_completed` is true, `_copy_tree_redacted` can skip symlinked children under `.completed/` while still reporting success, so `pause_save` may publish a snapshot that is missing provenance sentinels needed by later resume checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: When include_completed is true, fail closed on symlinked .completed entries or verify required sentinels exist in the published tree before returning success.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Step 5c provenance coverage is missing end-to-end
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-pause-provenance
- **Severity**: minor
- **Concern**: The current tests stop at pause load or only inspect snapshot contents; they do not run the resumed Step 5c publish gate with the restored provenance set, nor do they assert the pause-save branch preserved `.completed/` in the committed snapshot. That leaves the false-refusal regression uncovered end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add an integration test that restores the #6527-style tmpdir then asserts design publish does not refuse with complete without .completed/step-3; optionally extend test_pause_save_uses_real_log_publish_path to assert .completed/ in the committed pause snapshot.
  - From dyn-dyn-pause-provenance: Extend that test (or add a sibling) to `git ls-tree` / `git show` the pause branch and assert `larch-logs/design/RUN1/.completed/step-1c` is present after a successful `pause_save_main`.
  - From dyn-dyn-pause-provenance: After restore, call the Step 5c publish provenance gate (or a focused helper test) with restored `.step3-review-result.env`, `.completed/step-3`, `composed-plan.md`, and `.completed/step-5b`, and assert publish is not refused for missing `step-3`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0


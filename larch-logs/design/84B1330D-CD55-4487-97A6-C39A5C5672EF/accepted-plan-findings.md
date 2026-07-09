### FINDING_3: Step 5c rc=4 contract test blocks the new refusal class
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The current Step 5c rc=4 test hard-codes `validator-defects`, which conflicts with the new `missing-guideline-assessment` refusal path and will fail once that refusal is routed outside the validator-defect bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `### UPDATED: python/tests/design/test_design_lifecycle.py` (or equivalent): keep the validator-defect case, add a sibling test where `PUBLISH_REFUSE_REASON=missing-guideline-assessment` and `VALIDATE_STATUS=not-run` asserts a distinct `STEP5C_STATUS` (or none) and never `validator-defects`


### FINDING_4: Commit-time completeness verification loses the consumer repo root
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The main commit path calls completeness verification without the consumer repo root, so the new guideline-assessment requirement can be skipped when the run is staged from the ephemeral tmpdir source tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Pass the existing `repo_root` through `verify_run_log_completeness()` and `required_artifacts_for_run()` from `_copy_tree_to_repo_after_completeness()` so the approved design run check runs before the tree copy.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/report/run_log_commit.py` passing resolved `repo_root` into `verify_run_log_completeness`; keep derive-only fallback for audit callers without cwd context.


### FINDING_6: Run-log tests can pass without guideline fixtures
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The new `guideline-assessment` rows depend on a present `ARCHITECTURAL_GUIDELINES.md` at the derived consumer root, but the planned tests can remain vacuous if they never seed that fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin fixtures: write `## /design run <id>: approved` (or `: approved-partition`) into `final-summary.md`, place a valid `ARCHITECTURAL_GUIDELINES.md` at the derived consumer root, and assert the row appears before testing missing-artifact failure


### FINDING_7: Step 5c completion sentinel is written before refusal handling
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: A missing-guideline refusal can still leave `.completed/step-5c` behind, which makes Step 6 and downstream orchestration treat the run as cleanly completed instead of fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the `.completed/step-5c` write after refusal handling, or explicitly remove the sentinel on this refusal path before returning.



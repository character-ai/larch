### FINDING_1: Empty assessment files still pass completeness checks
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A zero-byte or whitespace-only `architectural-guideline-assessment.md` can still satisfy the new presence checks, so publish-time and run-log completeness can accept a run that contains no real assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Treat `present` as regular file with non-empty stripped content in `_check_guideline_assessment_completeness`; mirror the rule in run-log presence (or reuse the same helper) and add tests for empty and whitespace-only files
  - From Cursor-Innovation: Require non-empty content in the shared completeness helper (for example `stat().st_size > 0` or stripped read) for both `present` and artifact-present checks; add publish and run-log tests with a zero-byte regular file.
  - From Cursor-Pragmatic: Require non-empty stripped content in _check_guideline_assessment_completeness and mirror the same rule in run-log verification (extend _verify_has_file or artifact_present_or_waived for slug guideline-assessment). Add a publish test with an empty assessment file that still expects refusal
  - From Cursor-Requirements: Require non-empty stripped content in _check_guideline_assessment_completeness.present, aligned with persist_design_assessment whitespace rejection

### FINDING_2: Repo-root derivation for run-log completeness points at the wrong directory
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `_derive_consumer_repo_root_from_run_dir()` can resolve `larch-logs/design` instead of the consumer git root, so the new required-artifact row is skipped and post-commit completeness never fires on real runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Derive the git toplevel as `run_dir.parent.parent.parent` when the path matches `.../larch-logs/design/<run-id>`, or run `git -C run_dir rev-parse --show-toplevel`; return `None` on mismatch; pin with a fixture under a fake repo root

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

### FINDING_5: ARCH_GUIDE_* fields never reach the Step 5c status env
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The new refusal envelope is only allowlisted in `.design-publish-result.env`, so `step5c_core()` still drops it when it rewrites `.design-step5c-status.env`, and later consumers cannot see the `ARCH_GUIDE_*` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the four `ARCH_GUIDE_*` fields to the rows written to `.design-step5c-status.env` and to `STEP5C_STATUS_ALLOW_KEYS`, not just `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`.

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

### FINDING_8: Missing-guideline warning marker is sticky across retries
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: `.missing-guideline-assessment-warning` is only created, not cleared, so a later successful retry can still carry the warning into `final-summary.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Delete the marker when completeness passes, or clear it before rerunning publish after Gate C so the summary prefix reflects the current state only.

### FINDING_9: Warning can precede the final-summary header
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Prefixing the warning ahead of the `## /design run ...` heading can break consumers that require the final-summary header to remain on the first line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Insert the warning immediately after the `## /design run ...` heading in normal and fallback summaries, and test that the header remains first.

### FINDING_10: Approved-partition runs may fail guideline-assessment gating
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: If partition runs exit before Gate C assessment persistence, treating `approved-partition` as requiring `architectural-guideline-assessment.md` will false-fail runs that never had a chance to create the artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Limit _design_run_approved and the guideline-assessment RequiredArtifact condition to terminal : approved only; exclude approved-partition unless partition runs are proven to reach persist-design-assessment

### FINDING_11: publish_rc 4 still labels missing-guideline refusals as validator-defects
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The Step 5c publish_rc=4 branch still appears to force `validator-defects`, so the new `missing-guideline-assessment` refusal will not have a distinct status in bgjob logs and contract tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Branch publish_rc 4 on PUBLISH_REFUSE_REASON=missing-guideline-assessment to emit STEP5C_STATUS=missing-guideline-assessment (or gate-c-refusal) and add matching test_design_lifecycle coverage

### FINDING_12: approved-partition publishes are not covered by the publish completeness gate
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The publish-side completeness gate is described as applying only to `approved`, so split runs that end as `approved-partition` can bypass the degraded warning/waiver path even when the assessment is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Use an explicit approved outcome set containing approved and approved-partition in the completeness helper and degraded log-publish path. Add a focused approved-partition missing-artifact test.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py
- **Concern**: [SCOPE-REDUCTION] Degraded path adds a second tmpdir marker on top of the execution issue. Scenario: The plan writes both a Warnings execution issue and .missing-guideline-assessment-warning, then design_summary.py reads the marker. That duplicates state and the marker is not in _publish_excluded, so it can land in committed design logs as noise
- **Proposed resolution**: Drive the summary prefix from the committed Warnings entry (or a single KV written into execution-issues.md) and drop .missing-guideline-assessment-warning unless publish filter excludes it

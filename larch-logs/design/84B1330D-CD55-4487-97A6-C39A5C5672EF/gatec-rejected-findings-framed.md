---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Empty assessment files still pass completeness checks
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A zero-byte or whitespace-only `architectural-guideline-assessment.md` can still satisfy the new presence checks, so publish-time and run-log completeness can accept a run that contains no real assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Treat `present` as regular file with non-empty stripped content in `_check_guideline_assessment_completeness`; mirror the rule in run-log presence (or reuse the same helper) and add tests for empty and whitespace-only files
  - From Cursor-Innovation: Require non-empty content in the shared completeness helper (for example `stat().st_size > 0` or stripped read) for both `present` and artifact-present checks; add publish and run-log tests with a zero-byte regular file.
  - From Cursor-Pragmatic: Require non-empty stripped content in _check_guideline_assessment_completeness and mirror the same rule in run-log verification (extend _verify_has_file or artifact_present_or_waived for slug guideline-assessment). Add a publish test with an empty assessment file that still expects refusal
  - From Cursor-Requirements: Require non-empty stripped content in _check_guideline_assessment_completeness.present, aligned with persist_design_assessment whitespace rejection


### [Plan Review] FINDING_5

### FINDING_5: ARCH_GUIDE_* fields never reach the Step 5c status env
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The new refusal envelope is only allowlisted in `.design-publish-result.env`, so `step5c_core()` still drops it when it rewrites `.design-step5c-status.env`, and later consumers cannot see the `ARCH_GUIDE_*` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the four `ARCH_GUIDE_*` fields to the rows written to `.design-step5c-status.env` and to `STEP5C_STATUS_ALLOW_KEYS`, not just `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`.


### [Plan Review] FINDING_8

### FINDING_8: Missing-guideline warning marker is sticky across retries
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: `.missing-guideline-assessment-warning` is only created, not cleared, so a later successful retry can still carry the warning into `final-summary.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Delete the marker when completeness passes, or clear it before rerunning publish after Gate C so the summary prefix reflects the current state only.


### [Plan Review] FINDING_9

### FINDING_9: Warning can precede the final-summary header
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Prefixing the warning ahead of the `## /design run ...` heading can break consumers that require the final-summary header to remain on the first line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Insert the warning immediately after the `## /design run ...` heading in normal and fallback summaries, and test that the header remains first.


### [Plan Review] FINDING_10

### FINDING_10: Approved-partition runs may fail guideline-assessment gating
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: If partition runs exit before Gate C assessment persistence, treating `approved-partition` as requiring `architectural-guideline-assessment.md` will false-fail runs that never had a chance to create the artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Limit _design_run_approved and the guideline-assessment RequiredArtifact condition to terminal : approved only; exclude approved-partition unless partition runs are proven to reach persist-design-assessment


### [Plan Review] FINDING_11

### FINDING_11: publish_rc 4 still labels missing-guideline refusals as validator-defects
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The Step 5c publish_rc=4 branch still appears to force `validator-defects`, so the new `missing-guideline-assessment` refusal will not have a distinct status in bgjob logs and contract tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Branch publish_rc 4 on PUBLISH_REFUSE_REASON=missing-guideline-assessment to emit STEP5C_STATUS=missing-guideline-assessment (or gate-c-refusal) and add matching test_design_lifecycle coverage


### [Plan Review] FINDING_12

### FINDING_12: approved-partition publishes are not covered by the publish completeness gate
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The publish-side completeness gate is described as applying only to `approved`, so split runs that end as `approved-partition` can bypass the degraded warning/waiver path even when the assessment is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Use an explicit approved outcome set containing approved and approved-partition in the completeness helper and degraded log-publish path. Add a focused approved-partition missing-artifact test.


### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py
- **Concern**: [SCOPE-REDUCTION] Degraded path adds a second tmpdir marker on top of the execution issue. Scenario: The plan writes both a Warnings execution issue and .missing-guideline-assessment-warning, then design_summary.py reads the marker. That duplicates state and the marker is not in _publish_excluded, so it can land in committed design logs as noise
- **Proposed resolution**: Drive the summary prefix from the committed Warnings entry (or a single KV written into execution-issues.md) and drop .missing-guideline-assessment-warning unless publish filter excludes it


---LARCH-REJECTED-END---

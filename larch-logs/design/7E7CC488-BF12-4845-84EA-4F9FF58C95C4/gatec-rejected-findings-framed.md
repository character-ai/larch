---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_4

### FINDING_4: Failed post-write validation can delete or overwrite a previously valid assessment
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: A re-authoring attempt may overwrite an existing note and then fail while writing or validating metadata, sidecar, or receipt artifacts. Cleanup that removes the failed attempt's files without preserving prior state can cause data loss and leave no recoverable assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the write a transaction: validate before writing, stage all artifacts under attempt-specific paths, and atomically commit them together; or snapshot and restore the prior note, metadata, sidecar, and receipt when post-write validation fails. Limit cleanup to artifacts owned by the current attempt.
  - From Codex-Innovation: Add transactional preservation: validate before writes, record which target paths were absent or back up existing artifacts, and on re-author cleanup remove only newly created files or restore the prior note, metadata, and sidecar atomically


### [Plan Review] FINDING_5

### FINDING_5: The invariant staged-writer path does not carry an explicit validated outcome
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The plan names an explicit outcome for guideline staged writing but does not fully update the invariant staged-writer function, CLI, and callers. Invariant refresh, pin, or report paths may continue deriving `ASSESSMENT_KIND` from prose, reintroducing prose-based routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the invariant staged wrapper or document the direct CLI contract, thread a required-by-validation `--outcome` through `write_invariant_staged_assessment`, and update invariant staged refresh, pin, and report callers to preserve and validate it


---LARCH-REJECTED-END---

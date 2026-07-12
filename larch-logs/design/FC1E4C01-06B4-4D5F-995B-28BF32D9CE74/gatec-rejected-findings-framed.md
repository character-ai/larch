---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Include committed run-log discovery in the repoint set
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `python/larch/design/design_step_log.py` still discovers committed runs with a raw `larch-logs/implement/*/manifest.json` glob. This bypasses the shared containment and manifest-acceptance policy and conflicts with the planned adoption ratchet.
- **Suggested revisions (informational for voters; coder decides)**:


### [Plan Review] FINDING_3

### FINDING_3: Repoint committed plan-review classification traversal
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `_design_plan_review_round_dirs` still enumerates committed `plan-review/round-*` directories with a raw glob, leaving a committed corpus walk outside the shared API and potentially bypassing containment and symlink policy.
- **Suggested revisions (informational for voters; coder decides)**:


### [Plan Review] FINDING_4

### FINDING_4: Specify file-level safety for classification artifacts
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The classification helpers do not specify whether returned TSV artifacts must be regular, non-symlink files contained within the run directory. A symlink such as `findings-classification.tsv` could otherwise point outside the committed corpus.
- **Suggested revisions (informational for voters; coder decides)**:


### [Plan Review] FINDING_9

### FINDING_9: Add required regression files to the firm file list
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The plan requires difficulty-calibration, fluff-analysis, voter-calibration, and final-report regression coverage but does not list the corresponding test and harness files under `Files to modify/create`. Implementations could omit those checks while still claiming the stated validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the exact affected test and harness paths to `Files to modify/create`, including `python/tests/calibration/test_difficulty_calibration.py`, the fluff and voter shell harnesses, and `python/tests/report/test_final_report.py` if its metadata boundary changes.


### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:267-271
- **Concern**: [SCOPE-REDUCTION] `final_report.py` firm update appears unnecessary. Scenario: The listed reads are session-local `implement_tmpdir/.../manifest.json` lookups for token/outcome recovery, not committed `larch-logs` walks or dual-manifest loops. They are already excluded by the plan’s session-manifest carve-out and are not ratchet targets. Drop `### UPDATED: python/larch/report/final_report.py` and the associated `test_final_report.py` corpus-boundary work unless a concrete committed-corpus call site is identified.
- **Proposed resolution**:


---LARCH-REJECTED-END---

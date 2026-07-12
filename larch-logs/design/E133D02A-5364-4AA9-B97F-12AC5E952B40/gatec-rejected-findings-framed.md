---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3: Preserve lenient historical rejected-OOS heading IDs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Replacing `_REJECTED_OOS_BLOCK_RE` with the canonical parser may reject historical rejected-OOS headings whose IDs contain alphanumeric or underscore characters, reducing rejected-OOS audit output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either keep a local malformed/historical-ID matcher with a reason-bearing lint suppression for this diagnostic path, or extend the migration note to use a compose/historical boundary mode that still accepts alphanumeric IDs for rejected-OOS audit only.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:1080-1091
- **Concern**: [SCOPE-REDUCTION] audit_runs.py is listed for canonical block-parser migration but only uses vote-table and prose-body diagnostic regexes, not reviewer-item block segmentation. Scenario: Including it adds churn without advancing the one-owner goal; prior concern about a missing consumer was based on non-segmentation scans
- **Proposed resolution**: Drop `audit_runs.py` from the firm file set; keep only the existing vote-table and malformed-prose diagnostics local, and document them as lint-exempt distinct grammars if the new detector would match them


---LARCH-REJECTED-END---

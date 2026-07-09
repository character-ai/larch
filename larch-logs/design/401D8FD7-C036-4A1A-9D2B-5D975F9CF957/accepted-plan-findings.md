### FINDING_2: Ensure architectural-invariants read emits the full invariant body
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The plan still permits `I-Stale-1` to land in a form that `architectural-invariants read` strips, so the canonical reader surface may show only the heading instead of the full invariant body required by acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Reformat I-Stale-1 into `- Why:` bullets so the reader emits the full body, or widen this PR to update `parse_invariant_entries` and its tests."
  - From Codex-Pragmatic: "Revise the plan so the read command emits the full `I-Stale-1` body, either by updating `parse_invariant_entries` with focused tests or by formatting the invariant in the reader-supported shape while preserving the required normative content"
  - From Codex-Requirements: "Make the firm plan satisfy full-body read output: either format the new invariant body using reader-preserved `- Why:` lines, or add firm parser and targeted test updates that preserve invariant prose in `architectural-invariants read`"



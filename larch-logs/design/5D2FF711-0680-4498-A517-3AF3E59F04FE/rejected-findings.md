### [Plan Review] FINDING_2

### FINDING_2: Security OOS lookup misses production design artifacts
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Progress-report security filtering still appears to search only round-local files, so accepted security OOS can be counted when the production design source lives outside `round_dir`; that risks letting security-tagged OOS into proposed/fileable counts unless the lookup spans the design and ballot artifacts used in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the progress-report OOS security lookup used for classification and markdown rows to search production design sources, including round_dir.parent.parent/security-oos-observations.md and root findings-oos.md or ballot sources, before counting proposed/fileable; add a production-shaped design round test.


### [Plan Review] FINDING_3

### FINDING_3: Security exclusion must decrement proposed counts
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The security OOS exclusion is still wired around the old accepted/fileable slot, so accepted security rows can leak into `OOS_PROPOSED_COUNT` or operator-facing proposed counts after the split, and `write_implement_round_meta` still lacks the design-side decrement applied elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Apply the same security skip/decrement in `write_implement_round_meta` (shared helper used by both writers, or call `_adjust_design_security_oos` on the proposed bucket before persisting). Add an implement-side regression mirroring `test_write_design_round_meta_security_oos_and_panel`.
  - From Cursor-Requirements: Vote-accepted security OOS leaks into operator-facing `OOS proposed` despite the edge-case requirement to exclude security-tagged OOS from both columns. Extend `_adjust_design_security_oos` (or the new proposed/fileable derivation) so accepted security rows decrement `OOS_PROPOSED_COUNT` / proposed render counts as well as fileable counts; add a design meta test with accepted security OOS asserting both proposed and fileable stay zero.



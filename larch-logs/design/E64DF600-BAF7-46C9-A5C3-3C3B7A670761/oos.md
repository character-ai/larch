### FINDING_3: Violation preservation is not enforceable with unconditional sidecar clear
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Acceptance requires that unavailable never erases a blocking invariant violation. The plan adds classification precedence only in `ship_guidelines.py`, but `_invariants_gate_before_pr` always clears the invariant outcome sidecar before gate evaluation and `write_invariant_ship_outcome` always rewrites it. A later unavailable refresh therefore drops a persisted `violation` outcome before classification can preserve it, even if the durable violation note still exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify and test a no-clobber write contract: read the existing invariant outcome sidecar (and authored violation durable note) before clear/write; when the new gate resolves to unavailable, keep the existing violation outcome and skip unavailable downgrade. Document the touch point (`ship.py` gate and/or `write_invariant_ship_outcome`) in the firm plan files.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)


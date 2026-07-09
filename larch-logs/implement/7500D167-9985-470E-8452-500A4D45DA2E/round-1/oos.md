### FINDING_7: [OUT_OF_SCOPE] module-level prefix tables in preflight/deps_audit can drift outside lint coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ast-ratchet
- **Severity**: minor
- **Concern**: Lifecycle prefixes still live in module-level tuple/dict aggregates in `preflight.py` and `deps_audit.py`, but this lint only sees the narrower comparison/match AST surface, so those duplicates can drift unless the tables import the tracked constants directly or scope expands later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Expand scope in a follow-up or refactor those tables to import config/title_match constants directly
  - From dyn-dyn-ast-ratchet: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] legacy admission prefixes remain outside the tracked token map
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `admission.py` still relies on handwritten legacy prefix entries, so retired lifecycle tokens can remain matched even though this lint cannot see them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Keep the legacy shell audit or hoist those tokens into config if they should be ratcheted


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] stale baseline rows are left unmatched until regeneration
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: When baselined rows no longer have a live match, check mode does not call attention to them, so manual regeneration is still needed to clear stale baseline entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document regen-after-refactor workflow; optional follow-up could warn on unmatched baseline keys


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] scan_file suppresses parse and IO errors without diagnostics
- **Reviewer(s)**: dyn-dyn-ast-ratchet
- **Severity**: minor
- **Concern**: If a file cannot be parsed or opened, the scanner returns no findings and the failure is silent, so check mode can miss violations in unreadable or broken production files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-ratchet: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] future match/case selectors sit outside the current context set
- **Reviewer(s)**: dyn-dyn-ast-ratchet
- **Severity**: minor
- **Concern**: Python 3.10 `match`/`case` patterns are not included in `CONTEXT_KINDS`, so a lifecycle literal in a future `case "[DONE]":` selector would not be flagged under the current closed set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-ratchet: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


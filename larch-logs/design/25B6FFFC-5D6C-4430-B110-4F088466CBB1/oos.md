### OOS_2: [OUT_OF_SCOPE] Consolidate commit-route coverage relay into scope_disposition
- **Description**: [OUT_OF_SCOPE] Consolidate commit-route coverage relay into scope_disposition. Scenario: _relay_scope_coverage duplicates advisory fallback and KV emission logic that validate_disposition_for_ship already owns; two edited paths increase the chance commit routing and ship validation diverge after hardening
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:59-104
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Reuse existing no-follow read helper before adding generic trusted-I/O primitives
- **Description**: [OUT_OF_SCOPE] Reuse existing no-follow read helper before adding generic trusted-I/O primitives. Scenario: architectural_guidelines already implements _read_regular_text_no_follow; the plan adds a second generic trusted-read layer in io.py plus snapshot-local copies, increasing surface area for a coverage-only fix
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/io.py:1-120
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


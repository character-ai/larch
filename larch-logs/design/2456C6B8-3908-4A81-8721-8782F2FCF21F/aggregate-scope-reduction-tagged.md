### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan:Issue disposition
- **Concern**: [SCOPE-REDUCTION] Issue disposition adds GitHub comment/close steps unrelated to the test-only deliverable. Scenario: The binding scope is a regression guard for the three named `issue_wire` consumers; closing #7047 is operator tracking work that does not affect whether the ratchet ships or prevents marker bypasses
- **Proposed resolution**: Remove the Issue disposition section from the plan; handle #7047 closure outside implementation or in a separate operator checklist if still required ### Numbered findings 1. **architecture** — plan:Issue disposition — **[SCOPE-REDUCTION]** The plan’s only firm deliverable is `python/tests/issue/test_plan_marker_ownership.py`. The “Issue disposition” section (comment on #7047, close as fixed by #7095) is GitHub lifecycle work, not part of the ratchet. The scope anchor targets marker-grammar bypass regression for `decompose.py`, `design_router.py`, and `learn_from_bugs.py`; the guard ships without any issue mutation. **Suggested revision:** Drop Issue disposition from the plan body. ### Review notes (not TSV) The plan aligns with the current tree: all three consumers already call the assigned helpers (`issue_wire.compose_named_block`, `issue_wire.parse_named_block`, `issue_wire.named_block_marker_re`), and `python/larch/` has no hardcoded `larch:plan:start`/`larch:plan:end` outside excluded `issue_wire.py`. Versioned tracking markers (`larch:plan v1`) and operator prose (`larch:plan block`) will not trip the proposed substring guard. Scan scope limited to `python/larch/` matches the OOS observation; other runtime paths (`analyze_bugs.py` via `strip_named_block`, preflight/plan_review via CLI) already route through `issue_wire`.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/issue/test_plan_marker_ownership.py:5-14 (planned)
- **Concern**: [SCOPE-REDUCTION] Add no permanent ownership scanner for explicitly out-of-scope files. Scenario: The current HEAD already routes all three consumers through issue_wire, so this adds maintenance without changing runtime behavior.
- **Proposed resolution**: Remove the new test file; retain the existing #7095 unification and issue disposition.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/issue/test_plan_marker_ownership.py (plan)
- **Concern**: [SCOPE-REDUCTION] Drop Issue disposition from the plan. Scenario: The plan mixes a test-only deliverable with operator GitHub workflow (comment on #7047, close as fixed by #7095). That is not code, not CI, and expands implement scope beyond the ratchet.
- **Proposed resolution**: Remove the Issue disposition section from the plan; handle issue closure in the PR description or a separate operator step after merge.

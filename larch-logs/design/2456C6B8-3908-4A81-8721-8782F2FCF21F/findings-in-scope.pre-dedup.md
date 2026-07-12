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



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py:10-13 (planned)
- **Concern**: AST checks verify helper names but not marker arguments. Scenario: A call using marker="design-pause" would satisfy the check while plan detection or boundary trimming silently stops working.
- **Proposed resolution**: Require marker="plan", plus kind="start" for named_block_marker_re, at the relevant call sites.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/issue/test_plan_marker_ownership.py (plan)
- **Concern**: [SCOPE-REDUCTION] Drop Issue disposition from the plan. Scenario: The plan mixes a test-only deliverable with operator GitHub workflow (comment on #7047, close as fixed by #7095). That is not code, not CI, and expands implement scope beyond the ratchet.
- **Proposed resolution**: Remove the Issue disposition section from the plan; handle issue closure in the PR description or a separate operator step after merge.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py (plan)
- **Concern**: Literal scan should target AST string nodes, not whole-file substring search. Scenario: The plan says fail when a source string hardcodes the markers but does not pin detection to string literals. A naive `in file_text` scan false-fails on comments, docstrings, or prose that quotes `larch:plan:start` while runtime behavior still delegates to issue_wire.
- **Proposed resolution**: Walk each module AST and flag only `ast.Constant`/`ast.JoinedStr` nodes (or equivalent) whose decoded value contains `larch:plan:start` or `larch:plan:end`; keep `issue_wire.py` excluded.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py
- **Concern**: Raw substring scan for larch:plan:start/end can false-positive on comments or docstrings. Scenario: A maintainer adds a comment or docstring that quotes the marker grammar; the ratchet fails even though runtime code still delegates to issue_wire
- **Proposed resolution**: Scan only AST string constants (or strip comments before substring scan) so documentation examples do not trip the guard



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py
- **Concern**: AST presence checks do not pin plan marker keyword arguments. Scenario: A consumer keeps calling issue_wire.parse_named_block or compose_named_block but passes marker other than plan; the ratchet passes while /design routing or partition stubs break
- **Proposed resolution**: Require keyword marker=plan on parse_named_block and compose_named_block calls and kind=start on named_block_marker_re in the three named consumers



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py:10-13
- **Concern**: AST checks require helper names but not the plan-marker arguments. Scenario: A consumer can call the assigned helper with marker="design-pause" or kind="end"; the ownership test passes while plan generation, routing, or boundary detection breaks
- **Proposed resolution**: Require marker="plan" for all three calls, plus kind="start" for named_block_marker_re 1. [correctness] `python/tests/issue/test_plan_marker_ownership.py:10-13`: The AST checks should validate the arguments, not only helper presence. Otherwise an incorrect helper call still satisfies the ratchet and breaks plan handling. Require the exact `plan` marker, and `kind="start"` for `named_block_marker_re`.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_plan_marker_ownership.py
- **Concern**: AST checks require helper calls but not the required plan-marker arguments. Scenario: A consumer can call the shared helper with marker="design-pause" or the wrong kind and pass the guard while plan handling breaks
- **Proposed resolution**: Verify marker="plan" for all three calls and kind="start" for named_block_marker_re 1. **Correctness**: Require the AST checks to validate the helper arguments, not only the callee names.




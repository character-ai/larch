---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Validate plan-marker arguments in ownership checks
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: AST checks verify helper usage but not marker or kind arguments, allowing incorrect calls to pass while breaking plan handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require marker="plan", plus kind="start" for named_block_marker_re, at the relevant call sites.
  - From Cursor-Pragmatic: Require keyword marker=plan on parse_named_block and compose_named_block calls and kind=start on named_block_marker_re in the three named consumers
  - From Codex-Pragmatic: Require marker="plan" for all three calls, plus kind="start" for named_block_marker_re 1. [correctness] `python/tests/issue/test_plan_marker_ownership.py:10-13`: The AST checks should validate the arguments, not only the callee names. Otherwise an incorrect helper call still satisfies the ratchet and breaks plan handling. Require the exact `plan` marker, and `kind="start"` for `named_block_marker_re`.
  - From Codex-Requirements: Verify marker="plan" for all three calls and kind="start" for named_block_marker_re 1. **Correctness**: Require the AST checks to validate the helper arguments, not only the callee names.


### [Plan Review] FINDING_2

### FINDING_2: Restrict marker scans to code literals
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Whole-file substring scans can falsely flag comments, docstrings, or quoted documentation instead of detecting runtime marker ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Walk each module AST and flag only `ast.Constant`/`ast.JoinedStr` nodes (or equivalent) whose decoded value contains `larch:plan:start` or `larch:plan:end`; keep `issue_wire.py` excluded.
  - From Cursor-Pragmatic: Scan only AST string constants (or strip comments before substring scan) so documentation examples do not trip the guard


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan:Issue disposition
- **Concern**: [SCOPE-REDUCTION] Issue disposition adds GitHub comment/close steps unrelated to the test-only deliverable. Scenario: The binding scope is a regression guard for the three named `issue_wire` consumers; closing #7047 is operator tracking work that does not affect whether the ratchet ships or prevents marker bypasses
- **Proposed resolution**: Remove the Issue disposition section from the plan; handle #7047 closure outside implementation or in a separate operator checklist if still required ### Numbered findings 1. **architecture** — plan:Issue disposition — **[SCOPE-REDUCTION]** The plan’s only firm deliverable is `python/tests/issue/test_plan_marker_ownership.py`. The “Issue disposition” section (comment on #7047, close as fixed by #7095) is GitHub lifecycle work, not part of the ratchet. The scope anchor targets marker-grammar bypass regression for `decompose.py`, `design_router.py`, and `learn_from_bugs.py`; the guard ships without any issue mutation. **Suggested revision:** Drop Issue disposition from the plan body. ### Review notes (not TSV) The plan aligns with the current tree: all three consumers already call the assigned helpers (`issue_wire.compose_named_block`, `issue_wire.parse_named_block`, `issue_wire.named_block_marker_re`), and `python/larch/` has no hardcoded `larch:plan:start`/`larch:plan:end` outside excluded `issue_wire.py`. Versioned tracking markers (`larch:plan v1`) and operator prose (`larch:plan block`) will not trip the proposed substring guard. Scan scope limited to `python/larch/` matches the OOS observation; other runtime paths (`analyze_bugs.py` via `strip_named_block`, preflight/plan_review via CLI) already route through `issue_wire`.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/issue/test_plan_marker_ownership.py:5-14 (planned)
- **Concern**: [SCOPE-REDUCTION] Add no permanent ownership scanner for explicitly out-of-scope files. Scenario: The current HEAD already routes all three consumers through issue_wire, so this adds maintenance without changing runtime behavior.
- **Proposed resolution**: Remove the new test file; retain the existing #7095 unification and issue disposition.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/issue/test_plan_marker_ownership.py (plan)
- **Concern**: [SCOPE-REDUCTION] Drop Issue disposition from the plan. Scenario: The plan mixes a test-only deliverable with operator GitHub workflow (comment on #7047, close as fixed by #7095). That is not code, not CI, and expands implement scope beyond the ratchet.
- **Proposed resolution**: Remove the Issue disposition section from the plan; handle issue closure in the PR description or a separate operator step after merge.


---LARCH-REJECTED-END---

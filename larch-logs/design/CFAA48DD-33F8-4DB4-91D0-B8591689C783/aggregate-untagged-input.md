### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.tsv:2
- **Concern**: The TSV restore for `skills/design/SKILL.md` raises `expected_count` to 1 but never restores `step_markers=2b`.. Scenario: Without `step_markers`, lint only checks file-level `readability-style.md`.**` count. A Step 2b anchor can land outside `<!-- step:2b -->` (for example near line 72) and still pass, so plan drafting may miss the composition-site load the issue targets.
- **Proposed resolution**: Set the SKILL.md row to `expected_count=1` with `step_markers=2b`, and place the restored MANDATORY anchor inside the Step 2b body.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:466
- **Concern**: The `checks_run_relevant.py` update is named but not pinned to concrete trigger paths.. Scenario: The plan adds a vague readability router while the existing rule only keys off the TSV pair. Edits to `skills/shared/readability-style.md`, `python/larch/lint/lint_readability_preamble.py`, `python/larch/design/design_step2b.py`, or `python/larch/rendering/rendering.py` can still skip `make test-lint-readability-preamble`, rendering tests, and `make test-design-structure`.
- **Proposed resolution**: Add one `_DIRECT_TARGET_RULES` tuple listing those paths (plus `scripts/test-design-structure.sh` when touched) and map them to the readability/structural tests named in Testing strategy.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:3
- **Concern**: Public /design reference repoint steps are incomplete on path form.. Scenario: `discussion-rounds.md`, `approval-gates.md`, and `brainstorm.md` still use bare `skills/design/references/readability-style.md` in counted MANDATORY lines. The planned SKILL.md-only path walk will not catch reference regressions, and consumer installs can keep resolving the wrong path after the move.
- **Proposed resolution**: In each listed reference `### UPDATED`, require repoint to `` `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.** `` in every MANDATORY anchor, not just a shared file move.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:3
- **Concern**: Firm UPDATED entry for discussion-rounds.md has no repoint action while the file still cites the deleted design-scoped path.. Scenario: After the move, line 3 keeps `skills/design/references/readability-style.md` and breaks the surviving Step 1c/1d anchor; lint count can still pass while the path is wrong.
- **Proposed resolution**: Add the same repoint bullet as approval-gates: update the MANDATORY line to `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` with the counted `.**` suffix.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-readability-preamble.tsv
- **Concern**: Plan raises `skills/design/SKILL.md` to expected_count=1 for Step 2b but does not require `step_markers=2b`.. Scenario: Without the column, placement lint is skipped and the anchor can sit outside the `<!-- step:2b -->` body while still passing exact-count.
- **Proposed resolution**: Set the SKILL.md row to `expected_count=1` with `step_markers=2b` when restoring the Step 2b MANDATORY anchor.

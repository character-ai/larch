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



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:72-72
- **Concern**: [SCOPE-REDUCTION] The plan restores a Step 2b anchor but does not explicitly retire the global soft read at line 72.. Scenario: After restore, `SKILL.md` can load readability guidance twice: always at line 72 and again at Step 2b line 315. That repeats the #5273 token-cost surface the issue is undoing without improving coverage.
- **Proposed resolution**: State in `skills/design/SKILL.md` UPDATED: remove the global soft read at line 72 once the Step 2b MANDATORY anchor exists; keep only composition-site loads.



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-readability-preamble.tsv:1
- **Concern**: [SCOPE-REDUCTION] The plan adds both per-skill manifest rows and a dynamic `SKILL.md` walk with exemptions.. Scenario: Every new skill then needs a TSV row plus satisfying the walker, doubling maintenance and inflating the committed floor without adding enforcement the walker does not already provide.
- **Proposed resolution**: Use the dynamic walk plus exemption rows for `skills/*/SKILL.md` coverage; keep per-file TSV rows only for counted orchestrator-inline and external-prompt sites.



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



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:72-315
- **Concern**: [SCOPE-REDUCTION] Plan restores a Step 2b MANDATORY anchor but leaves the global soft read (line 72) and in-step soft read (line 315).. Scenario: That reintroduces duplicate loads and extra token cost that #5273 removed; two soft reads plus one MANDATORY load the same file three times per run.
- **Proposed resolution**: Remove or replace the soft reads when adding the Step 2b counted MANDATORY anchor; keep one load at the composition site only.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-readability-preamble.tsv
- **Concern**: [SCOPE-REDUCTION] Plan adds both a dynamic every-`SKILL.md` walk with exemptions and per-skill manifest rows for all public/dev skills.. Scenario: Issue acceptance needs the walk plus floor metadata, not duplicate per-skill `orchestrator-inline` rows; dual enforcement inflates the floor sum and doubles maintenance on every new skill.
- **Proposed resolution**: Limit new TSV rows to real composition references (`design-outline`, `finalize-step5`, implement reference files); let the SKILL.md walk plus exemption rows enforce catalog coverage.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-brainstorm-prompts.sh
- **Concern**: [SCOPE-REDUCTION] Firm UPDATE to test-brainstorm-prompts.sh/.md is not required for correctness.. Scenario: The harness only checks `<READABILITY_STYLE>` token lines and brainstorm.md path pins, not the readability file location, so the firm file adds churn without new enforcement.
- **Proposed resolution**: Drop the firm UPDATE or downgrade to MAY_UPDATE only if a new shared-path assertion is actually added.




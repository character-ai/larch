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

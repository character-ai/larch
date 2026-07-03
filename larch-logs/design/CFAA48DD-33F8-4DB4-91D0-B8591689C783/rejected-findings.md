### [Plan Review] FINDING_1

### FINDING_1: Step 2b anchor needs placement lint
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The TSV restore for `skills/design/SKILL.md` raises the count, but without `step_markers=2b` lint can still miss whether the restored MANDATORY anchor is actually inside the Step 2b body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Set the SKILL.md row to `expected_count=1` with `step_markers=2b`, and place the restored MANDATORY anchor inside the Step 2b body.
  - From Cursor-Requirements: Set the SKILL.md row to `expected_count=1` with `step_markers=2b` when restoring the Step 2b MANDATORY anchor.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:72-72
- **Concern**: [SCOPE-REDUCTION] The plan restores a Step 2b anchor but does not explicitly retire the global soft read at line 72.. Scenario: After restore, `SKILL.md` can load readability guidance twice: always at line 72 and again at Step 2b line 315. That repeats the #5273 token-cost surface the issue is undoing without improving coverage.
- **Proposed resolution**: State in `skills/design/SKILL.md` UPDATED: remove the global soft read at line 72 once the Step 2b MANDATORY anchor exists; keep only composition-site loads.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-readability-preamble.tsv:1
- **Concern**: [SCOPE-REDUCTION] The plan adds both per-skill manifest rows and a dynamic `SKILL.md` walk with exemptions.. Scenario: Every new skill then needs a TSV row plus satisfying the walker, doubling maintenance and inflating the committed floor without adding enforcement the walker does not already provide.
- **Proposed resolution**: Use the dynamic walk plus exemption rows for `skills/*/SKILL.md` coverage; keep per-file TSV rows only for counted orchestrator-inline and external-prompt sites.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:72-315
- **Concern**: [SCOPE-REDUCTION] Plan restores a Step 2b MANDATORY anchor but leaves the global soft read (line 72) and in-step soft read (line 315).. Scenario: That reintroduces duplicate loads and extra token cost that #5273 removed; two soft reads plus one MANDATORY load the same file three times per run.
- **Proposed resolution**: Remove or replace the soft reads when adding the Step 2b counted MANDATORY anchor; keep one load at the composition site only.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-readability-preamble.tsv
- **Concern**: [SCOPE-REDUCTION] Plan adds both a dynamic every-`SKILL.md` walk with exemptions and per-skill manifest rows for all public/dev skills.. Scenario: Issue acceptance needs the walk plus floor metadata, not duplicate per-skill `orchestrator-inline` rows; dual enforcement inflates the floor sum and doubles maintenance on every new skill.
- **Proposed resolution**: Limit new TSV rows to real composition references (`design-outline`, `finalize-step5`, implement reference files); let the SKILL.md walk plus exemption rows enforce catalog coverage.



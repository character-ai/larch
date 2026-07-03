### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:92
- **Concern**: Step 0-pre When clause still forces a pre-0a read of flags.md. Scenario: Removing the MANDATORY READ block at line 24 does not remove the When gate at line 92. Orchestrators can still load flags.md on every /design run, undermining the eager-closure drop and Python-owned validation goal.
- **Proposed resolution**: In the Step 0-pre section, change the When line to run immediately before Step 0a (or before session setup) with no flags.md read prerequisite. Align any nearby Step 0-pre prose that still implies flags.md is required first.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:14
- **Concern**: Public flags prose still claims normative parse authority after header demotion. Scenario: The plan demotes flags.md to conditional background in the header but leaves line 14 calling a nonexistent script path and marking parse validation as normative. Editors and operators get conflicting authority signals in the same edit.
- **Proposed resolution**: When replacing parse-argv with parse-flags on line 14, repoint to python/cli.py design parse-flags and reword the sentence as background-only (not normative validation). Keep the plan-size and later sections untouched per plan scope.



### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:14
- **Concern**: [SCOPE-REDUCTION] flags.md body can still claim normative validation authority. Scenario: The plan limits authority edits to the header, so the Public flags section can still say parse-flags is normative after the PR. That leaves flags.md as a competing validation source instead of a conditional prose reference.
- **Proposed resolution**: Extend the flags.md update to remove or soften all normative validation wording, including the Public flags sentence, while still leaving non-argv sections unchanged.




### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:Approach;skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Optional Step 5b.5 sanitizer pre-check adds complexity without clearing the issue's minimum-change bar. Scenario: The binding scope targets Claude-authored narration in the Step 5b.5 diagram sequence. The issue transcript also shows harness-visible `Ran N shell commands` and failed ad-hoc sanitize invocations. Step 5c already owns authoritative sanitize/promote/skip via `python/larch/design/design_publish.py::_sanitize_diagram_candidate`. A silent pre-check still adds orchestrator Bash surface, preserves uncontrollable harness noise, and reopens wrong-flag probing without changing publish behavior.
- **Proposed resolution**: Drop the optional pre-check from SKILL.md, finalize-step5.md, and structural tests. Require: write candidate silently, emit only required `🔶`/`⚠ 5b.5` lines plus the anti-halt blockquote, then continue to Step 5c. Add a negative harness assertion that Step 5b.5 prose does not invoke `python/cli.py mermaid sanitize` before Step 5c.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:9,19,28,36
- **Concern**: [SCOPE-REDUCTION] The optional pre-check preserves an unnecessary command that can produce one of the exact unwanted harness lines. Scenario: Step 5c already performs authoritative sanitization, so running this optional probe adds no required behavior and may still render a shell-command count that the issue asks to suppress as much as feasible
- **Proposed resolution**: Remove the optional pre-check permission and its related command-specific prompt and test requirements; proceed directly from candidate authoring to the required Step 5c continuation

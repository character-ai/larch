### FINDING_2: Read-only pre-check may mutate the authoritative candidate
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: The edge-case text permits the optional read-only pre-check to revise the candidate, contradicting the pre-check’s non-mutating contract and allowing a non-authoritative probe to alter Step 5c’s input or Step 5c-owned artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite the edge case: the pre-check never modifies the candidate or any Step 5c-owned artifact; on failure it is ignored and Step 5c remains authoritative. If re-authoring is allowed, say only the orchestrator may silently rewrite the candidate once with no sanitizer narration, still without writing sentinels, promoted/skipped files, or warnings.
  - From Codex-Pragmatic: Replace “It may revise the candidate” with an explicit statement that the pre-check must not revise or otherwise mutate the candidate


### FINDING_3: Global execution-issues exception may reauthorize Step 5b.5 sanitizer warnings
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The global execution-issues exception still pairs diagram generation with sanitizer rejection at Step 5b.5, which can be read as authorizing sanitizer-rejection warnings and bounded execution-issues writes that the quiet pre-check contract intends to reserve for Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow line 111 to generation failures only, or add an explicit Step 5b.5 carve-out that sanitizer-rejection logging is Step 5c publish-owned only. Pin the narrowed wording in test-design-structure.sh so prompt edits cannot resurrect pre-check warning authority.


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:Approach;skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Optional Step 5b.5 sanitizer pre-check adds complexity without clearing the issue's minimum-change bar. Scenario: The binding scope targets Claude-authored narration in the Step 5b.5 diagram sequence. The issue transcript also shows harness-visible `Ran N shell commands` and failed ad-hoc sanitize invocations. Step 5c already owns authoritative sanitize/promote/skip via `python/larch/design/design_publish.py::_sanitize_diagram_candidate`. A silent pre-check still adds orchestrator Bash surface, preserves uncontrollable harness noise, and reopens wrong-flag probing without changing publish behavior.
- **Proposed resolution**: Drop the optional pre-check from SKILL.md, finalize-step5.md, and structural tests. Require: write candidate silently, emit only required `🔶`/`⚠ 5b.5` lines plus the anti-halt blockquote, then continue to Step 5c. Add a negative harness assertion that Step 5b.5 prose does not invoke `python/cli.py mermaid sanitize` before Step 5c.



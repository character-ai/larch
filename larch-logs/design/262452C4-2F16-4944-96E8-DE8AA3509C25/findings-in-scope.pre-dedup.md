### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:Approach;skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Optional Step 5b.5 sanitizer pre-check adds complexity without clearing the issue's minimum-change bar. Scenario: The binding scope targets Claude-authored narration in the Step 5b.5 diagram sequence. The issue transcript also shows harness-visible `Ran N shell commands` and failed ad-hoc sanitize invocations. Step 5c already owns authoritative sanitize/promote/skip via `python/larch/design/design_publish.py::_sanitize_diagram_candidate`. A silent pre-check still adds orchestrator Bash surface, preserves uncontrollable harness noise, and reopens wrong-flag probing without changing publish behavior.
- **Proposed resolution**: Drop the optional pre-check from SKILL.md, finalize-step5.md, and structural tests. Require: write candidate silently, emit only required `🔶`/`⚠ 5b.5` lines plus the anti-halt blockquote, then continue to Step 5c. Add a negative harness assertion that Step 5b.5 prose does not invoke `python/cli.py mermaid sanitize` before Step 5c.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh;skills/design/SKILL.md:593
- **Concern**: Anti-halt blockquote pinning may truncate the existing Step 5b.5 continuation guard. Scenario: The plan pins preservation of only `> **Continue to Step 5c IMMEDIATELY.` Current SKILL.md keeps a longer required blockquote: `> **Continue to Step 5c IMMEDIATELY** after the skip marker exists or the candidate write/failure-log path is complete.` A literal `contains` on the short form can push implementers to replace the longer guard while trying to reject free-form Step 5c checklist recaps, weakening when continuation is mandatory.
- **Proposed resolution**: Pin the full existing blockquote (or require `contains` of both the anti-halt prefix and `after the skip marker exists or the candidate write/failure-log path is complete`). Reject free-form recaps with separate `not_contains` examples from the issue anchor, not by shortening the normative anti-halt text.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:edge-cases
- **Concern**: Edge-case text contradicts the read-only pre-check contract. Scenario: The plan defines the optional pre-check as a silent read-only probe against the candidate in place, but the edge-case bullet says it may revise the candidate. An implementer can treat a failed pre-check as license to mutate the candidate, narrate a fix loop, or skip straight to Step 5c with a sentinel already satisfied if other forbidden writes occur.
- **Proposed resolution**: Rewrite the edge case: the pre-check never modifies the candidate or any Step 5c-owned artifact; on failure it is ignored and Step 5c remains authoritative. If re-authoring is allowed, say only the orchestrator may silently rewrite the candidate once with no sanitizer narration, still without writing sentinels, promoted/skipped files, or warnings.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:111
- **Concern**: Global execution-issues exception still authorizes Step 5b.5 sanitizer-rejection warnings. Scenario: The planned Step 5b.5 quiet contract forbids pre-check sanitizer narration and `**⚠ 5b.5:` warnings, but SKILL.md line 111 still pairs diagram generation with sanitizer rejection at site design Step 5b.5. That stale global rule can justify reintroducing the demonstrated pre-Step-5c sanitizer chat warnings and bounded execution-issues writes during Step 5b.5 orchestration.
- **Proposed resolution**: Narrow line 111 to generation failures only, or add an explicit Step 5b.5 carve-out that sanitizer-rejection logging is Step 5c publish-owned only. Pin the narrowed wording in test-design-structure.sh so prompt edits cannot resurrect pre-check warning authority.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:591-593
- **Concern**: Step 5b.5 anti-halt blockquote still lacks an explicit forbidden-recap carve-out. Scenario: The issue transcript shows halt-prone free-form Step 5c checklists paraphrasing the required anti-halt blockquote. The plan pins preserving `> **Continue to Step 5c IMMEDIATELY.**` but does not require adjacent text forbidding checklist-style transition recaps that duplicate Step 5c duties.
- **Proposed resolution**: At the Step 5b.5 anti-halt blockquote, add one sentence: after candidate write or generation-failure logging, emit only the required blockquote and continue; do not print Step 5c compose/validate/publish checklists or validity recaps. Pin that sentence in test-design-structure.sh.



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:46
- **Concern**: Accepted immutability fix remains incomplete because the edge case permits the pre-check to revise the candidate. Scenario: The implementer may follow this explicit permission and rewrite `architecture-diagram.candidate.md`, contradicting the read-only contract at lines 9, 19-21, and 28-30 and letting a non-authoritative probe alter Step 5c's input
- **Proposed resolution**: Replace “It may revise the candidate” with an explicit statement that the pre-check must not revise or otherwise mutate the candidate



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:9,19,28,36
- **Concern**: [SCOPE-REDUCTION] The optional pre-check preserves an unnecessary command that can produce one of the exact unwanted harness lines. Scenario: Step 5c already performs authoritative sanitization, so running this optional probe adds no required behavior and may still render a shell-command count that the issue asks to suppress as much as feasible
- **Proposed resolution**: Remove the optional pre-check permission and its related command-specific prompt and test requirements; proceed directly from candidate authoring to the required Step 5c continuation




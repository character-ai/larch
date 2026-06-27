### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:209-211
- **Concern**: Positive grep misses the retained judge-grammar sections. Scenario: The retained-core check can still pass if `skills/shared/dialectic-protocol.md` loses `Judge Output Format` or `Parser tolerance`, even though the clarifier still depends on those rules to parse `THESIS`/`ANTI_THESIS` lines. That leaves the active contract incomplete while the split appears valid.
- **Proposed resolution**: Add a positive grep for `Judge Output Format` and `Parser tolerance` in `skills/shared/dialectic-protocol.md`, or otherwise pin those section headers explicitly.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-legacy.md
- **Concern**: [ALREADY_ADDRESSED] Legacy-file validation still title-marker-only after the round-3 grep expansion.. Scenario: The expanded positive grep at plan.txt:215 checks section-title strings and disposition tokens, not moved bodies. An implementer can retain headings like Launching Judges or Consumer Contract while dropping argv fences, Per-side waterfall steps, resolutions field rules, or Step 3.5 criteria; make lint still passes.
- **Proposed resolution**: Pin substantive legacy preservation greps (for example run-external-agent, Judge Prompt Template, Dialectic-Local Presence Check, resolutions field-name list, Step 3.5 still-contested criterion bullets) or a byte-count floor for the parked block.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:213-215
- **Concern**: [ALREADY_ADDRESSED] Legacy-file positive grep still does not prove all moved dialectic sections were preserved (FINDING_5 fix incomplete).. Scenario: Round 3 expanded legacy greps, but the positive list still omits moved section markers such as Judge Prompt Template and Dialectic-Local Presence Check. An implementer can drop those parked blocks, keep title-only hits like Launching Judges, and still pass validation while losing audit content the plan requires moved verbatim.
- **Proposed resolution**: Add Judge Prompt Template, Dialectic-Local Presence Check, and Collecting Judge Results (split pattern) to the dialectic-legacy.md positive grep set (or one anchored block-presence check per removed active section).

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:231-241
- **Concern**: [ALREADY_ADDRESSED] Step-prefix split lacks fail-closed grep banning the three encoding token literals in progress-reporting.md (FINDING_8 fix incomplete).. Scenario: The plan requires rewriting Breadcrumb Format and Step Start Formatting without STEP_NUM_PREFIX, STEP_PATH_PREFIX, or PARENT_SKILL_PATH, and failure mode 188 warns against a whole-file ban conflict, but testing only greps for removed ## --step-prefix Encoding headings plus a manual verify bullet. A partial edit can leave line-15 STEP_PATH_PREFIX prose, pass make lint, and fail the split goal.
- **Proposed resolution**: Add an explicit negative grep: rg -n 'STEP_NUM_PREFIX|STEP_PATH_PREFIX|PARENT_SKILL_PATH' skills/shared/progress-reporting.md && exit 1 || true

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:61-103
- **Concern**: Active dialectic negative greps omit inline legacy judge tokens in kept Ballot Format and Threshold Rules subsections.. Scenario: Section-title greps catch Launching Judges and collect-results, but kept-subsection residue such as 3-panel, judge_codex_available, judge_cursor_available, Code Reviewer subagent, run-external-agent, and subagent_type can remain in ballot/judge prose after partial trims (current file lines 68, 141, 153). CI passes while Gate C clarifier readers still load external-judge choreography the plan targets for removal.
- **Proposed resolution**: Extend the second active-file negative grep to include 3-panel, judge_codex_available, judge_cursor_available, Code Reviewer subagent, run-external-agent, and subagent_type; keep clarifier-safe judge vote-line grammar.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/progress-reporting.md:15
- **Concern**: Testing lacks an automated post-split ban on the three encoding token literals in progress-reporting.md.. Scenario: The plan rewrites Breadcrumb Format and failure mode 188 warns against a whole-file token ban, but Testing strategy only manual-verifies line 241. An implementer can leave STEP_PATH_PREFIX on line 15, still pass make lint, and miss the ~52-line standalone read savings.
- **Proposed resolution**: Add a scoped negative grep: rg -n "STEP_NUM_PREFIX|STEP_PATH_PREFIX|PARENT_SKILL_PATH" skills/shared/progress-reporting.md must exit non-zero after the encoding section move.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:17-21
- **Concern**: Active validation has no positive grep for clarifier Caller Binding paths while only forbidding $DIALECTIC_TMPDIR.. Scenario: Negative greps ban $DIALECTIC_TMPDIR and external judge output stems, but positive greps do not require $DESIGN_TMPDIR/dialectic-ballot.txt or python/design_dialectic.py ballot assembly. Caller Binding can stay on $DIALECTIC_TMPDIR placeholders while section-title greps pass, contradicting clarifier-only framing and design_dialectic.py.
- **Proposed resolution**: Add a positive grep requiring $DESIGN_TMPDIR/dialectic-ballot.txt (and optionally design_dialectic.py ballot assembly) in the active dialectic-protocol.md file.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:213-215
- **Concern**: Legacy-file preservation check is too sparse to guarantee a complete move. Scenario: The OR-style grep can still pass if `dialectic-legacy.md` only mentions a few markers like `Consumer Contract` or `Disposition Enum` while omitting whole parked sections such as `Caller Binding`, `Overview`, or `Collecting Judge Results`, leaving the audit reference incomplete.
- **Proposed resolution**: Validate each moved retired section or heading explicitly in `dialectic-legacy.md` instead of relying on a few keyword matches.

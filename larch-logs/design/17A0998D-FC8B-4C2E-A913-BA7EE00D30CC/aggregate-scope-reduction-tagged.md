### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/dialectic-legacy.md:75-79
- **Concern**: [SCOPE-REDUCTION] Legacy-file positive greps still omit several mandated parked section titles from the remove list.. Scenario: Round 3 expanded the legacy grep, but the Testing strategy block at plan.txt:213-215 still does not require `Overview (Legacy Step 2a.5 Debater Flow)`, `Dialectic-Local Presence Check`, `Judge Prompt Template`, or legacy `Scope and Precedence` binding prose. An implementer can drop those moved blocks, keep the shorter title hits that remain in the grep, and still pass validation while failing the plan's audit-archive contract.
- **Proposed resolution**: Extend the legacy positive grep (or add a small harness assertion) to require every section title listed in the plan's dialectic-legacy move list, not only the shorter subset already in the Testing strategy block.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:197-205
- **Concern**: [SCOPE-REDUCTION] Active dialectic negative greps omit `Per-side waterfall` / `debater waterfall` markers beyond isolated tokens.. Scenario: The remove list parks `Per-side waterfall retry`, and failure mode #3 warns about partial kept-subsection trims, but the active negative greps never match the section title or generic `per-side waterfall` / `debater waterfall` prose. An implementer can delete only `dialectic-execution`, `debate-<n>`, and six-tag lines while leaving the debater retry narrative under a retitled heading; greps pass while Gate C readers still load retired choreography.
- **Proposed resolution**: Add `Per-side waterfall|per-side waterfall|debater waterfall|render debate-retry` to the active `dialectic-protocol.md` negative grep set (or explicitly require deleting the entire `## Per-side waterfall retry` block in the Files section).

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md:114-118
- **Concern**: [SCOPE-REDUCTION] Voter argv removal boundary starts at line 120, leaving the ## Launching Voters header and dispatcher intro.. Scenario: The plan replaces lines ~120-183 with an ownership note but does not remove ## Launching Voters (114-118). Those four lines repeat plan-review voter-dispatch and agent dispatch-voters ownership already stated in ## Voter Panel Composition (59-75) and again in the replacement note (~91-96). A literal edit ships ~5 lines of dead scaffolding and blunts the ~50-line voting read reduction.
- **Proposed resolution**: Extend the contiguous removal/replace span to 114-183 (drop the whole ## Launching Voters section) or explicitly list the header plus its two dispatcher paragraphs in the remove set; add a negative grep for ## Launching Voters in skills/shared/voting-protocol.md.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/dialectic-protocol.md
- **Concern**: [SCOPE-REDUCTION] Active dialectic negative greps omit external-judge launch residue tokens.. Scenario: Round-3 greps added path placeholders and collect-results, but partial trims can still leave Launching Judges argv prose (run-external-agent, launch-codex-exec, subagent_type, judge_codex_available, judge_cursor_available) in kept subsections while section-title greps pass. Gate C clarifier uses Claude subprocess judges only; that residue reloads retired external-judge choreography on the always-loaded path.
- **Proposed resolution**: Add these literals to the second active-file negative grep: run-external-agent, launch-codex-exec, subagent_type, judge_codex_available, judge_cursor_available, and Dialectic-Local Presence.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/shared/voting-protocol.md:114-118
- **Concern**: [SCOPE-REDUCTION] Launching Voters preamble kept outside the 120-183 deletion window duplicates the replacement ownership note.. Scenario: The plan deletes argv fences and interstitials at 120-183 and inserts a compact dispatcher-ownership note there, but leaves the preceding ## Launching Voters paragraphs that already state plan-review voter-dispatch and agent dispatch-voters ownership. Post-edit readers still load ~5 redundant lines and the issue's ~50-line voting read reduction is partially lost.
- **Proposed resolution**: Extend the removal/replace span to cover 114-183 (drop the ## Launching Voters header and preamble) so one ownership note is the sole dispatch prose; or explicitly instruct merging 114-118 into the replacement block.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/voting-protocol.md:114-118
- **Concern**: [SCOPE-REDUCTION] Plan replaces lines ~120-183 but leaves the Launching Voters preamble that duplicates the new ownership note.. Scenario: The contiguous delete starts at Generic Cursor voter argv; the existing /design and /implement dispatcher paragraphs above it repeat the same python/cli.py plan-review voter-dispatch and agent dispatch-voters ownership the replacement block must state. A literal implementation keeps ~5 lines of duplicate dispatcher prose and blunts the ~50-line voting read reduction.
- **Proposed resolution**: Instruct one merged Launching Voters section: delete lines ~114-183 as a single block and replace with one compact ownership note (no separate preamble plus second note).

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/dialectic-legacy.md:215
- **Concern**: [SCOPE-REDUCTION] Prior legacy preservation grep expansion is still incomplete versus the move list.. Scenario: The positive grep at plan line 215 omits moved sections such as Overview, Judge Prompt Template, Dialectic-Local Presence Check, and debater quorum / six-tag prose. An implementer can drop those parked blocks while section-title hits like Launching Judges remain, and make lint still passes.
- **Proposed resolution**: Extend the legacy-file positive grep to require those moved section markers (for example Overview, Judge Prompt Template, Dialectic-Local Presence Check, debater quorum / six-tag checklist) or an equivalent block-presence check tied to every item in the move list.

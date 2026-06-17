### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agent_voters.py:397-404
- **Concern**: The plan replaces slot 1 with cursor-validity on the Cursor path but never explicitly removes today's unconditional _launch_claude_voter call before dispatch-waterfall.. Scenario: An implementer can keep the existing Claude voter launch and add three Cursor archetype rows, producing four judges and writing Claude votes into v1 while v1_tool expects cursor-validity.
- **Proposed resolution**: Branch dispatch_voters: when --cursor-available true launch only the three-row waterfall (no _launch_claude_voter); call _launch_claude_voter only on the --cursor-available false fallback path.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:592
- **Concern**: The plan updates step-5-review.sh banner text but not the Step 5 IMPORTANT paragraph that still tells operators the banner uses Claude+Codex+Cursor.. Scenario: step-5-review.sh can ship with archetype wording while SKILL.md still documents the retired voter trio for /implement Step 5.
- **Proposed resolution**: Add an explicit ### UPDATED: skills/implement/SKILL.md item to replace the ~line 592 voter parenthetical with three Cursor archetype voters plus single-Claude fallback while preserving the 3-judge panel on every round anchor.

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/review-core.sh:1098-1117
- **Concern**: Normal dispatch still compacts surviving voter paths and only passes --voter-files when the compacted array is non-empty. Scenario: On the new panel, a failed middle slot drops that path; slot-3 votes shift into v2_* columns and vN_tool attribution corrupts. When all three Cursor voters fail, tally may receive no --voter-files at all and skip the three-slot contract instead of reaching main-agent-required with fixed slot placeholders
- **Proposed resolution**: Replace compaction with fixed-length voter_files[0..2] and voter_tools[0..2]; always append --voter-files (3 entries) and --voter-tools (3 labels) on the normal dispatch path, using empty paths plus canonical archetype labels for failed/skipped slots

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/tally-code-votes.sh:421-448
- **Concern**: Three-slot fixed-slot iteration is specified for the ballot loop but not for the preamble quorum math or 0-judge early exit. Scenario: With three argv entries where two are empty placeholders, ELIGIBLE_VOTERS=${#VOTER_FILES[@]} stays 3 and triggers 2-of-3 thresholds when only one judge voted; the 0-judge branch still calls write_classification_tsv_row without vN_tool/body_severity while the header is 22 columns
- **Proposed resolution**: Apply the same tiered three-slot path to preamble counting (substantive readable slots only) and to 0-judge placeholder rows; keep the legacy 18-column path only when --voter-tools is omitted and length is 1

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agent_voters.py:397-428
- **Concern**: Cursor-available path still implied to reuse today’s parallel Claude launch plus tool-name waterfall mapping. Scenario: Launching Claude alongside three Cursor rows reintroduces a fourth judge and cost; mapping ALL_OUTPUT_* by tool=cursor overwrites earlier slots so multiple Cursor outputs collapse into voter_3_path
- **Proposed resolution**: When --cursor-available true, launch only the three-row Cursor manifest (no _launch_claude_voter); bind voter_1/2/3 paths from manifest slot order or fixed output paths, not tool==codex/cursor branches

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:466-477
- **Concern**: Parse-rate retry prompt wiring not updated for archetype-specific voter prompts. Scenario: After the panel change, slot-2/3 retries would still pass legacy codex/cursor prompt files without --archetype lens blocks, so retries diverge from first-pass archetype voting
- **Proposed resolution**: Store three rendered prompt paths (validity, plan-fidelity, pragmatism) and pass the matching file into _run_parse_rate_retry for each slot; Claude fallback keeps the no-archetype prompt for slot 1 only

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py:657-710
- **Concern**: parse-rate retry launch only accepts voter_tool in {claude,codex,cursor}. Scenario: cursor-validity labels passed verbatim hit launch_voter_retry unknown-tool exit 2, silently degrading that slot via NOT_SUBSTANTIVE
- **Proposed resolution**: Normalize cursor-* to cursor inside parse_rate_retry_main (or launch_voter_retry) before launch; keep the archetype label only in diagnostics and vN_tool cells

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/legacy_review_shell/tally-code-votes.sh:32-52
- **Concern**: Planned tiered validation drops the existing multi-voter --voter-files contract. Scenario: Existing callers can pass two or three --voter-files without --voter-tools today. The plan rejects those as ambiguous, which is a breaking CLI and harness regression not required for the new review-core path.
- **Proposed resolution**: Use the fixed three-slot path only when --voter-tools is supplied. Preserve current compacted legacy semantics for omitted --voter-tools with one to three voter files.

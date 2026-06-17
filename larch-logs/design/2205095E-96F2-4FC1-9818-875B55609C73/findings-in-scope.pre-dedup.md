### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rendering.py:render_voter_main
- **Concern**: Plan-fidelity archetype has no no-plan-context behavior for code-review voters. Scenario: /review --diff (and other paths where dispatch-code-voters.sh omits --plan-file) still launch plan-fidelity-completeness with lens text centered on implementation-plan traceability; without bounded plan context the judge may default NO on legitimate in-scope findings or mis-route real-but-OOS items, shifting 2-of-3 outcomes versus the incumbent generic voters
- **Proposed resolution**: When --verification-context code and no plan context file is staged, inject explicit fallback text: judge plan-fidelity against the diff and ballot scope only; treat missing plan as absence of a formal plan anchor, not automatic NO

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/legacy_review_shell/tally-code-votes.sh:430-536
- **Concern**: Parse-rate compaction must pair labels with files before the voting loop. Scenario: The plan adds EFFECTIVE_VOTER_LABELS compaction but the main tally loop still builds classification_cells from EFFECTIVE_VOTER_FILES only; if write_classification_tsv_row is extended to six cells per slot without zipping compacted labels by index, vN_tool can disagree with the vote ratings in the same row
- **Proposed resolution**: If --voter-labels is present, parse it into VOTER_LABELS aligned with VOTER_FILES, compact both arrays in the existing parse-rate loop, and zip EFFECTIVE_VOTER_LABELS[i] when appending each five rating cells before calling write_classification_tsv_row

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/dispatch-code-voters.sh:44-58
- **Concern**: python/agent_waterfall.py:254-255. Scenario: Claude-floor path must use agent launch-claude-review not dispatch-waterfall
- **Proposed resolution**: agent dispatch-waterfall rejects manifest tool values outside codex/cursor so a single-Claude voter cannot ride the waterfall NDJSON path; routing Cursor-unavailable fallback through waterfall exits 2 or never launches On --cursor-available false keep launch-claude-review for VOTER_1_PATH with the existing .done wait and local sentinel synthesis; reserve dispatch-waterfall for the three cursor archetype slots only

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/legacy_review_shell/review-core.sh:1091-1110
- **Concern**: review-core.sh builds voter_files but never passes matching --voter-labels to tally. Scenario: After 21-column TSV adds vN_tool a middle-slot failure compacts voter_files to two paths while labels stay cursor-validity/cursor-pragmatism; without parallel label arrays v2_tool mis-names the surviving slot
- **Proposed resolution**: Build voter_labels under the same status/path guards as voter_files and pass --voter-labels to tally-code-votes.sh in identical order (plan already states this; ensure no caller skips it)

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-code-voters.sh:381-382
- **Concern**: python/audit_runs.py:548. Scenario: DISPATCH_OK=false when zero archetype judges survive is unspecified
- **Proposed resolution**: Plan sets DISPATCH_OK=true when at least one Cursor archetype survives but does not define the all-three-failed case; waterfall --no-fallback can still emit DISPATCH_OK=true while effective_judges=0 leaving audit DISPATCH_OK=false heuristics inconsistent After status re-evaluation on the 3-Cursor path set DISPATCH_OK=false when effective_judges=0; keep DISPATCH_OK=true for partial 1/3 or 2/3 survival

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py:687-709
- **Concern**: python/legacy_review_shell/tally-code-votes.sh:430-437. Scenario: parse-rate retry for cursor-* archetype labels is required before cutover
- **Proposed resolution**: launch_voter_retry and parse_rate_check_tool_label only accept bare codex/cursor today; dispatch will pass cursor-validity etc so parse-rate retries fail closed and compacted EFFECTIVE_VOTER_LABELS never align with retried slots Implement the planned cursor-* prefix mapping in voting.py and add the cited pytest coverage before enabling archetype dispatch

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/voting-protocol.md:116-177
- **Concern**: Launching Voters prose still describes legacy code-review voter dispatch after the planned partial rewrite. Scenario: The plan updates Overview and the code-review composition blurb but leaves adjacent sections that still say code review launches Claude plus Codex/Cursor, Codex uses VOTER_2 skipped, Cursor uses VOTER_3 skipped, Claude dispatch lives in dispatch-code-voters.sh, and wait-reviewers examples use codex/cursor-vote-output paths. Those blocks sit immediately under the section being rewritten and will contradict the new 3-Cursor-archetype plus single-Claude-floor model.
- **Proposed resolution**: Operators and later edits will follow stale launch/wait contracts; harnesses or debug copy-paste can reintroduce Codex voters or mis-order sentinels after the cutover. Extend the voting-protocol.md update to cover the full code-review Launching Voters surface: remove or re-scope the generic Codex voter block for /review, replace the Cursor availability note (no more VOTER_3-only skip), replace the Claude-in-dispatch note on the normal path, and update the wait-reviewers sentinel example to the three predetermined cursor-* output paths (or dispatch-waterfall manifest) plus the Claude-floor fallback.

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-code-voters.sh:115-299
- **Concern**: Plan retires #3704 but is silent on removing Claude-only wait/sentinel machinery (`launch-claude-review` background, `voter1_pid`/`voter1_rc`, synthetic `VOTER_1_PATH.done` publish, `TIMEOUT 1` handling) on the normal 3-Cursor path.. Scenario: On Cursor-available runs the dispatcher could still launch or wait on a Claude voter while also running a 3-slot Cursor waterfall, mis-binding `VOTER_1_*`, corrupting sentinel arbitration, and breaking the intended all-Cursor panel.
- **Proposed resolution**: Explicitly delete the Claude parallel lane and its post-wait reap/synthetic-.done block for `--cursor-available true`; build `wait_sentinels`, status classification, and parse-rate retry only from the three predetermined `cursor-*-vote-output.txt` paths (keep the Claude-floor subset only when `--cursor-available false`).

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: README.md:89, docs/review-agents.md:102, docs/skills.md:99
- **Concern**: Public Step 5 docs are omitted from the plan. Scenario: The PR can land with canonical consumer docs still promising Claude plus Codex plus Cursor voters and shrink-not-backfill, contradicting the new 3-Cursor voter panel
- **Proposed resolution**: Add these docs to the plan and update the Step 5 voter wording while preserving the required 3-judge panel on every round anchor

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md:116-169
- **Concern**: The voting-protocol update is too narrow. Scenario: The plan rewrites overview and composition prose but can leave the Launching Voters and Cursor/Codex availability sections telling code review to launch Claude, Codex, and Cursor voters
- **Proposed resolution**: Update all code-review voter launch and availability paragraphs in voting-protocol.md so normal code review is three Cursor archetype voters, Cursor-unavailable fallback is one Claude voter, and Codex is design-only for voter availability examples


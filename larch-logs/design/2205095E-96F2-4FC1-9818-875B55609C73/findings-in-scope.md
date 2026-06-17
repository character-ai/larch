### FINDING_1: Plan-fidelity voter lacks no-plan-context fallback for code review
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan-fidelity archetype has no behavior when no implementation plan is staged. On `/review --diff` and other paths where `dispatch-code-voters.sh` omits `--plan-file`, `plan-fidelity-completeness` still judges against implementation-plan traceability. Without bounded plan context, the judge may default NO on legitimate in-scope findings or mis-route real-but-OOS items, shifting 2-of-3 outcomes versus incumbent generic voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When --verification-context code and no plan context file is staged, inject explicit fallback text: judge plan-fidelity against the diff and ballot scope only; treat missing plan as absence of a formal plan anchor, not automatic NO

### FINDING_2: Archetype voter labels must stay aligned through parse-rate compaction and tally
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned 21-column TSV `vN_tool` column and parse-rate compaction require parallel label and file arrays end-to-end. Today `review-core.sh` builds `voter_files` but does not pass matching `--voter-labels`; `tally-code-votes.sh` compacts `EFFECTIVE_VOTER_FILES` without zipping compacted labels into classification cells; and `voting.py` parse-rate retry only accepts bare `codex`/`cursor`, so `cursor-*` archetype labels fail closed before cutover. Any mismatch leaves `vN_tool` disagreeing with vote ratings for the surviving slot after middle-slot failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: If --voter-labels is present, parse it into VOTER_LABELS aligned with VOTER_FILES, compact both arrays in the existing parse-rate loop, and zip EFFECTIVE_VOTER_LABELS[i] when appending each five rating cells before calling write_classification_tsv_row
  - From Cursor-Innovation: Build voter_labels under the same status/path guards as voter_files and pass --voter-labels to tally-code-votes.sh in identical order (plan already states this; ensure no caller skips it)
  - From Cursor-Innovation: launch_voter_retry and parse_rate_check_tool_label only accept bare codex/cursor today; dispatch will pass cursor-validity etc so parse-rate retries fail closed and compacted EFFECTIVE_VOTER_LABELS never align with retried slots Implement the planned cursor-* prefix mapping in voting.py and add the cited pytest coverage before enabling archetype dispatch

### FINDING_3: Claude-floor fallback must use launch-claude-review, not dispatch-waterfall
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: On the Cursor-unavailable path, routing the single Claude voter through `agent dispatch-waterfall` is invalid: `dispatch-waterfall` rejects manifest tool values outside `codex`/`cursor`, so a single-Claude voter cannot use the waterfall NDJSON path and either exits 2 or never launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: agent dispatch-waterfall rejects manifest tool values outside codex/cursor so a single-Claude voter cannot ride the waterfall NDJSON path; routing Cursor-unavailable fallback through waterfall exits 2 or never launches On --cursor-available false keep launch-claude-review for VOTER_1_PATH with the existing .done wait and local sentinel synthesis; reserve dispatch-waterfall for the three cursor archetype slots only

### FINDING_4: DISPATCH_OK must be false when zero archetype judges survive
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan defines `DISPATCH_OK=true` when at least one Cursor archetype survives but is silent on the all-three-failed case. With waterfall `--no-fallback`, dispatch can still emit `DISPATCH_OK=true` while `effective_judges=0`, leaving audit `DISPATCH_OK=false` heuristics inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan sets DISPATCH_OK=true when at least one Cursor archetype survives but does not define the all-three-failed case; waterfall --no-fallback can still emit DISPATCH_OK=true while effective_judges=0 leaving audit DISPATCH_OK=false heuristics inconsistent After status re-evaluation on the 3-Cursor path set DISPATCH_OK=false when effective_judges=0; keep DISPATCH_OK=true for partial 1/3 or 2/3 survival

### FINDING_5: voting-protocol.md code-review voter launch prose is incomplete and stale
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The planned `voting-protocol.md` update rewrites Overview and the code-review composition blurb but leaves adjacent Launching Voters, availability, and wait-reviewers sections describing the legacy Claude + Codex + Cursor model (`VOTER_2`/`VOTER_3` skips, Claude-in-dispatch, `codex`/`cursor-vote-output` paths). That contradicts the new 3-Cursor-archetype plus single-Claude-floor model and can mislead operators, harnesses, and later edits after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Operators and later edits will follow stale launch/wait contracts; harnesses or debug copy-paste can reintroduce Codex voters or mis-order sentinels after the cutover. Extend the voting-protocol.md update to cover the full code-review Launching Voters surface: remove or re-scope the generic Codex voter block for /review, replace the Cursor availability note (no more VOTER_3-only skip), replace the Claude-in-dispatch note on the normal path, and update the wait-reviewers sentinel example to the three predetermined cursor-* output paths (or dispatch-waterfall manifest) plus the Claude-floor fallback.
  - From Codex-Generic: Update all code-review voter launch and availability paragraphs in voting-protocol.md so normal code review is three Cursor archetype voters, Cursor-unavailable fallback is one Claude voter, and Codex is design-only for voter availability examples

### FINDING_6: Normal 3-Cursor path must not retain Claude parallel voter machinery
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan retires #3704 but is silent on removing Claude-only wait/sentinel machinery (`launch-claude-review` background, `voter1_pid`/`voter1_rc`, synthetic `VOTER_1_PATH.done` publish, `TIMEOUT 1` handling) on the normal `--cursor-available true` path. The dispatcher could still launch or wait on a Claude voter while also running a 3-slot Cursor waterfall, mis-binding `VOTER_1_*`, corrupting sentinel arbitration, and breaking the intended all-Cursor panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Explicitly delete the Claude parallel lane and its post-wait reap/synthetic-.done block for `--cursor-available true`; build `wait_sentinels`, status classification, and parse-rate retry only from the three predetermined `cursor-*-vote-output.txt` paths (keep the Claude-floor subset only when `--cursor-available false`).

### FINDING_7: Public Step 5 voter docs omitted from plan
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Canonical consumer docs (`README.md`, `docs/review-agents.md`, `docs/skills.md`) still promise Claude plus Codex plus Cursor voters and shrink-not-backfill for Step 5. The plan does not include them, so the PR can land with public docs contradicting the new 3-Cursor voter panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add these docs to the plan and update the Step 5 voter wording while preserving the required 3-judge panel on every round anchor

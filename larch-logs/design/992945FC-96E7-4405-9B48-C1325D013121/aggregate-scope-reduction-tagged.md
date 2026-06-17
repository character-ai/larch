### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_voters.py:388-447
- **Concern**: [SCOPE-REDUCTION] Cursor-available path must not keep the legacy Claude slot-1 launch/wait alongside a three-row Cursor waterfall. Scenario: Implementing three Cursor manifest rows without deleting `_launch_claude_voter` and `claude_process.wait()` can launch four judges or block on a Claude `.done` sentinel that was never created
- **Proposed resolution**: Branch `dispatch_voters`: when `--cursor-available true`, launch only the three-row `code-voter-slots.ndjson` via `_dispatch_waterfall --no-fallback`; bind slots 1–3 from fixed output paths; skip Claude entirely on this path

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/legacy_review_shell/tally-code-votes.sh:163-283
- **Concern**: [SCOPE-REDUCTION] Planned 22-column code-review TSV adds body_severity and renames reviewer_slots beyond the required voter identity change. Scenario: The issue requires per-voter identity labels. Adding body_severity extraction and switching code-review attribution to finding_reviewers expands the log schema and can break consumers of code-review reviewer_slots without being needed for the Cursor voter cutover.
- **Proposed resolution**: Keep the code-review schema change minimal: retain reviewer_slots, add only v1_tool/v2_tool/v3_tool on the explicit three-slot path, and make readers tolerate 18-column legacy plus the minimal new tool-column schema.

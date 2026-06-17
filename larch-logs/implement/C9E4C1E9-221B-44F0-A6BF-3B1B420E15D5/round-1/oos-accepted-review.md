### OOS_1: [OUT_OF_SCOPE] `agent_voters.py` binds fixed per-slot output paths from `CURSOR_VOTER_SLOTS`, skips Claude on the Cursor-available path, keeps `--no-fallback`, and emits archetype `VOTER_N_TOOL` labels.
- `agent_voters.py` binds fixed per-slot output paths from `CURSOR_VOTER_SLOTS`, skips Claude on the Cursor-available path, keeps `--no-fallback`, and emits archetype `VOTER_N_TOOL` labels.


### OOS_2: [OUT_OF_SCOPE] `review-core.sh` always passes three `--voter-files` and three `--voter-tools` entries (empty path plus canonical label for failed/skipped slots).
- `review-core.sh` always passes three `--voter-files` and three `--voter-tools` entries (empty path plus canonical label for failed/skipped slots).


### OOS_3: [OUT_OF_SCOPE] `tally-code-votes.sh` uses fixed slot iteration, substantive-slot quorum counting, 21-column `code-review-classification-header`, and preserves `vN_tool` on empty slots.
- `tally-code-votes.sh` uses fixed slot iteration, substantive-slot quorum counting, 21-column `code-review-classification-header`, and preserves `vN_tool` on empty slots. **Other notes**


### OOS_4: [OUT_OF_SCOPE] `test_agent_voters.py::test_failed_middle_cursor_slot_degrades_without_backfill` covers dispatch-side no-Codex-backfill behavior.
- `test_agent_voters.py::test_failed_middle_cursor_slot_degrades_without_backfill` covers dispatch-side no-Codex-backfill behavior.


### OOS_5: [OUT_OF_SCOPE] MAV and zero-findings paths still omit `--voter-tools`, so they stay on the legacy 18-column compacted path as intended.
- MAV and zero-findings paths still omit `--voter-tools`, so they stay on the legacy 18-column compacted path as intended.


### OOS_6: [OUT_OF_SCOPE] `skills/fluff-analysis/scripts/fluff-analysis.py` now reads ratings by header name, which should tolerate the new 21-column schema when `vN_tool` columns are present.
- `skills/fluff-analysis/scripts/fluff-analysis.py` now reads ratings by header name, which should tolerate the new 21-column schema when `vN_tool` columns are present.


### OOS_7: [OUT_OF_SCOPE] **Cursor unavailable, Codex available:** Voter quorum drops from the legacy 2-judge (Claude + Codex) tier to 1-judge (Claude only). The branch implements the settled plan decision; not a dispatch bug.
- **Cursor unavailable, Codex available:** Voter quorum drops from the legacy 2-judge (Claude + Codex) tier to 1-judge (Claude only). The branch implements the settled plan decision; not a dispatch bug.


### OOS_8: [OUT_OF_SCOPE] **Core wiring looks correct:** `dispatch_voters` branches cleanly on `--cursor-available`; `_dispatch_waterfall` keeps `--no-fallback`; `review-core.sh` always passes three canonical `--voter-files` / `--voter-tools` pairs; `tally-code-votes.sh` counts only substantive non-empty slots on the three-slot path. `test_tally_three_slot_claude_fallback_single_quorum` covers the Claude-fallback quorum path.
- **Core wiring looks correct:** `dispatch_voters` branches cleanly on `--cursor-available`; `_dispatch_waterfall` keeps `--no-fallback`; `review-core.sh` always passes three canonical `--voter-files` / `--voter-tools` pairs; `tally-code-votes.sh` counts only substantive non-empty slots on the three-slot path. `test_tally_three_slot_claude_fallback_single_quorum` covers the Claude-fallback quorum path.


### OOS_9: [OUT_OF_SCOPE] **`review-core.sh` ignores `DISPATCH_OK`:** All voters failing still flows to tally and `main-agent-vote-required`. That matches the plan’s MAV path and is not a regression.
- **`review-core.sh` ignores `DISPATCH_OK`:** All voters failing still flows to tally and `main-agent-vote-required`. That matches the plan’s MAV path and is not a regression.


### OOS_10: [OUT_OF_SCOPE] **`voter_launcher_tool` normalization** exists, but `launch_voter_retry` was removed earlier (#4547); parse-rate retry is diagnostic-only today. Not introduced by this branch’s fallback work.
- **`voter_launcher_tool` normalization** exists, but `launch_voter_retry` was removed earlier (#4547); parse-rate retry is diagnostic-only today. Not introduced by this branch’s fallback work.



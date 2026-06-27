### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **risk-integration** `python/test_plan_review_panel.py` — The plan called for end-to-end `dispatch_voters` coverage (consumer `--log-root`, per-tool output paths, `prompt_files` manifest rows, snapshot-failure paths, `no_fallback=True`). Round 2 added resolver/waterfall/render/replay unit tests, but plan-review dispatch integration is still thin (only `_fresh_calibration_stats_file` kill-switch). **Suggested fix:** Extend the existing `dispatch_voters` harness to assert snapshot argv, render `--voter-tool` / `--calibration-stats-file`, and manifest `prompt_files` entries.
- **Suggested revision**: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **architecture** `python/voting.py:518-553` — `_voter_calibration_run_dir` and `_voter_calibration_run_started_at` duplicate `analyze_issues._ground_truth_run_dir` / `_ground_truth_run_started_at` (round-1 FINDING_4). Live prompt feedback and `/voter-calibration` reports can drift if one copy changes. **Suggested fix:** Share one helper module or import the analyze_issues functions.
- **Suggested revision**: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **code-quality** `python/test_agent_voters.py:897-903` — Manifest assertions still check slot/tool shape only, not `prompt_files` per base tool (plan-listed). Waterfall relaunch behavior is covered in `test_agent_waterfall.py`, but code-review dispatch wiring lacks a direct manifest contract test. **Suggested fix:** Parse `code-voter-slots.ndjson` and assert non-empty `prompt_files` maps with expected tool keys.
- **Suggested revision**: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/voting.py:518-524` — `_voter_calibration_run_dir` and `_voter_calibration_run_started_at` remain duplicated copies of `analyze_issues._ground_truth_run_dir` / `_ground_truth_run_started_at` rather than a shared helper. Future ground-truth fixes will not automatically flow into live voter prompt-feedback snapshotting.
- **Suggested revision**: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/test_plan_review_panel.py:428-432` — Plan-mandated `dispatch_voters` integration coverage is still thin versus the plan (consumer `--log-root` wiring, per-tool output paths, `prompt_files` manifest assertions, snapshot-failure / stale-file paths). `/implement` and resolver unit tests improved in round 2; plan-review dispatch wiring has less direct harness protection.
- **Suggested revision**: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/voting.py:579-584` — Run directories without readable manifest timestamps all sort as `datetime.min` and can crowd out timestamped runs inside the same window. This matches the prior rejected FINDING_5 behavior and may skew calibration feedback on mixed corpora. **Prior-round status (brief):** FINDING_1 (phase-3 synthetic outputs), FINDING_8 (implement vs review keepalive precedence), and replay feedback disable look fixed with tests. FINDING_2 remains incomplete on the design-only path described above. FINDING_3 is partially addressed but plan-review dispatch integration coverage is still sparse.
- **Suggested revision**: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **architecture** `python/voting.py:518-524` and `python/analyze_issues.py:1839-1845` — `_voter_calibration_run_dir` duplicates `_ground_truth_run_dir`; future ground-truth fixes will not automatically apply to live prompt-feedback windowing (prior FINDING_4 rejected).
- **Suggested revision**: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **risk-integration** `python/test_plan_review_panel.py:413-425` and `python/test_agent_voters.py` — Plan-required harness coverage for `prompt_files` manifest rows, per-tool render paths, and `no_fallback=True` vs `False` enumeration is still thin in production dispatch tests despite unit tests in `test_agent_waterfall.py` and `test_voting.py` (prior FINDING_3 partially addressed).
- **Suggested revision**: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **code-quality** `python/plan_review_panel.py:899-913` — `_launchable_base_tools_for_slot(..., no_fallback=True)` is called and its return value discarded; manifest `prompt_maps_by_slot` is hand-authored instead. Safe today, but enumeration and manifest authoring can drift silently if waterfall policy changes. **Round-1 accepted fixes verified:** Phase-3 `prompt-missing` no longer synthesizes Claude outputs (`test_phase3_prompt_missing_records_drop_not_synthetic_output`). Implement-session keepalive precedence over nested review keepalive is fixed (`test_resolve_voter_calibration_log_root_prefers_implement_over_review_keepalive`). Phase-2 per-tool prompt selection works (`test_waterfall_per_tool_prompt_files_phase2_uses_cursor_prompt`). Replay disables feedback (`test_calibration_replay`). **Commits (4 since `origin/main`):** `0ee75955a` Wire voter calibration prompt feedback; `74be75b02` larch-logs flush; `f526e8edb` cyclic import fix; `79f923927` Address code review feedback (round 1).
- **Suggested revision**: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **code-quality** `python/plan_review_panel.py:899-913` — `dispatch_voters` calls `_launchable_base_tools_for_slot(..., no_fallback=True)` but discards the result; manifest `prompt_files` are hardcoded and not filtered by launchable tools. Behavior matches today’s hardcoded maps, but the call is misleading dead weight for future edits. **Branch context:** 4 commits since `origin/main`; round-1 fixes for phase-3 `prompt-missing` synthetic outputs (`agent_waterfall.py:1087-1117`, `test_agent_waterfall.py:1528-1556`) and implement-before-review keepalive precedence (`voting.py:798-804`, `test_voting.py:1666-1680`) look complete. Rendering/snapshot isolation (`rendering.py:1132-1168`, `voting.py:718-724`) correctly gates on `--voter-tool`, rejects symlinks, omits `body_severity`, and keeps prompts byte-stable without `--voter-tool`.
- **Suggested revision**: Address the concern above.


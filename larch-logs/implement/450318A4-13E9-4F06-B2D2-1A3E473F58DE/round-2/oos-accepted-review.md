### OOS_1: correctness: python/test_agent_voters.py:897-903
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Code-review tests do not assert voter 2/3 manifest rows contain prompt_files maps. Regression to legacy prompt_file-only manifest would still pass tests while waterfall relaunch uses wrong or missing per-tool prompts. Parse code-voter-slots.ndjson and assert prompt_files keys match launchable base tools for each slot.
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/agent_waterfall.py:1103-1164
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Phase-3 failures still get synthetic final outputs and then bypass drop recording. A crashed or collector-failed phase-3 Claude fallback can vanish from the dropped-slots report while ALL_OUTPUT_FILES points at a path that never produced a valid vote. Leave final_outputs empty for phase-3 failures, or record a separate failure marker and teach drop/path emission to preserve failed slots without pretending they succeeded.
- **Suggested revision**: Address the concern above.


### OOS_3: **code-quality** `python/test_plan_review_panel.py:413-432` — Plan-mandated `dispatch_voters` integration coverage is still largely missing. Round 2 added only `test_fresh_calibration_stats_file_returns_none_when_feedback_disabled`. The existing `dispatch_voters` harness does not assert snapshot invocation, consumer `--log-root` resolution, per-tool output paths (`codex-plan-voter-prompt-codex.txt`, etc.), `prompt_files` manifest rows, `no_fallback=True` enumeration, snapshot-failure / stale-file behavior, or render `--calibration-stats-file` / `--voter-tool` wiring. **Suggested fix:** Extend the harness near line 413 per the plan checklist, including a plugin-cwd + consumer `larch-logs` integration case with `LARCH_CONSUMER_REPO` or `CLAUDE_PROJECT_DIR`.
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **code-quality** `python/test_plan_review_panel.py:413-432` — Plan-mandated `dispatch_voters` integration coverage is still largely missing. Round 2 added only `test_fresh_calibration_stats_file_returns_none_when_feedback_disabled`. The existing `dispatch_voters` harness does not assert snapshot invocation, consumer `--log-root` resolution, per-tool output paths (`codex-plan-voter-prompt-codex.txt`, etc.), `prompt_files` manifest rows, `no_fallback=True` enumeration, snapshot-failure / stale-file behavior, or render `--calibration-stats-file` / `--voter-tool` wiring. **Suggested fix:** Extend the harness near line 413 per the plan checklist, including a plugin-cwd + consumer `larch-logs` integration case with `LARCH_CONSUMER_REPO` or `CLAUDE_PROJECT_DIR`.
- **Suggested revision**: Address the concern above.


### OOS_4: **code-quality** `python/test_agent_voters.py:93-97` — `test_agent_voters` still does not validate the new dispatch contract. No test asserts `prompt_files` in `code-voter-slots.ndjson`, codex-absent cursor fallback calibration (`--voter-tool cursor` + stats on the launched prompt), waterfall relaunch per-tool prompt selection, snapshot delete-before-write, or `--calibration-stats-file` on `render voter` calls. The default harness stub writes a malformed snapshot (`tool\tyes_votes`) so happy-path tests never exercise end-to-end calibration injection even though production may pass a stats path. **Suggested fix:** Add the plan’s codex-absent / `prompt_files` / waterfall-relaunch cases; make the snapshot stub emit a valid `read_voter_calibration_stats` TSV; assert render argv includes `--calibration-stats-file` and the matching `--voter-tool` when feedback is enabled.
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **code-quality** `python/test_agent_voters.py:93-97` — `test_agent_voters` still does not validate the new dispatch contract. No test asserts `prompt_files` in `code-voter-slots.ndjson`, codex-absent cursor fallback calibration (`--voter-tool cursor` + stats on the launched prompt), waterfall relaunch per-tool prompt selection, snapshot delete-before-write, or `--calibration-stats-file` on `render voter` calls. The default harness stub writes a malformed snapshot (`tool\tyes_votes`) so happy-path tests never exercise end-to-end calibration injection even though production may pass a stats path. **Suggested fix:** Add the plan’s codex-absent / `prompt_files` / waterfall-relaunch cases; make the snapshot stub emit a valid `read_voter_calibration_stats` TSV; assert render argv includes `--calibration-stats-file` and the matching `--voter-tool` when feedback is enabled.
- **Suggested revision**: Address the concern above.



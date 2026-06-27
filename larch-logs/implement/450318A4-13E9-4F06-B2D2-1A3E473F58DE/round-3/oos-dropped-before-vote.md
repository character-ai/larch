### OOS_1: [OUT_OF_SCOPE] risk-integration: python/test_agent_voters.py:1498-1527
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Dispatch tests use malformed snapshot TSV stubs. Harness passes while render voter never injects calibration because stats lack valid_yes_severity_count rows. Write valid snapshot fixtures in harness or assert calibration prose in rendered prompt files.
- **Suggested revision**: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] architecture: python/larch/state/session_env.py:45-60
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan documents REPO_CWD anchor but implement write-env never persists it. Operators reading the plan may expect session-env REPO_CWD; runtime depends on keepalive CLONE_PATH instead. Add REPO_CWD to implement session write path or update plan/docs to name keepalive as the sole filesystem anchor.
- **Suggested revision**: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] correctness: python/agent_waterfall.py:1103-1134
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] phase3_launch_failed still adds synthetic outputs to ALL_OUTPUT_FILES. Failed Claude phase-3 fallbacks may appear as launched paths without valid votes, confusing downstream collectors. Align phase3_launch_failed with phase3_missing_prompt drop semantics or record explicit failure markers.
- **Suggested revision**: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **risk-integration** `python/test_agent_voters.py:94-98` and `python/test_plan_review_panel.py:450-453` — Dispatch harness stubs still write malformed snapshot TSV (`tool\tyes_votes` only). Tests assert `--calibration-stats-file` is passed but not that calibration prose is injected, so CI can pass while the incentive path never renders feedback in harness runs.
- **Suggested revision**: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/agent_waterfall.py:1103-1117` — `phase3_missing_prompt` no longer gets synthetic outputs (improvement), but `phase3_launch_failed` still writes a phase-3 output path and sets `dispatch_ok = False` without a corresponding drop record. Failed Claude fallbacks may still appear in `ALL_OUTPUT_FILES` without valid votes.
- **Suggested revision**: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-calibration-corpus-output.txt
- **Concern**: - **correctness** `python/agent_voters.py:388` — Waterfall manifest rows always emit `prompt_files`, including `{}` when a slot map is missing. `_parse_prompt_files_map()` rejects empty maps and can abort the whole waterfall if availability/render ever yields an empty per-slot map.
- **Suggested revision**: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **correctness** `python/agent_waterfall.py:1103-1110` — Phase-3 launch failures still synthesize `final_outputs`/`final_tools` for failed Claude fallbacks while `phase3_missing_prompt` paths correctly avoid launch. A crashed phase-3 slot can disappear from dropped-slot reporting while `ALL_OUTPUT_FILES` still references a synthetic path. Pre-existing waterfall behavior; still worth fixing separately.
- **Suggested revision**: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **risk-integration** `python/test_agent_voters.py:94-97` — Default harness snapshot stub and plan-review calibration harness stubs still write malformed TSV (`tool\tyes_votes` only). Tests prove flag wiring, not that the incentive block reaches voter prompts when real stats exist. Consider a shared fixture with a full calibration snapshot header and an assertion on `**Your recent calibration:**` in rendered prompt files.
- **Suggested revision**: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-dyn-waterfall-prompts-output.txt
- **Concern**: - **architecture** `python/plan_review_panel.py:899-913` — `_launchable_base_tools_for_slot(..., no_fallback=True)` is called but its return value is discarded; plan-review per-tool renders are hardcoded instead of driven by enumeration. Harmless today because maps match policy, but the dead call can drift from manifest contents without test failure.
- **Suggested revision**: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **code-quality** `python/test_agent_voters.py:94-98`, `python/test_plan_review_panel.py:450-455` — Dispatch harnesses still stub `render voter` with canned stdout and write malformed snapshot TSV (`tool\tyes_votes`). Tests verify argv wiring and manifest shape, not that valid snapshot data produces calibration prose in the prompt files voters actually read. End-to-end prompt-feedback validation remains thin.
- **Suggested revision**: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-prompt-feedback-output.txt
- **Concern**: - **risk-integration** `skills/voter-calibration/scripts/voter-calibration.py` — The plan’s `MAY_UPDATE` note was not applied. The report still reads as diagnostic-only, which is now misleading because live dispatch can inject recent calibration into voter prompts (without changing weighting, spawning, or verdict computation).
- **Suggested revision**: Address the concern above.


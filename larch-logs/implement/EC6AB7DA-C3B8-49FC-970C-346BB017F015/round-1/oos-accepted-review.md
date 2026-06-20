### OOS_1: correctness: python/design_lifecycle.py:1357-1362
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] step_final_summary_main returns 0 when .completed/step-final-summary exists regardless of core rc A retry after a prior successful run leaves the sentinel; a broken render returns rc=1 but main exits 0 without fresh LARCH_FINAL_SUMMARY markers, so the orchestrator treats the task as success Only return 0 from the sentinel branch when rc==0, or remove the sentinel at the start of each run before rendering
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/design_lifecycle.py:149-180
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _bg_wait_marker_context does not remove pre-existing .bg-wait-active when marker setup fails A stale marker from a crashed run survives setup OSError; hook-bg-poll-guard keeps denying probes after final-summary has finished On setup failure attempt safe cleanup of a pre-existing marker file, or unlink before atomic replace
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/design_lifecycle.py:1357-1361
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] step_final_summary_main treats a stale .completed/step-final-summary sentinel as success after a non-zero core result A rerun in the same DESIGN_TMPDIR can fail to render, emit no fresh final-summary markers, and still exit 0 because a previous run left the sentinel behind Clear the sentinel before starting render, or track whether this invocation created it and only return 0 for a freshly written sentinel
- **Suggested revision**: Address the concern above.


### OOS_4: **risk-integration** `python/design_lifecycle.py:1343-1362` — `step_final_summary_main` can report success when the current run failed. After `step_final_summary_core` returns a non-zero `rc` (for example `render_rc == 1` from an exception in `render_final_summary_main`), the wrapper still returns `0` whenever `.completed/step-final-summary` already exists from an earlier attempt in the same `$DESIGN_TMPDIR`. The background Bash fence and `hook-bg-poll-guard.sh` both treat process exit code and that sentinel as completion signals; masking a fresh failure as exit `0` can make the orchestrator skip failure handling, emit a stale summary, or advance cleanup while render actually failed. **Suggested fix:** Only normalize to exit `0` when this invocation wrote the sentinel (for example atomically touch a run-scoped sentinel, or record a completion token in a sidecar and require it in `step_final_summary_main`). If a pre-existing sentinel is found without a matching current-run marker, remove it before work starts or return the real non-zero `rc`.
- **Reviewer**: dyn-final-summary-output.txt
- **Concern**: - **risk-integration** `python/design_lifecycle.py:1343-1362` — `step_final_summary_main` can report success when the current run failed. After `step_final_summary_core` returns a non-zero `rc` (for example `render_rc == 1` from an exception in `render_final_summary_main`), the wrapper still returns `0` whenever `.completed/step-final-summary` already exists from an earlier attempt in the same `$DESIGN_TMPDIR`. The background Bash fence and `hook-bg-poll-guard.sh` both treat process exit code and that sentinel as completion signals; masking a fresh failure as exit `0` can make the orchestrator skip failure handling, emit a stale summary, or advance cleanup while render actually failed. **Suggested fix:** Only normalize to exit `0` when this invocation wrote the sentinel (for example atomically touch a run-scoped sentinel, or record a completion token in a sidecar and require it in `step_final_summary_main`). If a pre-existing sentinel is found without a matching current-run marker, remove it before work starts or return the real non-zero `rc`.
- **Suggested revision**: Address the concern above.



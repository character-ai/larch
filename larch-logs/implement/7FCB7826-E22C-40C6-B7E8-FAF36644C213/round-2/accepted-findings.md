### FINDING_13: Publish harness stub exports leak between cases
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: important
- **Concern**: `test-design-publish.sh` does not reset stub exports between cases that call `bash "$SUBJECT"` directly or via `run_publish`. After **PUBLISH_OK=false** or **unexpected publish**, `PUBLISH_OK_VALUE`, `PUBLISH_STUB_RC`, `PUBLISH_EMIT_OK`, etc. remain exported; later cases (e.g. clear-architecture, upsert failure) inherit polluted state and exercise the wrong publish path while still passing narrow assertions. Only `PLAN_BLOCK_RC` is cleared after the plan-write-failure case; `run_publish` uses `${PUBLISH_STUB_RC:-0}` so prior non-default exports persist across `run_publish` calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-harness-isolation-output.txt: Add a `reset_publish_stub_env()` (or per-case `unset`/`export` block) before every direct `bash "$SUBJECT"` and at the start of `run_publish`, clearing `PLAN_BLOCK_RC`, `PUBLISH_STUB_RC`, `PUBLISH_EMIT_OK`, `PUBLISH_OK_VALUE`, `UPSERT_STUB_RC`, `UPSERT_STATUS_VALUE`, `ARCH_SOURCE_VALUE`, `RENAME_STUB_RC`, and `RENAMED_OMIT_LINE`, then set only what the case needs.
  - From dyn-test-harness-isolation-output.txt: Either call the same reset helper at the top of `run_publish` before applying defaults, or use explicit assignments (`export PUBLISH_STUB_RC=0`) instead of `:-` so each invocation gets a known baseline unless the case overrides.


### FINDING_3: Structural tests omit `${REPO:+--repo}` pin on `design-publish.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `${REPO:+--repo}` forwarding on `design-publish.sh` is not pinned in `scripts/test-design-structure.sh` (lines 1032–1058). `REPO` forwarding on upsert/publish/rename/render could be removed without CI failure, so forked or non-default-repo design runs could target the wrong GitHub repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `grep -Fq '${REPO:+--repo' "$DESIGN_PUBLISH_SH"` (or per-helper pins) alongside existing (15b) driver checks.


### FINDING_4: Marker-before-publish ordering under-tested (structure + unit harness)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-harness-isolation-output.txt
- **Severity**: important
- **Concern**: Reentry marker must precede `design-log-publish.sh` (not only tracking-issue rename). Static check 25 in `test-design-structure.sh` pins marker before `[DESIGNED]` rename but not before publish; `test-design-publish.sh` happy-path checks only `plan-block-write` → upsert → publish in `CALL_LOG` and does not log or assert `design_reentry_marker_write` before publish/rename. A regression that runs publish/rename before the marker could pass happy-path unit tests (and partial structure pins) while breaking session-cache reentry guard during publish in live `/design` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Log marker stub calls in `CALL_LOG` and assert ordering vs publish/rename.
  - From cursor-specialist-testing-output.txt: Add `publish_marker_line < publish_log_line` line-order assertion on `design-publish.sh`.
  - From cursor-specialist-testing-output.txt: Add source line-order `marker before design-log-publish` in `test-design-structure.sh` or runtime ordering in `test-design-publish.sh`.
  - From cursor-specialist-edge-cases-output.txt: Assert marker invocation between `plan-block-write` and `design-log-publish` in `CALL_LOG`.
  - From cursor-specialist-plan-fidelity-output.txt: Stub or log marker write in the happy-path case and assert marker precedes `design-log-publish` and `tracking-issue-write` in the ordered trace.
  - From dyn-test-harness-isolation-output.txt: After `run_publish`, assert reentry marker file exists (e.g. `$HOME/.cache/larch/sessions/design-completed-42-9999` for `--issue 42 --claude-pid 9999`) and mtime is not after the first `design-log-publish` entry in `PUBLISH_LOG` / `CALL_LOG`, or add a thin test-only wrapper that logs marker invocation before publish.


### FINDING_5: Driver exit 1 conflates plan-block-write failure with result-env write failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-euo-safety-output.txt
- **Severity**: important
- **Concern**: On the plan-block-write failure path, `write_result_env_and_emit` only calls `emit_kv` after `phase_driver_write_result_env` succeeds (`design-publish.sh` 146–155). If the atomic result-env write fails, the driver exits `1` without writing `.design-publish-result.env` and without emitting `PLAN_WRITE_OK=false` on stdout, while the orchestrator still treats exit `1` as the normal plan-write failure path (`SKILL.md` 1356–1362). Plan may already be on GitHub; operator may see no preserve banner, Step 5c may be skipped, and Step 6 cleanup gating may not match the “plan published, preserve tmpdir” contract. Sibling `design-init-runparams.sh` emits machine lines before `phase_driver_write_result_env` on failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use a distinct exit code or write result env earlier with an explicit orchestrator branch.
  - From cursor-specialist-edge-cases-output.txt: Reserve exit `1` for plan-write only; use distinct exit for contract/tail failures or ERR-trap partial result env; extend harness for result-env and source failures.
  - From dyn-bash-euo-safety-output.txt: On the failure branch, emit `PLAN_WRITE_OK=false` and `FINAL_SUMMARY_PATH` (and any `WARN=` lines) to stdout before calling `phase_driver_write_result_env`, or split `write_result_env_and_emit` so contract-critical `emit_kv` calls precede the write the way Step 0b drivers do; keep `exit 1` after both when plan-block-write failed.



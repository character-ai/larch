# Review Round 5

- Mode: `diff`
- 6 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_11: Missing runtime tests for main-agent escalation recording
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required runtime tests for main-agent escalation recording are missing from `test-design-step3-review.sh`. `main-agent-vote`/`apply` and `postplan-operator-required` ledger rows or phase mapping could regress without CI failure; only `tally-error` is exercised at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Call step3_record_report_evidence for each main-agent status and assert ledger trigger/phase; add a remap-vs-status guard case.


### FINDING_13: Final summary block omits report-gate sidecar chat handoff
- **Reviewer(s)**: dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: The Final summary block in `skills/design/SKILL.md` directs the orchestrator to emit only `final-summary.md` after background `design-step-final-summary.sh`. It does not require emitting `design-failure-operator-action-chat.md` or `design-failure-chat-print.md`. Those sidecars are written by `design-failure-report.sh` and printed by `render-final-summary.sh` via `print_report_gate_sidecars`, but the background fence output is discarded. Cancelled and single-phase terminal-failure exits therefore satisfy run-log audit without the guaranteed chat-visible operator-action / fallback-print path the plan requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: Mirror Step 5c’s `REPORT_GATE_SIDECARS_FILE` contract in `design-step-final-summary.sh` (aggregate sidecars to a handoff file and emit a KV), and extend the Final summary block orchestrator prose to require verbatim emission of that handoff immediately after `final-summary.md`.


### FINDING_14: abort_failed_publish_tail exits before report-gate sidecar handoff
- **Reviewer(s)**: dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: `abort_failed_publish_tail` in `design-step5c.sh` calls `render-final-summary.sh --post-publish-only` for `failed-publish-tail`, then `exit 1` before `emit_report_gate_sidecars_from_disk`. SKILL.md directs the orchestrator to stop immediately and skip Step 5c items 5–7, so there is no `REPORT_GATE_SIDECARS_FILE` handoff on this path. Terminal state staging and the report gate still run, but operator-action skips and fallback-print sidecars remain on disk only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: Call `emit_report_gate_sidecars_from_disk` (or equivalent) inside `abort_failed_publish_tail` before exit, and add a SKILL.md instruction to emit `REPORT_GATE_SIDECARS_FILE` on publish-tail hard abort the same way as the `_publish_rc` 0/1/3 path.


### FINDING_15: design-step3-review env-read failure bypasses escalation recording
- **Reviewer(s)**: dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: When `read-result-env.sh` fails, `design-step3-review.sh` synthesizes `LOOP_STATUS=panel-failed` without setting `STEP3_REVIEW_LOOP_STATUS` and without calling `step3_record_report_evidence`. If the orchestrator continues through Gate B bypass on a degraded panel, a later `approved` teardown can miss escalation-success filing. The loop records evidence only inside `step3_loop_emit_envelope`; this wrapper-level synthetic status bypasses that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: On env-read failure, set `STEP3_REVIEW_LOOP_STATUS=panel-failed` in the emitted KV stdout and invoke the same `record-escalation` path used in `review-design-step3-loop.sh` (or re-emit through a minimal envelope) before returning `LOOP_STATUS=panel-failed`.


### FINDING_2: postplan-failed staging helper aborts Step 3 driver under set -e
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `step3_stage_postplan_failed` in `review-design-step3-loop.sh` returns exit 1 when `STAGED=false`, while `run-step3-review.sh` uses `set -e`. A conflicting terminal state on postplan-failed aborts the Step 3 driver before `STEP3_REVIEW_LOOP_STATUS` and final-summary routing are emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Log the warning and continue envelope emission; do not return 1 from the staging helper.


### FINDING_3: Publish exit code 5 skips failed-publish-tail terminal staging
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` exit code 5 (runtime failures such as validator infrastructure errors and redaction failures) is treated as a setup abort in `design-step5c.sh`, skipping `design-stage-terminal-state.sh` and the failed-publish-tail summary/report path. Teardown then falls back to missing-terminal-state instead of filing a terminal report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Route exit 5 through the same publish-tail staging and summary path as other unexpected hard failures.
  - From codex-generic-output.txt: Either keep runtime publish-tail failures on rc `2`, or have the rc `5` branch distinguish setup validation from publish-tail hard failures and call `abort_failed_publish_tail`.



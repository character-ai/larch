## Goal
Implement issue #4104: [IMPLEMENTING] [OOS] Implement workflow test coverage & bootstrap harness — 5 items.

## Implementation Plan
## Plan

### Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Use the approved outline as binding scope.
- Keep the change small.
- Fix Step 5 timing with a **single-writer contract**:
  - Terminal lint-fix `main-agent-required` writes the timing row in-loop.
  - That same branch must not persist `round-start-s`.
  - Deferred `--record-only` remains the writer for true Step 5 prompt-side handoffs only.
- Add runtime coverage for:
  - Step 5 lint-fix main-agent stalls.
  - Ship-pr lint-fix main-agent handoff KVs.
  - Generated `larch-run.sh` dispatch, rejection, awk parity, and resume partial-upgrade behavior.

### UPDATED: skills/review-and-fix/scripts/review-implement-step5-loop.sh

- In the lint-fix `main-agent-required)` branch:
  - Keep `step5_surface_lint_stderr_tail` first.
  - Add `_emit_implement_round_timing_row "$round_num" "$round_start_s" "$(step5_now_s)" "${post_accepted_count:-0}" "${post_rejected_count:-0}"` before `step5_emit_final_envelope`.
  - Remove the `step5_persist_round_start "$round_num" "$round_start_s"` call from this branch.
- Keep `step5_persist_round_start` unchanged for:
  - `main-agent-vote-required`
  - `coder-main-agent-required`
- Keep `step5_emit_final_envelope` and `flush_review_batches` behavior unchanged.
- Do not change other lint-fix statuses.

### UPDATED: skills/review-and-fix/scripts/test-review-and-fix.sh

- Update the `lint-fix-terminal-tail` case.
- Keep existing assertions for:
  - Exit code `2`.
  - Stderr-tail surfacing before the final envelope.
  - Final envelope reason `lint-fix-main-agent-required`.
- Replace the defer-only assertions with the new contract:
  - `timing-ledger.tsv` exists after loop exit.
  - The ledger has exactly one Step 5 round row for round `1`.
  - The row uses the current round start and post-review accepted and rejected counts.
  - `round-1/round-start-s` is absent.
- Remove the manual `record-implement-review-round-timing.sh` simulation from this case.
- Add a guard that invoking `step-5-resume.sh --record-only` for the same round does not add a second row when no `round-start-s` file exists.
- Keep the existing defer-only expectations for non-terminal prompt-side handoffs.

### UPDATED: skills/review-and-fix/scripts/test-review-implement-step5-loop-timing.sh

- Keep existing helper tests for in-loop timing rows.
- Keep existing defer-only coverage for `coder-main-agent-required`.
- Add focused coverage for the lint-fix `main-agent-required` terminal branch:
  - The branch emits one in-loop timing row.
  - The branch does not persist `round-start-s`.
  - A subsequent record-only resume attempt does not create another row.
- Assert row count by `(kind=round, skill=implement, round=<N>, start_s=<S>)`, not by exact `end_s`.

### UPDATED: scripts/test-ship-pr-rebase.sh

- Replace the grep-only `SHIP_PR_LEDGER_*` assertion with a runtime sandbox.
- Source `scripts/ship-pr.sh` in a subshell so `main` does not run.
- Use a temp `IMPLEMENT_TMPDIR`, state file, and fake redacted logs.
- Override only narrow functions needed to avoid network, git pushes, and full ship-pr execution:
  - `run_lint_fix_loop_capture`
  - `failure_capture_path`
  - Any noisy stderr surfacing if needed.
- Drive the actual handoff path enough to exercise:
  - `run_captured_cmd_then_fix_loop`
  - `_rcc_handle_fix_status`
  - `rcc_main_agent_required_detail_log`
  - `emit_ship_pr_ledger_ready`
  - `exit_ship_pr_internal_lint_fix_handoff`
- Add two runtime cases:
  - **check-first:** captured command fails, lint-fix returns `LINT_FIX_STATUS=main-agent-required`, then the path exits `3`.
  - **dispatch-first:** prior redacted log exists, lint-fix returns `main-agent-required`, then the path exits `3`.
- Assert stdout contains:
  - `SHIP_PR_LEDGER_READY=true`
  - `SHIP_PR_LEDGER_SITE=ship-pr-internal`
  - `SHIP_PR_LEDGER_TRIGGER=ship-pr-internal-lint-fix`
  - `SHIP_PR_LEDGER_STEP=8`
  - `SHIP_PR_LEDGER_PHASE=<phase>`
  - `SHIP_PR_LEDGER_DISPATCHER=ship-pr`
  - `SHIP_PR_LEDGER_EXIT_CODE=3`
  - `SHIP_PR_LEDGER_FAILURE_DETAIL_LOG=<tmpdir path>`
- Assert the state file records:
  - `BAIL_REASON=ship-pr-internal-lint-fix`
  - `BAIL_FAILURE_DETAIL_LOG=<tmpdir path>`
  - `STALL_TRACKING=false`
  - `EXIT_CODE=3`
- Add fallback coverage where `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG` is missing.
- Assert the fallback detail log comes from the captured failure file or the initial redacted log.
- Assert detail logs outside `$IMPLEMENT_TMPDIR` are not exported as `SHIP_PR_LEDGER_FAILURE_DETAIL_LOG`.
- Keep existing static pins for other rebase behavior.

### UPDATED: scripts/test-implement-fence-shape.sh

- Keep the current Python static fence-shape checks.
- Add a launcher sandbox after the static block.
- Generate `larch-run.sh` in a temp dir by importing `python.bootstrap._write_larch_run_sh`.
- Use a fake plugin root under the temp dir with:
  - An executable `.sh` target that prints argv.
  - A `.py` target that prints argv and confirms Python execution.
  - An unsupported extension target for rejection coverage.
- Add launcher contract assertions:
  - `.sh` target passes argv through unchanged.
  - `.py` target runs through `python3`, not bare exec.
  - `.py` target passes argv through unchanged.
  - Absolute target paths exit `2`.
  - `../` traversal targets exit `2`.
  - Unsupported extensions exit `2`.
- Add awk fallback parity coverage:
  - Extract only the single-quoted awk program used to populate `LARCH_CLAUDE_PLUGIN_ROOT` from `skills/implement/scripts/step-0-bootstrap.sh`.
  - Extract the same awk program from generated `larch-run.sh`.
  - Assert the awk programs match exactly.
  - Do not compare surrounding guard predicates.
- Add partial-upgrade coverage through the bootstrap resume infra path:
  - Create a temp `IMPLEMENT_TMPDIR`.
  - Write `session-env.sh` with minimal session keys.
  - Write `plugin-root.env` before the test starts.
  - Ensure `larch-run.sh` is absent before the test starts.
  - Include `plan.txt` and `feature-description.txt` fixtures so the case remains compatible with full resume-tail execution.
  - Stub bootstrap `_run` and `_cli` calls to avoid branch, session, network, and reviewer side effects.
  - Invoke the resume bootstrap infra path with `resume_plan_tail=True`.
  - Assert `larch-run.sh` exists and is executable afterward.
- Use direct `_write_larch_run_sh` calls only for standalone launcher dispatch assertions.

### Edge cases

- `step-5-resume.sh --record-only` may still run after a terminal lint-fix stall. It must not add a second row for `lint-fix-main-agent-required`.
- `round-start-s` must remain present for true prompt-side Step 5 handoffs.
- `round-start-s` must not be created for the terminal lint-fix `main-agent-required` branch.
- `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG` may be missing. The ship-pr handoff test should cover fallback detail-log selection.
- Detail logs outside `$IMPLEMENT_TMPDIR` must not be exported as `SHIP_PR_LEDGER_FAILURE_DETAIL_LOG`.
- `larch-run.sh` must reject invalid paths before dispatch.
- The awk parity check should compare the awk program, not unrelated guard predicates.
- The partial-upgrade launcher test must exercise the bootstrap resume branch. A direct writer-only test is insufficient for that case.

### Failure modes

- A Step 5 timing row can double-count if the lint-fix terminal branch both emits in-loop and leaves `round-start-s` for deferred recording.
- A Step 5 lint stall can still miss timing if the timing call is placed after the final envelope or exit path.
- Step 5 tests will fail if defer-only assertions are left unchanged.
- Sourcing `ship-pr.sh` can accidentally run `main` if the test executes the script directly.
- The launcher test can become brittle if it asserts the host Python path exactly. Assert observable Python dispatch instead.
- The partial-upgrade test can miss the regression if it calls `_write_larch_run_sh` directly instead of the resume bootstrap infra path.
- The resume bootstrap path can fail before the launcher assertion if `session-env.sh`, `plan.txt`, or `feature-description.txt` fixtures are missing.

### Testing strategy

- Run focused Step 5 tests:
  - `bash skills/review-and-fix/scripts/test-review-and-fix.sh`
  - `bash skills/review-and-fix/scripts/test-review-implement-step5-loop-timing.sh`
- Run focused ship-pr and launcher tests:
  - `bash scripts/test-ship-pr-rebase.sh`
  - `bash scripts/test-implement-fence-shape.sh`
- Run the repository-recommended check:
  - `bash scripts/relevant-checks.sh`
- If relevant-checks cannot run cleanly locally, run and report:
  - `make lint`

## Acceptance

- Step 5 lint `main-agent-required` terminal branch emits a timing row to `timing-ledger.tsv` and does not persist `round-start-s`.
- A subsequent `step-5-resume.sh --record-only` for the same round does not add a second row.
- `test-review-and-fix.sh` and `test-review-implement-step5-loop-timing.sh` pass with updated assertions.
- `test-ship-pr-rebase.sh` passes with runtime execution of the ship-pr lint-fix handoff path and all `SHIP_PR_LEDGER_*` KV fields asserted.
- `test-implement-fence-shape.sh` passes with launcher dispatch, rejection, awk-parity, and partial-upgrade assertions.

diff_lines: 280

## Test plan
(no test plan section in plan-file)

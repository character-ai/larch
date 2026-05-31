# Review Round 3

- Mode: `diff`
- 16 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Dispatch-first missing post-fix log maps to dispatch-failed instead of exhausted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After an applied fix, when verification checks still fail and there is no usable post-fix raw log (missing, empty, or unredactable under allowed tmpdir), Python sets `loop.status` to `dispatch-failed` (TRANSIENT escalation) via `_redacted_log_for_dispatch` returning `None`. Bash treats missing `_RCC_RAW_LOG_PATH` as `exhausted` (STALLED). Phase 7 cutover would diverge operator recovery on the same fault; `dispatch-failed` should be reserved for redaction/write failures, not absent capture logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Align with ship-pr.sh: missing/empty capture log → exhausted; redaction failure → dispatch-failed; add dispatch-first unit test for ChecksResult with no usable log path.


### FINDING_10: No test for codex-fail then cursor-success when both tools present
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No stub test exercises ordered fallback when both Codex and Cursor are present. A refactor could break `checks.py` fallback without CI signal because codex-only failure paths never invoke Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub test with codex_present=True cursor_present=True; force _run_codex rc!=0 and _run_cursor rc==0; assert cursor dispatch argv and applied/coder_tool cursor.
  - From cursor-specialist-plan-fidelity-output.txt: Add stub test with both tools present: failing codex, succeeding cursor; assert two dispatches and cursor argv.


### FINDING_12: Generic failed fix outcomes → dispatch-failed not integration-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Mapping of generic failed fix outcomes to `dispatch-failed` in `run_check_fix_loop` is not integration-tested. A bug in `_handle_fix_outcome` else branch could mis-escalate structural failures while `escalate()` table tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add run_check_fix_loop test with fixer returning failed/forbidden-path-violation; assert loop.status dispatch-failed and escalate TRANSIENT.


### FINDING_13: max_iter upper bound (6) not exercised in run_check_fix_loop
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Wrong loop bound logic for values above default might only surface in ship-pr CI per-job paths using `RCC_MAX_ITER=6`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one exhausted loop test with max_iter=6 and six failing iterations.


### FINDING_14: run_checks_phase lacks Outcome.OK end-to-end test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No integration test expects `Outcome.OK` for skipped or passing relevant-checks stub; top-level wiring bugs in `validate_tmpdir`/skipped clean path could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add integration test expecting Outcome.OK for skipped or passing relevant-checks stub.


### FINDING_15: Non-executable run-external-agent.sh path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Only missing-file fail-closed path is tested; present but non-executable wrapper may regress if `is_file`/`X_OK` logic changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test with present but non-executable run-external-agent.sh asserting failed missing-run-external-agent parity.
  - From cursor-specialist-plan-fidelity-output.txt: Add stub test expecting failed / missing-run-external-agent for chmod -x script.


### FINDING_16: dispatch-first allows allowed_tmpdir=None — log confinement bypass
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_check_fix_loop` permits `allowed_tmpdir=None`, so dispatch-first and `_redacted_log_for_dispatch` skip session-root confinement. A caller can pass `initial_redacted_log` outside the session sandbox (including symlinked paths when confinement is omitted), unlike bash `IMPLEMENT_TMPDIR` / `resolve_checks_log_path` wiring; fixer may read and send sensitive content to external agents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require validate_tmpdir-backed allowed_tmpdir for any fixer dispatch; reject paths outside that root (parity with ship-pr.sh resolve_checks_log_path)
  - From cursor-specialist-edge-cases-output.txt: Require allowed_tmpdir for dispatch-first or always validate via _resolve_checks_log_path.
  - From cursor-specialist-plan-fidelity-output.txt: Require allowed_tmpdir for dispatch-first or always validate initial_redacted_log.


### FINDING_17: Unbounded full-file log reads despite prompt cap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Log tailing and redaction read entire files into memory despite a 60KB prompt cap. Multi-GB check output from a malicious consumer risks OOM of the implement runner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use bounded reads (tail-only) and/or cap subprocess capture before writing/reading logs


### FINDING_18: Checks log filesystem path in external-agent prompt without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Session paths under `~/.cache/larch/sessions/claude-implement-*` are included in Codex/Cursor prompts even when log body is redacted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply redact.redact() to the path line or omit filesystem paths from third-party prompts


### FINDING_2: run_checks_phase / fix-site semantics differ from live Step 6 bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_checks_phase` uses a single capture/fix site and `run_check_fix_loop` continues after no-changes per `run_captured_cmd_then_fix_loop`. Live `ship-pr.sh` Step 6 uses separate sites for capture vs `ship-pr-ci-initial` lint-fix and breaks on no-changes. Phase 7 cutover may change labels and loop behavior unless the API adds fix-site mapping, documents the Step 6 contract, and adds parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Cursor preflight bash missing SCRIPT_DIR for lib-cursor-launcher-common.sh
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cursor preflight sources `lib-cursor-launcher-common.sh` without setting `SCRIPT_DIR`, so `agent-model-args` and `cursor-auth` paths resolve incorrectly under a real `Runner`. Step 6 or CI per-job fix with `cursor_present=True` can fail every dispatch with `dispatch-failed`/`main-agent-required` despite a working Cursor install.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Set SCRIPT_DIR from dirname of the sourced lib (or pass scripts_dir) before cursor_launcher_* calls; use cwd=repo_root if auth needs the consumer repo.


### FINDING_22: Phase 4 plan file list vs branch diff mismatch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Phase 4 plan lists three `python/` files but the branch also changes `test-lint-literal-counts.sh`, `test-plan-review-loop.sh`, and `plugin.json`. Reviewers can miss bundled non-Phase-4 harness/plugin changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Split or explicitly document ancillary changes outside the Phase 4 file list.


### FINDING_4: Plan vs runtime on agents.classify_launch_failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan text calls for `agents.classify_launch_failure` / `is_transient_infra_failure` on dispatch failure, but `checks.py` does not import `agents` and behavior is fixed `main-agent-required` / `dispatch-failed` per `lint-fix-loop.sh` #3207. A maintainer following the plan could add classifiers at Phase 7 cutover and diverge from bash. Amend plan/acceptance to match bash, or add classification only if bash gains it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Amend plan/acceptance to match bash fixed main-agent-required/dispatch-failed, or add classification only if bash gains it.


### FINDING_5: _scripts_dir(repo_root) ignores repo_root
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_scripts_dir(repo_root)` ignores `repo_root`, which is misleading when wiring to consumer repos in Phase 7. Rename to `_plugin_scripts_dir()` and drop the unused parameter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: No test for dispatch-first exhausted when raw log missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: No stub test asserts `exhausted` after applied fix plus missing raw log on the dispatch-first path. A regression on FINDING_1 would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: _run_codex does not unlink codex.sidecar before dispatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Unlike `lint-fix-loop.sh`, Python does not remove `codex.sidecar` before run. A stale sidecar from a prior attempt may skew telemetry on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unlink codex.sidecar before dispatch alongside events and wrapper logs.
  - From cursor-specialist-plan-fidelity-output.txt: Unlink run_dir/codex.sidecar before dispatch like lint-fix-loop.sh:243.



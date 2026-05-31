# Review Round 2

- Mode: `diff`
- 12 accepted, 8 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: Health-class dispatch failures return `failed` instead of `main-agent-required`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: important
- **Concern**: When codex and/or cursor dispatch both fail, `run_lint_fix` branches on `agents.classify_launch_failure()` and returns `FixOutcome(status="failed", failure_reason="dispatch-failed")` if any attempt has `failure_class == "health"`. Bash `lint-fix-loop.sh` (#3207, lines 414–429) always emits `main-agent-required` with `FAILURE_REASON=dispatch-failed` for the same case. `_handle_fix_outcome` maps `failed` → loop status `dispatch-failed`, and `escalate()` maps that to `Outcome.TRANSIENT` instead of `Outcome.NEEDS_USER_INPUT`, so infra/auth/empty-output health-class failures take transient retry semantics instead of the main-agent / recovery-waterfall path used in production bash. `classify_launch_failure` on the all-failed dispatch path only feeds this erroneous branch; bash does not classify local dispatch failures for status selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the health branch; always return main-agent-required with failure_reason=dispatch-failed when both present tiers fail; add a unit test stubbing classify_launch_failure to health.
  - From cursor-specialist-correctness-output.txt: Remove health branch; always return main-agent-required with failure_reason=dispatch-failed when present tiers exhaust; test NEEDS_USER_INPUT.
  - From cursor-specialist-correctness-output.txt: Drop classification on all-failed dispatch or use only for logging; align FixOutcome with bash.
  - From cursor-specialist-testing-output.txt: Remove the health-only branch or emit main-agent-required; add a unit test with a health-classified stub failure asserting NEEDS_USER_INPUT end-to-end.
  - From cursor-specialist-edge-cases-output.txt: Always return main-agent-required with failure_reason=dispatch-failed when both tiers fail; use classify_launch_failure for logging only unless product explicitly wants health→TRANSIENT.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the health-only branch; always return main-agent-required with failure_reason=dispatch-failed when both present tiers fail
  - From dyn-parity-drift-output.txt: Remove the health-only branch and always return `FixOutcome(status="main-agent-required", failure_reason="dispatch-failed", …)` when `coder_tool is None` and at least one external was present, matching `lint-fix-loop.sh`; keep `classify_launch_failure` only for logging/tests if needed, not for status selection.


### FINDING_10: `target_cmd_display` embedded in prompts without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `target_cmd_display` is embedded unvalidated in backtick-delimited prompt text and `run_checks_phase` allows it for any site. A caller passing newlines or instruction-like text can manipulate the codex/cursor fixer prompt beyond what bash allows for non per-job sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Match bash: allow only for ship-pr-ci-per-job reject control characters and newlines before interpolation or load via target_cmd_display_from_file parity.


### FINDING_12: `ship-pr-ci-per-job` site lacks `target_cmd_display` fail-closed validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No validation that `ship-pr-ci-per-job` has `target_cmd_display`. A caller using that site without `target_cmd_display` gets `relevant-checks.sh` prompt text instead of the failing CI command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed when site is ship-pr-ci-per-job and target_cmd_display is absent.


### FINDING_13: `is_transient_infra_failure` unused; plan/acceptance mismatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `is_transient_infra_failure` is never called though the plan lists it alongside `classify_launch_failure`. Acceptance/plan mismatch unless the health branch is kept.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire is_transient_infra_failure per plan or remove unused classification on local-fix path.


### FINDING_14: Unreachable prefix membership check after basename-derived prefix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Redundant guard after basename-derived prefix is unreachable dead code only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove redundant guard.


### FINDING_17: Truncation banner hardcodes `60000` instead of `_PROMPT_TAIL_BYTES`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Changing the tail limit requires two edits; banner could lie if the constant changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Interpolate _PROMPT_TAIL_BYTES into the truncation message.


### FINDING_2: `_compose_prompt` omits submodule-prohibition parity from bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_compose_prompt` omits `emit_submodule_prohibition` parity from `lib-submodule-prohibition.sh` and shortens final-line contract text. Fixer prompts lack bulleted submodule guardrails and `.git`/`.gitmodules` prohibition present in bash `compose_prompt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Port emit_submodule_prohibition text verbatim into _compose_prompt or shell out to the existing bash helper.


### FINDING_5: Missing forbidden-path and dispatch regression tests required by plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan testing strategy and bash `test-lint-fix-loop.sh` case 1b require forbidden-path reversion + violation coverage; Python only tests `forbidden-path-reset-failed` today. Gaps include committed forbidden submodule delta after successful reset, working-tree forbidden-path violation, and (per structure reviewer) health-class dispatch and related scenarios—regressions in dispatch escalation or forbidden-path handling can ship without pytest signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add stubbed scenarios for health-class failure, .gitmodules working-tree revert, and committed forbidden delta per plan testing strategy.
  - From cursor-specialist-testing-output.txt: Add StubRunner test: dispatch moves HEAD, committed diff touches forbidden path, reset succeeds, assert failed and forbidden-path-violation.
  - From cursor-specialist-plan-fidelity-output.txt: Add stub-Runner test asserting failure_reason=forbidden-path-violation after forbidden delta is reverted


### FINDING_6: Cursor dispatch test lacks full `run-external-agent.sh` argv parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires cursor leaf argv parity with `lint-fix-loop.sh:290-296` (unlike codex, which has fuller assertions). Current cursor test checks wrap/cwd and partial argv only; wrapper flag regressions (`--capture-stdout`, timeout, tool routing) could ship while codex parity test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend cursor test to find run-external-agent.sh argv and assert --tool cursor, --timeout 1800, --capture-stdout, and leaf cursor agent shape per lint-fix-loop.sh:290-296.
  - From cursor-specialist-plan-fidelity-output.txt: Extend cursor test to assert full run-external-agent.sh wrapper argv and no launch-*-ci.sh


### FINDING_7: Missing `run_relevant_checks` edge-case tests from plan
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed `run_relevant_checks` edge cases (broken symlink, agent-lint-missing warn, post-check-only coverage) have no tests. Parser/coverage regressions for partial runs or missing agent-lint would not fail `py-test` until production logs mis-classify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add three focused tmp_path tests with canned log bodies and symlink fixture.


### FINDING_8: Check-first loop lacks inline redaction fallback when only `raw_log_path` is set
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: In `run_check_fix_loop` check-first branch, a failing `ChecksResult` with non-empty `raw_log_path` but `redacted_log_path=None` terminates with `dispatch-failed` without on-the-fly redaction. Bash `run_captured_cmd_then_fix_loop` (`ship-pr.sh:314-317`) always builds a `.redacted` file via `redact-secrets.sh`; Python dispatch-first branch already has fallback redaction (`checks.py:1317-1328`). Redaction `OSError` or a runner that only sets `raw_log_path` cannot enter the fix loop even though bash would; silent redaction changes could turn fixable failures into `dispatch-failed`/TRANSIENT without targeted signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub failing ChecksResult with raw_log_path set and redacted_log_path None; assert loop status dispatch-failed.
  - From cursor-specialist-plan-fidelity-output.txt: Mirror dispatch-first redaction fallback in check-first branch when raw_log_path exists
  - From dyn-parity-drift-output.txt: Mirror the dispatch-first fallback in the check-first path—when `redacted_log_path` is missing but `raw_log_path` is a non-empty file, write `Path(raw_path).with_suffix(suffix + ".redacted")` via `redact.redact()` (or reuse a small shared helper) and proceed to `fixer()`; only set `dispatch-failed` if that write fails.


### FINDING_9: `checks_log` path not confined to validated session tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` and the dispatch-first loop accept any readable `checks_log` path without confining it to the validated session tmpdir (unlike `ship-pr.sh` `resolve_checks_log_path`). At Phase 7 cutover a buggy or compromised caller could pass sensitive paths (e.g. `~/.ssh/id_rsa`); tail content is redacted but still fed to codex/cursor and may leak material redact patterns miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Port resolve_checks_log_path semantics: realpath the candidate require it under canonical_tmp from validate_tmpdir apply in run_lint_fix run_check_fix_loop for initial_redacted_log and fallback redacted writes.



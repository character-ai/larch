# Review Round 1

- Mode: `diff`
- 17 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_13: correctness: skills/design/scripts/file-design-oos.sh:14-16
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] file-design-oos builds nonexistent shell command paths for the new Python OOS helpers. /design accepted OOS prepare runs bash against skills/implement/scripts/python/cli.py oos issue-cap and fails before filing. Use command arrays with python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap and file-conflict-deps.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/test-implement-structure.sh:105
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Structural test still requires step-7a.sh in SKILL while SKILL documents python/cli.py implement step-7a. CI structural gate does not validate the live Step 7a entrypoint; regression can merge undetected. Update harness to pin Python Step 7a fence and rebase-macro expectations.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/design/scripts/file-design-oos.sh:14-15
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] CAP_SH and DEPS_SH point at a nonexistent path and are invoked with bash. /design accepted-OOS prepare fails before issue capping or dependency generation. Call python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap and oos file-conflict-deps directly, or use argv arrays.
- **Suggested revision**: Address the concern above.


### FINDING_41: risk-integration: python/ship.py:1323-1331
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New security-sidecar pre-PR OOS gate has no dedicated pytest; test_ship only covers non-security accepted files. Refactor can drop security-sidecar branch undetected. Add test with non-empty security-oos-observations.md and no accepted non-security OOS asserting oos-filing.
- **Suggested revision**: Address the concern above.


### FINDING_42: risk-integration: python/stall_recovery.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Design/implement use Python stall-recovery; pytest has 2 smoke tests; CI runs 3 bash stall-recovery-report harnesses. validate-token/terminal-state/record-escalation regressions miss CI. Port three bash harnesses to python/test_stall_recovery.py and update Makefile shards.
- **Suggested revision**: Address the concern above.


### FINDING_43: risk-integration: python/test_execution_issues.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only 2 execution_issues tests; flush/refresh bash harnesses remain in CI per Makefile. FLUSH_STATUS and sentinel idempotency regress on Python flush path. Add flush/refresh/append CLI contract tests; retire bash harness targets.
- **Suggested revision**: Address the concern above.


### FINDING_44: risk-integration: Makefile:621-767
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan requires replacing C4c shell harness targets with pytest; Makefile and test-implement-structure.sh still pin bash step-7a and disposition harnesses. Merge gate does not validate Python surfaces /implement runs. Wire new pytest into harness shards; update structural test expectations.
- **Suggested revision**: Address the concern above.


### FINDING_54: **correctness** `skills/design/scripts/file-design-oos.sh:14-15` — The cutover sets `CAP_SH` and `DEPS_SH` to `$PLUGIN_ROOT/skills/implement/scripts/python/cli.py oos issue-cap` (and the file-conflict-deps variant). That path does not exist. `cmd_prepare` invokes them with `bash "$CAP_SH" ...`, so design OOS prepare always fails before cap or dependency emission. **Suggested fix:** Point at the real CLI, e.g. `python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap` and `python3 "$PLUGIN_ROOT/python/cli.py" oos file-conflict-deps`, or split script path from subcommand args instead of embedding subcommands in one string.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `skills/design/scripts/file-design-oos.sh:14-15` — The cutover sets `CAP_SH` and `DEPS_SH` to `$PLUGIN_ROOT/skills/implement/scripts/python/cli.py oos issue-cap` (and the file-conflict-deps variant). That path does not exist. `cmd_prepare` invokes them with `bash "$CAP_SH" ...`, so design OOS prepare always fails before cap or dependency emission. **Suggested fix:** Point at the real CLI, e.g. `python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap` and `python3 "$PLUGIN_ROOT/python/cli.py" oos file-conflict-deps`, or split script path from subcommand args instead of embedding subcommands in one string.
- **Suggested revision**: Address the concern above.


### FINDING_57: **correctness** `python/file_oos.py:534-586` — `disposition_checkpoint_main` omits pre-gate checks from `skills/implement/scripts/oos-disposition-checkpoint.sh:175-183`. When `security-oos-observations.md` is non-empty, the bash helper exits **2** with a validation failure. Python goes straight to `disposition_gate`, which returns **0** when `non_sec == 0` (`python/file_oos.py:479`). That lets Step 8 clear `OOS_PENDING` without security disposition and bypasses the ship-path guard that only runs while `OOS_PENDING=true`. **Suggested fix:** Fail closed before `disposition_gate` when the security sidecar exists (and when non-security accepted OOS exists but `oos-issues.ndjson` is missing), matching the bash validation messages and exit **2** semantics.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/file_oos.py:534-586` — `disposition_checkpoint_main` omits pre-gate checks from `skills/implement/scripts/oos-disposition-checkpoint.sh:175-183`. When `security-oos-observations.md` is non-empty, the bash helper exits **2** with a validation failure. Python goes straight to `disposition_gate`, which returns **0** when `non_sec == 0` (`python/file_oos.py:479`). That lets Step 8 clear `OOS_PENDING` without security disposition and bypasses the ship-path guard that only runs while `OOS_PENDING=true`. **Suggested fix:** Fail closed before `disposition_gate` when the security sidecar exists (and when non-security accepted OOS exists but `oos-issues.ndjson` is missing), matching the bash validation messages and exit **2** semantics.
- **Suggested revision**: Address the concern above.


### FINDING_64: **risk-integration** `skills/design/scripts/file-design-oos.sh:14-16,307-316` — The OOS cap/deps cutover stores a single string with embedded spaces (`$PLUGIN_ROOT/skills/implement/scripts/python/cli.py oos issue-cap`) and invokes it with `bash "$CAP_SH"`. That path does not exist, and `bash` cannot run `python3 … cli.py oos issue-cap` argv correctly. `/design` Step 5b `prepare` will fail at cap time (exit 2) instead of staging accepted OOS for `/issue`. **Suggested fix:** Use a proper argv array, e.g. `CAP_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap)` and `"${CAP_CMD[@]}" --input-file …`, and the same pattern for `file-conflict-deps`.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/file-design-oos.sh:14-16,307-316` — The OOS cap/deps cutover stores a single string with embedded spaces (`$PLUGIN_ROOT/skills/implement/scripts/python/cli.py oos issue-cap`) and invokes it with `bash "$CAP_SH"`. That path does not exist, and `bash` cannot run `python3 … cli.py oos issue-cap` argv correctly. `/design` Step 5b `prepare` will fail at cap time (exit 2) instead of staging accepted OOS for `/issue`. **Suggested fix:** Use a proper argv array, e.g. `CAP_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" oos issue-cap)` and `"${CAP_CMD[@]}" --input-file …`, and the same pattern for `file-conflict-deps`.
- **Suggested revision**: Address the concern above.


### FINDING_65: **risk-integration** `python/step_7a.py:32-77` and `skills/implement/SKILL.md:709` — `SKILL.md` routes Step 7a to `python3 … cli.py implement step-7a`, but the Python entrypoint is a thin stub. It does not run `rebase-checkpoint-probe.sh` 7a.r (the bash helper at `skills/implement/scripts/step-7a.sh:429-430` still does), skips the small/non-runtime classifier, transcript capture, `run-log write`/`commit`, and forked-target base selection. It only reads a optional `7a.r` relay file and uses `parse_known_args`, so `--issue-number`, `--run-id`, `--no-logs-commit`, and `--forked-target` from the SKILL fence are silently ignored. **Suggested fix:** Port the full `step-7a.sh` orchestration into `run_step7a` (or keep the bash wrapper as the live entrypoint until parity is complete), accept/reject unknown flags explicitly, and expand `python/test_step_7a.py` beyond the single happy-path KV test.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `python/step_7a.py:32-77` and `skills/implement/SKILL.md:709` — `SKILL.md` routes Step 7a to `python3 … cli.py implement step-7a`, but the Python entrypoint is a thin stub. It does not run `rebase-checkpoint-probe.sh` 7a.r (the bash helper at `skills/implement/scripts/step-7a.sh:429-430` still does), skips the small/non-runtime classifier, transcript capture, `run-log write`/`commit`, and forked-target base selection. It only reads a optional `7a.r` relay file and uses `parse_known_args`, so `--issue-number`, `--run-id`, `--no-logs-commit`, and `--forked-target` from the SKILL fence are silently ignored. **Suggested fix:** Port the full `step-7a.sh` orchestration into `run_step7a` (or keep the bash wrapper as the live entrypoint until parity is complete), accept/reject unknown flags explicitly, and expand `python/test_step_7a.py` beyond the single happy-path KV test.
- **Suggested revision**: Address the concern above.


### FINDING_66: **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:94-98` vs `skills/implement/SKILL.md:8477` — `SKILL.md` Step 18b now calls `python3 … cli.py final-report step18b`, but the shipped wrapper still invokes `write-final-report.sh`. Any caller still using `step-18b-final-report.sh` (including `scripts/test-implement-structure.sh:111`) hits the retired bash path instead of the Python contract documented in SKILL. **Suggested fix:** Make `step-18b-final-report.sh` delegate to `python3 "$PLUGIN_ROOT/python/cli.py" final-report step18b …`, or delete the wrapper and update structural tests to pin the Python fence only.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/step-18b-final-report.sh:94-98` vs `skills/implement/SKILL.md:8477` — `SKILL.md` Step 18b now calls `python3 … cli.py final-report step18b`, but the shipped wrapper still invokes `write-final-report.sh`. Any caller still using `step-18b-final-report.sh` (including `scripts/test-implement-structure.sh:111`) hits the retired bash path instead of the Python contract documented in SKILL. **Suggested fix:** Make `step-18b-final-report.sh` delegate to `python3 "$PLUGIN_ROOT/python/cli.py" final-report step18b …`, or delete the wrapper and update structural tests to pin the Python fence only.
- **Suggested revision**: Address the concern above.


### FINDING_67: **risk-integration** `scripts/file-failure-report-cross-repo.sh:8,138-165` — Tier-B public-file validation still shells out to `skills/implement/scripts/stall-recovery-report.sh` (`STALL_REPORT_SCRIPT`), not `python/cli.py stall-recovery validate-tier-b-public-file` as the plan requires. Runtime still works while the bash script exists, but the cutover is incomplete and stall-report filing will regress once `stall-recovery-report.sh` is deleted. **Suggested fix:** Replace `STALL_REPORT_SCRIPT` invocations with `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery validate-tier-b-public-file …`, preserving `--profile` / `--artifact-prefix` forwarding.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `scripts/file-failure-report-cross-repo.sh:8,138-165` — Tier-B public-file validation still shells out to `skills/implement/scripts/stall-recovery-report.sh` (`STALL_REPORT_SCRIPT`), not `python/cli.py stall-recovery validate-tier-b-public-file` as the plan requires. Runtime still works while the bash script exists, but the cutover is incomplete and stall-report filing will regress once `stall-recovery-report.sh` is deleted. **Suggested fix:** Replace `STALL_REPORT_SCRIPT` invocations with `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery validate-tier-b-public-file …`, preserving `--profile` / `--artifact-prefix` forwarding.
- **Suggested revision**: Address the concern above.


### FINDING_68: **risk-integration** `skills/implement/SKILL.md:116-119` — Structured invocation pins still document retired bash entrypoints (`compose-pr-summary.sh`, `render-run-summary.sh`, `implement-finalize.sh teardown`) while live wrappers already call Python (`scripts/ship-pr.sh`, `skills/implement/scripts/step-18-finalize.sh:74`, `skills/implement/scripts/step-17.sh:45`). Agent-lint pins and orchestrator copy can route implementers to deleted or bypassed surfaces. **Suggested fix:** Refresh the pin block to the Python verbs (`pr compose-summary`, `render run-summary`, `implement-finalize teardown`) matching the active callers.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:116-119` — Structured invocation pins still document retired bash entrypoints (`compose-pr-summary.sh`, `render-run-summary.sh`, `implement-finalize.sh teardown`) while live wrappers already call Python (`scripts/ship-pr.sh`, `skills/implement/scripts/step-18-finalize.sh:74`, `skills/implement/scripts/step-17.sh:45`). Agent-lint pins and orchestrator copy can route implementers to deleted or bypassed surfaces. **Suggested fix:** Refresh the pin block to the Python verbs (`pr compose-summary`, `render run-summary`, `implement-finalize teardown`) matching the active callers.
- **Suggested revision**: Address the concern above.


### FINDING_69: **risk-integration** `scripts/test-implement-structure.sh:105,162,283` — Structural harness still requires `skills/implement/scripts/step-7a.sh` and `implement-finalize.sh" teardown` in `step-18-finalize.sh`, but `SKILL.md` now documents `python/cli.py implement step-7a` (line 709) and `step-18-finalize.sh` calls `implement-finalize teardown` via Python (line 74). The plan’s `test-implement-structure.sh` update was not applied; `make test-implement-structure` will drift from the live routing. **Suggested fix:** Update harness needles to `python/cli.py implement step-7a` and `implement-finalize teardown` (Python), and align immediate-background pins with the SKILL fences.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `scripts/test-implement-structure.sh:105,162,283` — Structural harness still requires `skills/implement/scripts/step-7a.sh` and `implement-finalize.sh" teardown` in `step-18-finalize.sh`, but `SKILL.md` now documents `python/cli.py implement step-7a` (line 709) and `step-18-finalize.sh` calls `implement-finalize teardown` via Python (line 74). The plan’s `test-implement-structure.sh` update was not applied; `make test-implement-structure` will drift from the live routing. **Suggested fix:** Update harness needles to `python/cli.py implement step-7a` and `implement-finalize teardown` (Python), and align immediate-background pins with the SKILL fences.
- **Suggested revision**: Address the concern above.


### FINDING_70: **risk-integration** `skills/implement/references/stall-recovery.md:5,40,47,61,111` — Step 18a procedural docs still tell operators to run `stall-recovery-report.sh …` subcommands, while `skills/implement/SKILL.md` Step 18a contract surface now lists `python/cli.py stall-recovery` and design callers (`design-failure-report.sh:7`, `review-design-step3-loop.sh:26`) already use Python. Following the reference doc during stall recovery will hit the wrong entrypoint after bash deletion. **Suggested fix:** Replace every `stall-recovery-report.sh <subcommand>` example with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery <subcommand>` and keep argv ordering identical to the Python dispatcher.
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `skills/implement/references/stall-recovery.md:5,40,47,61,111` — Step 18a procedural docs still tell operators to run `stall-recovery-report.sh …` subcommands, while `skills/implement/SKILL.md` Step 18a contract surface now lists `python/cli.py stall-recovery` and design callers (`design-failure-report.sh:7`, `review-design-step3-loop.sh:26`) already use Python. Following the reference doc during stall recovery will hit the wrong entrypoint after bash deletion. **Suggested fix:** Replace every `stall-recovery-report.sh <subcommand>` example with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery <subcommand>` and keep argv ordering identical to the Python dispatcher.
- **Suggested revision**: Address the concern above.


### FINDING_75: **code-quality** `python/stall_recovery.py:470-477` — `dedup-tier-a-report` is routed to `compose_report()`, but the retired bash handler (`cmd_dedup_tier_a_report` in `skills/implement/scripts/stall-recovery-report.sh:2496-2535`) runs cross-repo dedup via `file-failure-report-cross-repo.sh --dedup-only` and writes `STALL_RECOVERY_REPORT_STATUS` values like `no-match` / `lookup-failed-open`. The Python path instead composes a fresh report body, so `design-failure-report.sh` `file_tier_a_after_compose()` will not get dedup status KVs and Tier A filing behavior diverges. **Suggested fix:** Implement a dedicated `dedup_tier_a_report()` function with the bash argv surface (`--body-file`, `--attempts-file`, `--escalation-ledger-file`, `--root-cause-file`) and stdout KV contract, and keep `compose_report()` only for `compose-report`.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/stall_recovery.py:470-477` — `dedup-tier-a-report` is routed to `compose_report()`, but the retired bash handler (`cmd_dedup_tier_a_report` in `skills/implement/scripts/stall-recovery-report.sh:2496-2535`) runs cross-repo dedup via `file-failure-report-cross-repo.sh --dedup-only` and writes `STALL_RECOVERY_REPORT_STATUS` values like `no-match` / `lookup-failed-open`. The Python path instead composes a fresh report body, so `design-failure-report.sh` `file_tier_a_after_compose()` will not get dedup status KVs and Tier A filing behavior diverges. **Suggested fix:** Implement a dedicated `dedup_tier_a_report()` function with the bash argv surface (`--body-file`, `--attempts-file`, `--escalation-ledger-file`, `--root-cause-file`) and stdout KV contract, and keep `compose_report()` only for `compose-report`.
- **Suggested revision**: Address the concern above.



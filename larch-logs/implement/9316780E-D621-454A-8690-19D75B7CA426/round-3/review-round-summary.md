# Review Round 3

- Mode: `diff`
- 21 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 7a code-flow diagram is a production stub
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-migration-parity-output.txt, dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: `generate_code_flow_diagram()` in `python/pr_body.py` discards `base_remote` / `base_ref`, never builds `code-flow-prompt.md` from a merge-base diff, and on the production path (no `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS`) writes a hardcoded `Implementation --> Runtime` Mermaid diagram instead of invoking `agent launch-claude-subprocess`. Step 7a therefore upserts a generic diagram unrelated to the branch diff while reporting success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port bash prompt assembly and agent launch-claude-subprocess invocation.
  - From codex-generic-output.txt: Restore the production subprocess launch path, write the changed-file prompt, and keep `LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS` only as the test override.
  - From dyn-migration-parity-output.txt: Port the bash prompt assembly (`git merge-base` + `git diff --name-only`), invoke the Claude subprocess launcher when the test hook is unset, and thread `base_remote` / `base_ref` through the full path.
  - From dyn-callsite-routing-output.txt: Port the bash launcher/prompt/sanitize path into `generate_code_flow_diagram()` (or have `step_7a.py` invoke `python/cli.py diagram code-flow` with the same argv as the retired shell helper), and add a pytest that fails when the stub path is taken without the test env var.


### FINDING_10: `issue_cap` accepts malformed non-empty batches
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `issue_cap` silently returns success for a non-empty malformed batch with no `### OOS_<N>:` blocks. The retired helper failed this path after `issue parse-input`, so malformed combined OOS files can proceed uncapped and fail downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Reuse `issue parse-input` parity or add equivalent validation that non-empty parsed items exactly match `### OOS_<N>:` headings before returning success.


### FINDING_11: `populate-sensitive-corpus` and `lint` still delegate to bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-callsite-routing-output.txt, dyn-lint-readiness-output.txt
- **Severity**: important
- **Concern**: `populate_sensitive_corpus` and `lint` in `python/stall_recovery.py` still shell out to `stall-recovery-report.sh` while live callers use the Python CLI. Deleting the bash script per the C4c plan breaks Tier B corpus population, allowlist lint, and `design-failure-report.sh` populate/validate flows; the dual surface also blocks `lint-retired-scripts` safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port remaining subcommands or defer bash deletion.
  - From cursor-specialist-edge-cases-output.txt: Port `populate-sensitive-corpus` and `lint` to Python, or defer bash deletion until those subcommands are native.
  - From dyn-callsite-routing-output.txt: Finish the port for those two subcommands in Python (or route them through already-native helpers) before removing `stall-recovery-report.sh`; add pytest coverage for both subcommands without bash delegation.
  - From dyn-lint-readiness-output.txt: Port the remaining two subcommands into `stall_recovery.py` (or shared helpers), delete the bash delegation path, and add focused tests so `make lint-retired-scripts` stays safe after script removal.


### FINDING_14: Stall-recovery CI coverage thinned without compose-report / Tier B parity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Makefile stall-recovery shards now run thin pytest (`validate_token` / `validate_terminal` only). Bash harness cases for `compose-report` sensitive-token rejection, path confinement, Tier B filing, `validate-tier-b-public-file` corpus checks, `populate-sensitive-corpus`, and `record-attempt` no longer run in CI. Regressions in security-sensitive stall-recovery behavior can ship with green harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add pytest coverage for `compose-report` and `validate-tier-b` parity cases before removing bash harness from the Makefile target.
  - From cursor-specialist-testing-output.txt: Add pytest for `validate-tier-b-public-file`, `compose-report`, `record-attempt`; finish port or retain bash harness for delegated paths.


### FINDING_15: `test-step-7a` swapped to thin mocked pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI target swapped from bash harness (~20 scenarios) to 3 mocked pytest tests. Merged Step 7a can break diagram upsert, rebase flush, or transcript paths while harness-12 stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port `test-step-7a.sh` scenarios into `test_step_7a.py` before removing bash harness from Makefile.


### FINDING_16: Production final-report/finalize on Python; CI still exercises bash harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Production uses Python `final-report` and `implement-finalize` CLI, but CI still runs bash-only `test-write-final-report` and `test-implement-finalize`. `pr_body.write_final_report` or finalize CLI KV regressions can ship while harness-6/20 pass on retired bash scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add plan-required pytest in `test_pr_body.py` and `test_finalize.py`; repoint Makefile targets after parity.


### FINDING_17: Runtime OOS on Python; CI OOS harnesses still bash-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Runtime OOS uses Python CLI, but CI OOS harnesses still test bash scripts; `test_file_oos.py` adds only one checkpoint test. Python disposition gate or issue-cap behavior can diverge from bash while step-8 checkpoint fails in production with green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port `test-oos-disposition-gate`, issue-cap, and file-conflict-deps coverage to `test_file_oos.py`; update Makefile targets.


### FINDING_18: Plan-required `test_pr_body.py` cases missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required tests for new `pr_body` APIs were not added despite large `pr_body.py` changes. `EMIT_BODY`, `WFR_RC`, cost line, or comment-only final-report behavior can break on the Python path with no targeted test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Implement plan-listed `test_pr_body.py` cases for `write_final_report`, `step18b`, `render_run_summary`, `post_tracking_issue`.


### FINDING_2: `write_final_report()` miscounts execution issues and warnings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `write_final_report()` hardcodes `warnings=0` and counts all bullet lines as execution issues without ndjson fallback. Final summary shows wrong Exec issues/Warnings counts after Step 7a flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port bash `refresh_issue_counts()` category split and ndjson fallback.


### FINDING_20: `implement-finalize teardown` stdout contract regression
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `implement-finalize teardown` no longer matches bash stdout contract: `teardown()` never resolves tracking-issue URL via `gh issue view`, `_emit_finalize_result()` always prints empty `ISSUE_URL=`, and omits `FINALIZE_SUBCOMMAND=teardown` required by Step 18 docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Fetch and emit the live issue URL in `teardown()`, add `issue_url` to `FinalizeResult`, emit it from `_emit_finalize_result()`, and print phase-specific `FINALIZE_SUBCOMMAND` (`postbump` / `postmerge` / `teardown`) like the retired bash driver.


### FINDING_21: `record_escalation()` drops bash parity; caller omits failure-detail log
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `record_escalation()` writes caller fields without `safe_*` token validation, omits `failure_detail_log` from the TSV row, and does not emit `ESCALATION_LEDGER_FILE` on success. Separately, `review_and_fix.py` cutover dropped `--failure-detail-log` that bash forwarded from `stderr_path`, so Step 5 coder-waterfall escalation ledgers lose the detail pointer `compose-report` relies on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Reuse `_safe_token()` (or equivalent) before writing, include a tmpdir-relative `failure_detail_log` column when `--failure-detail-log` is set, emit `ESCALATION_LEDGER_FILE`, and keep degraded/fallback paths aligned with the bash helper.
  - From dyn-migration-parity-output.txt: Pass `--failure-detail-log` when `stderr_path` is a readable tmpdir-local file, matching the old subprocess argv.


### FINDING_22: `validate_terminal_state()` is not a faithful bash port
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `validate_terminal_state()` emits `TERMINAL_STATE_VALID=` instead of bash `VALID=`, skips `FAILURE_DETAIL_LOG` in required-key checks, does not validate token safety or reject URL/path-like values, and does not verify `FAILURE_DETAIL_LOG` paths under the tmpdir when non-empty. Unsafe terminal-state files bash would reject can pass on the Python path used by `design-stage-terminal-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Emit `VALID=` for compatibility, port `terminal_state_value_valid` / detail-log path checks from the bash script, and require the `FAILURE_DETAIL_LOG` key (empty allowed).


### FINDING_23: Post-cutover structural harnesses still grep retired bash scripts
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: After Python cutover, structural CI harnesses still require retired shell entrypoints: `test-implement-timing-rehydration.sh` greps `implement-finalize.sh teardown` while `step-18-finalize.sh` calls `python/cli.py implement-finalize teardown`; `test-render-cost-line-callsites.sh` and `test-render-run-summary-callsites.sh` still require `render-run-summary.sh` / `write-final-report.sh` though live paths invoke `python/cli.py render run-summary` and `python/cli.py final-report write`. Shards 11, 17, and 19 should fail or give false confidence depending on whether harnesses were updated elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Update the awk pattern to match `implement-finalize teardown` (or `python/cli.py implement-finalize teardown`) and keep the “done mark before teardown” invariant.
  - From dyn-callsite-routing-output.txt: Repoint both greps at the Python CLI invocations and per-bucket flag forwarding in `render-final-summary.sh` / `pr_body.write_final_report`.
  - From dyn-callsite-routing-output.txt: Assert `python/cli.py render run-summary` wiring (including `--claude-input-tokens` / cost flags) instead of the retired shell script name.


### FINDING_24: Dual Step 7a entrypoints (live routing vs stale bash wrapper)
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` routes Step 7a through `python/cli.py implement step-7a`, but `step-7a.sh` still exists and calls `flush-execution-issues.sh` and `generate-code-flow-diagram.sh`. Stale docs, harnesses, or manual invocation can hit a different implementation than the Python orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Either delete or thin `step-7a.sh` to delegate to `python/cli.py implement step-7a`, and sweep remaining references (`test-implement-rebase-macro.sh`, `docs/linting.md`) so only one Step 7a authority remains.


### FINDING_3: `rebase-failed` stall misclassified (no Step 8 retry)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_classify_text()` lacks `rebase-failed` → `transient-infra` handling present in bash. `STALL_STEP=rebase-failed` gets `RESUME_HINT=none` instead of `step8-shippr` retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add explicit `rebase-failed` branch matching `stall-recovery-report.sh`.


### FINDING_4: `ci-fix-exhausted` always classified unrecoverable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `ci-fix-exhausted` is always classified unrecoverable regardless of detail log. CI-fix exhaustion with a valid detail log loses recoverable classification and retry budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror bash `detail_log_valid` `ci-fix-exhausted` branch.


### FINDING_5: `retry_policy()` caps diverge from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `retry_policy()` caps differ from bash (lint/test 2 vs 8, missing `ci-fix-exhausted`/`dispatch-failure`, unrecoverable defaults to 1). Stalls retry too early or when they should not retry at all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port `retry_cap_for` / `retry_delay_for` from bash.


### FINDING_6: Tier B public-file validation fails open and is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `validate_tier_b_public_file()` swallows `OSError` on corpus/public reads and returns `PUBLIC_FILE_VALID=true`; it can skip content validation when no corpus is passed and uses naive substring matching without bash allowlists. Unreadable corpus/public files and bodies bash would reject can pass Tier B validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return `PUBLIC_FILE_VALID=false` on `OSError` during checks.
  - From cursor-specialist-edge-cases-output.txt: Fail closed on `OSError`; require corpus for Tier B; port `sensitive_token_rejects_file` allowlist logic from `stall-recovery-report.sh`.
  - From dyn-migration-parity-output.txt: On `OSError` during corpus or public-file reads, emit `PUBLIC_FILE_VALID=false` and return `1`, matching fail-closed bash behavior.


### FINDING_7: `compose_report` is an incomplete security-sensitive port
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: Python `compose_report` is a stub relative to bash: hardcodes `stall-recovery-*` artifact paths and ignores `artifact_prefix` overrides from `design-failure-report.sh`; ignores `sensitive-corpus` and validation flags; skips `sensitive_token_rejects_file`; appends bounded root-cause prose directly into public output without fail-closed checks; does not perform Tier B upstream filing/dedup. `/design` failure reports and `/implement` Step 18a Tier B paths can leak sensitive tokens, omit bounded root-cause prose, show `FAILURE_CLASS=unknown`, or end at `status=printed` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port bash `cmd_compose_report`: honor `artifact_prefix` paths, run sensitive corpus rejection, invoke `file-failure-report-cross-repo` for Tier B, emit filed/dedup-comment/fallback statuses.
  - From cursor-specialist-edge-cases-output.txt: Resolve paths via `_artifact_path(tmpdir, default_name, artifact_prefix)` for classification, root-cause, and bounded files.
  - From codex-generic-output.txt: Parse the evidence and corpus flags, enforce the sensitive-corpus/content checks before writing output, and fail closed on unsafe public content.


### FINDING_8: `materialize_manifest_oos()` misroutes security OOS by manifest key
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `materialize_manifest_oos()` does not read spaced `Focus area` manifest keys per plan. Security manifest OOS can land in the public accepted file instead of the security sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Also read `Focus area` key before `_security_signal` routing.


### FINDING_9: `file-conflict-deps` emits malformed dependency TSV rows
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `file-conflict-deps` emits rows like `OOS_1\tOOS_2`, but `/larch:issue` requires numeric-only `<blocker-1based>\t<blocked-1based>` rows. When two OOS items touch the same file, `file-design-oos.sh` forwards the TSV and `/larch:issue` rejects it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Emit `f"{a}\t{b}\n"` and add a regression that feeds the generated TSV into the intra-batch dependency contract.



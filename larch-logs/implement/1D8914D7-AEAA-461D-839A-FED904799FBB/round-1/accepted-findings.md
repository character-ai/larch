### FINDING_10: correctness: skills/implement/scripts/step-7a.sh:399-403
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] rebase-checkpoint-probe.sh uses || true and step-7a.sh always exits 0, breaking macro exit-code routing 7a.r conflict (probe exit 1) but step-7a Bash tool exits 0; orchestrator may take macro success branch and skip conflict resolution Remove || true and propagate probe rc, or update SKILL macro to KV-only routing and test conflict envelope
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-step-7a.sh:107-110
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan failure-mode test for generator crash is not implemented despite crash stub. Empty-stdout exit 99 path could regress without CI signal; plan explicitly required mitigation. Add STEP7A_GEN_MODE=crash case asserting failed status warning and continued pipeline.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/scripts/step-7a.sh:209-224
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] no_logs_commit branch always sets LOG_FLUSH_STATUS=skipped-no-logs-commit. Flush failure then --no-logs-commit true reports skipped instead of degraded masking degraded flush. Only set skipped-no-logs-commit when status is still ok; add combined harness case.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/implement/scripts/step-7a.sh:328-329
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Duplicate Step 7a token/timing marks with generate-code-flow-diagram.sh; skip path now marks without generator. Timing/token reports gain extra boundaries vs pre-consolidation SKILL.md behavior. Keep marks in one script only; add structure or harness assertion for single mark.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent]  No test for generate-code-flow-diagram STATUS=skipped envelope. Skipped generator status could map or upsert-gate incorrectly without coverage. Add stub skipped mode and assertions for DIAGRAM_STATUS and upsert behavior.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent]  No golden byte-identical summary-diagrams.md test. Architecture cat vs placeholder regressions may reach live tracking issues undetected. Add ARCHITECTURE_DIAGRAM_FILE fixture with cmp to expected output.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/test-step-7a.sh:99-102,309-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] diagram-rejected test stubs STATUS=failed but generator returns STATUS=skipped on sanitizer rejection. CI can pass while production sets DIAGRAM_STATUS=skipped omits Warnings and skips upsert unlike test expectations. Stub STATUS=skipped for sanitizer case and assert skipped status no Warnings no upsert; add separate failed-path test if needed.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/implement/scripts/step-7a.sh:399-401
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-bump flush runs unconditionally after rebase probe because of trailing || true. On 7a.r conflict (probe exit 1) step-7a still runs flush and may larch-log.sh commit while the branch is mid-rebase; main had separate fences so macro routing blocked flush until resolution. Capture probe rc; skip run_log_flush unless rc=0; or defer flush to a post-macro invocation.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/implement/scripts/step-7a.sh:369-371
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sanitizer upsert skip uses substring match on SKIP_REASON only. Production STATUS=skipped with REASON_TOKEN=pipe-in-node-label does not match *sanitiz*|*reject* so tracking-issue upsert still runs despite step-7a.md invariant. Set COMMENT_UPSERT_SKIP=true when gen_status=skipped or match known sanitizer tokens.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/implement/SKILL.md:1434
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Macro text still references probe process exit code but step-7a always exits 0. Orchestrator may treat failed 7a.r as success from Bash exit alone while flush already ran inside step-7a. State that routing must parse REBASE_OUTCOME from full step-7a stdout; align with gated flush.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/implement/scripts/step-7a.sh:209-224
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] no_logs_commit overwrites degraded LOG_FLUSH_STATUS. Flush fails then --no-logs-commit true yields LOG_FLUSH_STATUS=skipped-no-logs-commit hiding degraded state. Preserve degraded when earlier flush steps failed; only emit skipped-no-logs-commit when commit skipped and status still ok.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/implement/scripts/test-step-7a.sh:309-316
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] diagram-rejected test uses STATUS=failed not production STATUS=skipped. Harness can pass while production sanitizer path still upserts on token-only SKIP_REASON. Stub STATUS=skipped with realistic REASON_TOKEN; assert no tracking-issue-summary.sh call.
- **Suggested revision**: Address the concern above.


### FINDING_26: code-quality: skills/implement/scripts/step-7a.sh:328-329
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate Step 7a token/timing marks in step-7a and generate-code-flow-diagram. Double ledger marks per diagram generation. Remove duplicate marks from one script.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/implement/scripts/step-7a.sh:209-224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] no_logs_commit else overwrites LOG_FLUSH_STATUS=degraded with skipped-no-logs-commit. Flush failure plus no_logs_commit=true reports skipped-no-logs-commit hiding degraded flush state from KV consumers. Only set skipped-no-logs-commit when commit skipped and status remains ok.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/implement/scripts/test-step-7a.sh:309-319
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Harness diagram-rejected uses STATUS=failed but production generator emits STATUS=skipped on sanitizer rejection. Live /implement runs surface DIAGRAM_STATUS=skipped and skip upsert via SKIP_REASON matching, while CI only tests a failed stub; production sanitizer path including Warnings append semantics is untested. Add a skipped+sanitizer-rejected harness case; assert DIAGRAM_STATUS=skipped and no upsert; update test-step-7a.md.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/implement/scripts/step-7a.sh:328-329
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 7a marks token/timing ledger twice when generate-code-flow-diagram.sh runs. Token/timing reports get duplicate Step 7a boundaries vs pre-consolidation behavior, skewing run analytics. Remove marks from generate-code-flow-diagram.sh or stop marking in step-7a before calling the generator; update structure test pin if needed.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: skills/implement/scripts/step-7a.sh:222-224
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] no_logs_commit forces LOG_FLUSH_STATUS=skipped-no-logs-commit even after flush failures. Operator or downstream KV consumer sees skipped-no-logs-commit while execution-issues records Tool Failures from a degraded flush. Preserve degraded when already set; only emit skipped-no-logs-commit when flush was otherwise ok.
- **Suggested revision**: Address the concern above.


### FINDING_34: architecture: skills/implement/scripts/test-step-7a.sh:107-110
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] crash stub mode is never exercised. Generator crash-before-envelope regression from plan failure modes has no automated coverage. Add crash test case per plan failure mode 1.
- **Suggested revision**: Address the concern above.


### FINDING_36: **correctness** `skills/implement/scripts/step-7a.sh:209-224` — When `--no-logs-commit true`, the `else` branch at lines 222–223 unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit`, even if an earlier flush helper already set `LOG_FLUSH_STATUS=degraded` (first `flush-execution-issues.sh`, post-transcript flush, or `capture-session-transcript.sh`). That contradicts the implementation plan’s aggregate rule: `degraded` when monitored helpers fail, and `skipped-no-logs-commit` only when the commit step is skipped. A run with `--no-logs-commit true` plus a flush failure would emit `skipped-no-logs-commit` instead of `degraded`, hiding degradation in the KV tail. **Suggested fix:** In the `no_logs_commit` branch, set `skipped-no-logs-commit` only when `LOG_FLUSH_STATUS` is still `ok` (e.g. `if [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`). Add a harness case combining `--no-logs-commit true` with a failing first `flush-execution-issues.sh` stub asserting `LOG_FLUSH_STATUS=degraded`.
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:209-224` — When `--no-logs-commit true`, the `else` branch at lines 222–223 unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit`, even if an earlier flush helper already set `LOG_FLUSH_STATUS=degraded` (first `flush-execution-issues.sh`, post-transcript flush, or `capture-session-transcript.sh`). That contradicts the implementation plan’s aggregate rule: `degraded` when monitored helpers fail, and `skipped-no-logs-commit` only when the commit step is skipped. A run with `--no-logs-commit true` plus a flush failure would emit `skipped-no-logs-commit` instead of `degraded`, hiding degradation in the KV tail. **Suggested fix:** In the `no_logs_commit` branch, set `skipped-no-logs-commit` only when `LOG_FLUSH_STATUS` is still `ok` (e.g. `if [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`). Add a harness case combining `--no-logs-commit true` with a failing first `flush-execution-issues.sh` stub asserting `LOG_FLUSH_STATUS=degraded`.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:328-329,340
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate Step 7a token/timing ledger marks in step-7a.sh and generate-code-flow-diagram.sh. Every successful diagram generation double-records the same Step 7a mark in ledgers skewing timing/token reports. Remove duplicate marks from one script keeping single mark on skip path if generator not called.
- **Suggested revision**: Address the concern above.


### FINDING_41: **correctness** `skills/implement/scripts/step-7a.sh:209-224` — In `run_log_flush`, `LOG_FLUSH_STATUS` is set to `degraded` when the first or post-transcript `flush-execution-issues.sh` call fails (or when `capture-session-transcript.sh` / `larch-log.sh commit` fails), but the final `else` branch unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit` whenever `no_logs_commit=true`, with no guard on the current value. Any earlier `degraded` assignment is therefore overwritten, so callers reading the KV tail cannot distinguish a failed pre-bump flush from a clean skip of the commit step. That contradicts the plan contract (“`degraded` when flush helpers fail; `skipped-no-logs-commit` when commit is skipped”) and leaves `test-step-7a.sh` without coverage for the combined `no_logs_commit=true` + flush-failure path. **Suggested fix:** Only set `skipped-no-logs-commit` when commit is intentionally skipped and no degradation was recorded—for example `if [ "${no_logs_commit:-false}" != "true" ]; then ... elif [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`—and add a harness case that stubs the first flush to fail with `--no-logs-commit true` and asserts `LOG_FLUSH_STATUS=degraded`.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:209-224` — In `run_log_flush`, `LOG_FLUSH_STATUS` is set to `degraded` when the first or post-transcript `flush-execution-issues.sh` call fails (or when `capture-session-transcript.sh` / `larch-log.sh commit` fails), but the final `else` branch unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit` whenever `no_logs_commit=true`, with no guard on the current value. Any earlier `degraded` assignment is therefore overwritten, so callers reading the KV tail cannot distinguish a failed pre-bump flush from a clean skip of the commit step. That contradicts the plan contract (“`degraded` when flush helpers fail; `skipped-no-logs-commit` when commit is skipped”) and leaves `test-step-7a.sh` without coverage for the combined `no_logs_commit=true` + flush-failure path. **Suggested fix:** Only set `skipped-no-logs-commit` when commit is intentionally skipped and no degradation was recorded—for example `if [ "${no_logs_commit:-false}" != "true" ]; then ... elif [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`—and add a harness case that stubs the first flush to fail with `--no-logs-commit true` and asserts `LOG_FLUSH_STATUS=degraded`.
- **Suggested revision**: Address the concern above.


### FINDING_45: **risk-integration** `scripts/test-lint-foreground-markers.sh:526-572` — Case 23 was repurposed for `step-7a.sh` and former cases 23–24 were renumbered to 24–25, but `scripts/test-lint-foreground-markers.md:29-30` still documents case 23 as the heredoc negative guard and case 24 as the backslash-continued path. The sibling contract explicitly requires numbering to match harness `# N —` comments, so operators and future editors will follow the wrong case map and may add regressions against the wrong scenarios. **Suggested fix:** Update `scripts/test-lint-foreground-markers.md` to add a case-23 row for the `step-7a.sh` foreground-only happy path and shift the heredoc/backslash entries to cases 24 and 25, matching the harness comments and EOF headers.
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/test-lint-foreground-markers.sh:526-572` — Case 23 was repurposed for `step-7a.sh` and former cases 23–24 were renumbered to 24–25, but `scripts/test-lint-foreground-markers.md:29-30` still documents case 23 as the heredoc negative guard and case 24 as the backslash-continued path. The sibling contract explicitly requires numbering to match harness `# N —` comments, so operators and future editors will follow the wrong case map and may add regressions against the wrong scenarios. **Suggested fix:** Update `scripts/test-lint-foreground-markers.md` to add a case-23 row for the `step-7a.sh` foreground-only happy path and shift the heredoc/backslash entries to cases 24 and 25, matching the harness comments and EOF headers.
- **Suggested revision**: Address the concern above.


### FINDING_46: **risk-integration** `scripts/test-lint-foreground-markers.sh:526-539` — The new `step-7a.sh` branch in `scripts/lint-foreground-markers.sh:349-361` is only covered by a single clean-path fixture (case 23). Unlike background denylist scripts (cases 2, 3, 5, 6, 19 in `scripts/test-lint-foreground-markers.sh:109-216`), there are no harness cases asserting violations for a missing foreground banner, missing `# Foreground required: see BASH_AUTHORING.md §4` comment, or a fence that sets `run_in_background: true` alongside `step-7a.sh`. A regression in `foreground_banner_ok_in_window`, `foreground_comment_ok_before_anchor_idx`, or the `has_rb` guard would pass `make test-lint-foreground-markers` and `make lint`. **Suggested fix:** Add three negative fixtures (mirror cases 2/3/6 semantics) that expect `missing foreground-required banner for step-7a.sh`, `missing foreground-required comment for step-7a.sh`, and `foreground-only invocation must not set run_in_background: true for step-7a.sh`, and document them in `scripts/test-lint-foreground-markers.md`.
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/test-lint-foreground-markers.sh:526-539` — The new `step-7a.sh` branch in `scripts/lint-foreground-markers.sh:349-361` is only covered by a single clean-path fixture (case 23). Unlike background denylist scripts (cases 2, 3, 5, 6, 19 in `scripts/test-lint-foreground-markers.sh:109-216`), there are no harness cases asserting violations for a missing foreground banner, missing `# Foreground required: see BASH_AUTHORING.md §4` comment, or a fence that sets `run_in_background: true` alongside `step-7a.sh`. A regression in `foreground_banner_ok_in_window`, `foreground_comment_ok_before_anchor_idx`, or the `has_rb` guard would pass `make test-lint-foreground-markers` and `make lint`. **Suggested fix:** Add three negative fixtures (mirror cases 2/3/6 semantics) that expect `missing foreground-required banner for step-7a.sh`, `missing foreground-required comment for step-7a.sh`, and `foreground-only invocation must not set run_in_background: true for step-7a.sh`, and document them in `scripts/test-lint-foreground-markers.md`.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/scripts/test-step-7a.sh:107-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] crash stub mode defined but no test case exercises generator crash. Regression for empty-stdout crash path from plan failure modes is unverified. Add crash test asserting failed status warning append comment posted exit 0.
- **Suggested revision**: Address the concern above.



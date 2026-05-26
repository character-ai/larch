### FINDING_1: correctness: skills/implement/scripts/step-7a.sh:369-392
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sanitizer rejection skips larch:diagrams upsert but main always upserted with placeholder. On sanitizer-rejected runs tracking issues lose the larch:diagrams comment that main still posted with Architecture + unavailable placeholder violating byte-identical acceptance. Restore upsert on sanitizer rejection or document intentional contract change and update acceptance plus harness to use STATUS=skipped production shape.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/implement/scripts/test-step-7a.sh:99-102,309-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] diagram-rejected test stubs STATUS=failed but generator returns STATUS=skipped on sanitizer rejection. CI can pass while production sets DIAGRAM_STATUS=skipped omits Warnings and skips upsert unlike test expectations. Stub STATUS=skipped for sanitizer case and assert skipped status no Warnings no upsert; add separate failed-path test if needed.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/implement/scripts/step-7a.sh:209-224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] no_logs_commit else overwrites LOG_FLUSH_STATUS=degraded with skipped-no-logs-commit. Flush failure plus no_logs_commit=true reports skipped-no-logs-commit hiding degraded flush state from KV consumers. Only set skipped-no-logs-commit when commit skipped and status remains ok.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:328-329,340
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate Step 7a token/timing ledger marks in step-7a.sh and generate-code-flow-diagram.sh. Every successful diagram generation double-records the same Step 7a mark in ledgers skewing timing/token reports. Remove duplicate marks from one script keeping single mark on skip path if generator not called.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:176-191
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unreachable non-zero exit check for capture-session-transcript.sh. Dead branch suggests transcript failures set degraded via exit code but helper always exits 0 misleading maintainers. Remove exit-code check or parse SESSION_TRANSCRIPT_STATUS per helper contract.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/implement/scripts/test-step-7a.sh:107-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] crash stub mode defined but no test case exercises generator crash. Regression for empty-stdout crash path from plan failure modes is unverified. Add crash test asserting failed status warning append comment posted exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/implement/scripts/step-7a.sh:360,390
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent append-tool-failure site labels 7a vs step-7a. Operators filtering execution-issues by site see split Step 7a failure entries. Standardize site string across all Step 7a append paths.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/step-7a.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] 403-line monolith bundles classifier compose upsert rebase and full flush. Future edits risk higher regression cost than smaller phased helpers. Consider extracting run_log_flush or classifier when a follow-up refactor is scheduled.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:399
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] rebase-checkpoint-probe suffixed with || true inside always-exit-0 wrapper. Callers relying on probe exit code instead of FD3 KV may miss rebase failures. Ensure Rebase Checkpoint Macro documents KV-only signaling; pre-existing macro concern.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/step-7a.sh:399-403
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] rebase-checkpoint-probe.sh uses || true and step-7a.sh always exits 0, breaking macro exit-code routing 7a.r conflict (probe exit 1) but step-7a Bash tool exits 0; orchestrator may take macro success branch and skip conflict resolution Remove || true and propagate probe rc, or update SKILL macro to KV-only routing and test conflict envelope
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-implement-rebase-macro.sh:63-77
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural harness still requires four rebase-checkpoint-probe.sh invocations in SKILL.md including 7a.r. After moving 7a.r into step-7a.sh SKILL.md has three probes; make test-implement-rebase-macro in test-harnesses-10 fails on merge. Update test-implement-rebase-macro.sh to allow 7a.r inside step-7a.sh (three SKILL fences + script pin) and re-run the harness.
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

### FINDING_17: risk-integration: skills/implement/scripts/test-step-7a.md:12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit]  Harness doc says 10 cases but PASS counts assertions. Operators may misread PASS=40 as 40 cases. Document assertion vs case counting in test-step-7a.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/step-7a.sh:105-106` — `compose_summary_diagrams` still `cat`s `$ARCHITECTURE_DIAGRAM_FILE` with only an existence check, then posts via `tracking-issue-summary.sh` without running `sanitize-mermaid-fragment.sh` on the architecture half (code-flow is sanitized on the success path). A poisoned `ARCHITECTURE_DIAGRAM_FILE` (e.g., via tampered `session-env.sh` or manifest) could publish unsanitized Mermaid or sensitive file content to a GitHub issue comment; `redact-secrets.sh` mitigates secrets but not diagram safety. **Suggested fix:** mirror `pr-body-template.md` and run `sanitize-mermaid-fragment.sh --from-md` on the architecture file before inclusion, or confine reads to paths under `$IMPLEMENT_TMPDIR` / design manifest roots.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/step-7a.sh:287-291` — `--implement-tmpdir` is validated only as an absolute path (`/*`), not as a session cache root (unlike `cleanup-tmpdir.sh` / `test-cache-root-validation` patterns). A mis-set tmpdir could make the helper write logs, transcripts, and token reports outside the intended `~/.cache/larch/sessions/...` tree. **Suggested fix:** reuse the shared cache-root acceptance helper before `mkdir -p` and downstream writes.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/scripts/step-7a.sh:369-371` — `COMMENT_UPSERT_SKIP` uses broad `*sanitiz*|*reject*` globbing on `SKIP_REASON`, which is stricter than `main` (always upserted with placeholders) and may skip the entire `larch:diagrams` comment—including the architecture section—when a non-sanitizer failure happens to embed those substrings. **Suggested fix:** match the canonical `sanitizer-rejected` token from `generate-code-flow-diagram.sh` / `sanitize-mermaid-fragment.sh` only.
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

### FINDING_27: architecture: skills/implement/scripts/step-7a.sh:188-191
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Non-zero rc check for capture-session-transcript is unreachable. Dead degraded branch; misleading maintenance signal. Remove rc check or parse SESSION_TRANSCRIPT_STATUS from stdout.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sanitizer rejection now skips larch:diagrams upsert vs main posting placeholder. Intentional acceptance per issue #2741 not introduced by helper bug alone. Document operator-facing behavior change if needed.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan generator-crash case not in harness. Low residual risk due to * status branch. Add STEP7A_GEN_MODE=crash test if desired.
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

### FINDING_33: correctness: skills/implement/scripts/step-7a.sh:335
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Small/non-runtime skip line uses hardcoded elapsed=0s. Breadcrumb no longer matches SKILL elapsed placeholder convention; minor observability drift. Compute real elapsed or document fixed 0s in step-7a.md.
- **Suggested revision**: Address the concern above.

### FINDING_34: architecture: skills/implement/scripts/test-step-7a.sh:107-110
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] crash stub mode is never exercised. Generator crash-before-envelope regression from plan failure modes has no automated coverage. Add crash test case per plan failure mode 1.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:188-191
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] capture-session-transcript non-zero rc handling is unreachable. Dead degraded branch adds maintenance noise only. Remove rc check or add comment that script always exits 0.
- **Suggested revision**: Address the concern above.

### FINDING_36: **correctness** `skills/implement/scripts/step-7a.sh:209-224` — When `--no-logs-commit true`, the `else` branch at lines 222–223 unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit`, even if an earlier flush helper already set `LOG_FLUSH_STATUS=degraded` (first `flush-execution-issues.sh`, post-transcript flush, or `capture-session-transcript.sh`). That contradicts the implementation plan’s aggregate rule: `degraded` when monitored helpers fail, and `skipped-no-logs-commit` only when the commit step is skipped. A run with `--no-logs-commit true` plus a flush failure would emit `skipped-no-logs-commit` instead of `degraded`, hiding degradation in the KV tail. **Suggested fix:** In the `no_logs_commit` branch, set `skipped-no-logs-commit` only when `LOG_FLUSH_STATUS` is still `ok` (e.g. `if [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`). Add a harness case combining `--no-logs-commit true` with a failing first `flush-execution-issues.sh` stub asserting `LOG_FLUSH_STATUS=degraded`.
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:209-224` — When `--no-logs-commit true`, the `else` branch at lines 222–223 unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit`, even if an earlier flush helper already set `LOG_FLUSH_STATUS=degraded` (first `flush-execution-issues.sh`, post-transcript flush, or `capture-session-transcript.sh`). That contradicts the implementation plan’s aggregate rule: `degraded` when monitored helpers fail, and `skipped-no-logs-commit` only when the commit step is skipped. A run with `--no-logs-commit true` plus a flush failure would emit `skipped-no-logs-commit` instead of `degraded`, hiding degradation in the KV tail. **Suggested fix:** In the `no_logs_commit` branch, set `skipped-no-logs-commit` only when `LOG_FLUSH_STATUS` is still `ok` (e.g. `if [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`). Add a harness case combining `--no-logs-commit true` with a failing first `flush-execution-issues.sh` stub asserting `LOG_FLUSH_STATUS=degraded`.
- **Suggested revision**: Address the concern above.

### FINDING_37: **code-quality** `skills/implement/scripts/step-7a.sh:122-130,144-150,166-169,177-187,194-203,211-217,339-342,379-385` — Every `set +e` / `rc=$?` / `set +e` block uses a second `set +e` where the harness in `skills/implement/scripts/test-step-7a.sh:281-284` uses `set -e` to restore errexit. With the script’s deliberate `set -uo pipefail` (no `-e` on line 4), both `set` calls are no-ops today and `rc=$?` still works; behavior is not wrong right now. The trailing `set +e` is still a copy-paste error: it does not restore errexit and would leave errexit disabled if someone later adds `-e` to the header. **Suggested fix:** Either drop the `set` pairs entirely (consistent with “no `-e`” on line 4) or change each trailing `set +e` to `set -e` only if `-e` is intentionally enabled for that scope; match `test-step-7a.sh` if temporary suppression is kept.
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/step-7a.sh:122-130,144-150,166-169,177-187,194-203,211-217,339-342,379-385` — Every `set +e` / `rc=$?` / `set +e` block uses a second `set +e` where the harness in `skills/implement/scripts/test-step-7a.sh:281-284` uses `set -e` to restore errexit. With the script’s deliberate `set -uo pipefail` (no `-e` on line 4), both `set` calls are no-ops today and `rc=$?` still works; behavior is not wrong right now. The trailing `set +e` is still a copy-paste error: it does not restore errexit and would leave errexit disabled if someone later adds `-e` to the header. **Suggested fix:** Either drop the `set` pairs entirely (consistent with “no `-e`” on line 4) or change each trailing `set +e` to `set -e` only if `-e` is intentionally enabled for that scope; match `test-step-7a.sh` if temporary suppression is kept.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/flush-execution-issues.sh:170-179` — The same `set +e` / `rc=$?` / `set +e` pattern exists in the pre-existing flush helper; not introduced by this branch’s Step 7a consolidation.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/step-7a.sh:394-399` — `BASE_ARGS` uses the Bash 3.2–safe `"${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"` expansion; no issue found under `set -u`.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/step-7a.sh:177-191` — `capture-session-transcript.sh` always exits 0 per `scripts/capture-session-transcript.sh`; the `rc` check is effectively dead but harmless and mirrors defensive wrapping elsewhere.
- **Suggested revision**: Address the concern above.

### FINDING_41: **correctness** `skills/implement/scripts/step-7a.sh:209-224` — In `run_log_flush`, `LOG_FLUSH_STATUS` is set to `degraded` when the first or post-transcript `flush-execution-issues.sh` call fails (or when `capture-session-transcript.sh` / `larch-log.sh commit` fails), but the final `else` branch unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit` whenever `no_logs_commit=true`, with no guard on the current value. Any earlier `degraded` assignment is therefore overwritten, so callers reading the KV tail cannot distinguish a failed pre-bump flush from a clean skip of the commit step. That contradicts the plan contract (“`degraded` when flush helpers fail; `skipped-no-logs-commit` when commit is skipped”) and leaves `test-step-7a.sh` without coverage for the combined `no_logs_commit=true` + flush-failure path. **Suggested fix:** Only set `skipped-no-logs-commit` when commit is intentionally skipped and no degradation was recorded—for example `if [ "${no_logs_commit:-false}" != "true" ]; then ... elif [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`—and add a harness case that stubs the first flush to fail with `--no-logs-commit true` and asserts `LOG_FLUSH_STATUS=degraded`.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:209-224` — In `run_log_flush`, `LOG_FLUSH_STATUS` is set to `degraded` when the first or post-transcript `flush-execution-issues.sh` call fails (or when `capture-session-transcript.sh` / `larch-log.sh commit` fails), but the final `else` branch unconditionally assigns `LOG_FLUSH_STATUS=skipped-no-logs-commit` whenever `no_logs_commit=true`, with no guard on the current value. Any earlier `degraded` assignment is therefore overwritten, so callers reading the KV tail cannot distinguish a failed pre-bump flush from a clean skip of the commit step. That contradicts the plan contract (“`degraded` when flush helpers fail; `skipped-no-logs-commit` when commit is skipped”) and leaves `test-step-7a.sh` without coverage for the combined `no_logs_commit=true` + flush-failure path. **Suggested fix:** Only set `skipped-no-logs-commit` when commit is intentionally skipped and no degradation was recorded—for example `if [ "${no_logs_commit:-false}" != "true" ]; then ... elif [ "$LOG_FLUSH_STATUS" = "ok" ]; then LOG_FLUSH_STATUS=skipped-no-logs-commit; fi`—and add a harness case that stubs the first flush to fail with `--no-logs-commit true` and asserts `LOG_FLUSH_STATUS=degraded`.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] **COMMENT_UPSERT_SKIP initialization** — `COMMENT_UPSERT_SKIP=false` is set at `skills/implement/scripts/step-7a.sh:243` before diagram generation; the sanitizer branch at `369-371` only runs on the generate path and correctly flips the flag when `SKIP_REASON` matches `*sanitiz*|*reject*`. No defect there.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **COMMENT_UPSERT_SKIP initialization** — `COMMENT_UPSERT_SKIP=false` is set at `skills/implement/scripts/step-7a.sh:243` before diagram generation; the sanitizer branch at `369-371` only runs on the generate path and correctly flips the flag when `SKIP_REASON` matches `*sanitiz*|*reject*`. No defect there.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] **Empty `gen_status` (crash / missing envelope)** — The `*)` arm at `362-367` maps empty or unknown `STATUS` to `DIAGRAM_STATUS=failed`, appends a Warning, and leaves `COMMENT_UPSERT_SKIP=false` unless `SKIP_REASON` matches the sanitizer pattern. That matches the plan (“treat crash like `STATUS=failed`; still post placeholder comment unless sanitizer rejection is signaled”) and is not a bug.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **Empty `gen_status` (crash / missing envelope)** — The `*)` arm at `362-367` maps empty or unknown `STATUS` to `DIAGRAM_STATUS=failed`, appends a Warning, and leaves `COMMENT_UPSERT_SKIP=false` unless `SKIP_REASON` matches the sanitizer pattern. That matches the plan (“treat crash like `STATUS=failed`; still post placeholder comment unless sanitizer rejection is signaled”) and is not a bug.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] **Harness gap** — `test-step-7a.sh` case `no-logs-commit` only exercises the happy path; it would not catch the `LOG_FLUSH_STATUS` overwrite above. Fixing the script should include a combined failure test.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **Harness gap** — `test-step-7a.sh` case `no-logs-commit` only exercises the happy path; it would not catch the `LOG_FLUSH_STATUS` overwrite above. Fixing the script should include a combined failure test.
- **Suggested revision**: Address the concern above.

### FINDING_45: **risk-integration** `scripts/test-lint-foreground-markers.sh:526-572` — Case 23 was repurposed for `step-7a.sh` and former cases 23–24 were renumbered to 24–25, but `scripts/test-lint-foreground-markers.md:29-30` still documents case 23 as the heredoc negative guard and case 24 as the backslash-continued path. The sibling contract explicitly requires numbering to match harness `# N —` comments, so operators and future editors will follow the wrong case map and may add regressions against the wrong scenarios. **Suggested fix:** Update `scripts/test-lint-foreground-markers.md` to add a case-23 row for the `step-7a.sh` foreground-only happy path and shift the heredoc/backslash entries to cases 24 and 25, matching the harness comments and EOF headers.
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/test-lint-foreground-markers.sh:526-572` — Case 23 was repurposed for `step-7a.sh` and former cases 23–24 were renumbered to 24–25, but `scripts/test-lint-foreground-markers.md:29-30` still documents case 23 as the heredoc negative guard and case 24 as the backslash-continued path. The sibling contract explicitly requires numbering to match harness `# N —` comments, so operators and future editors will follow the wrong case map and may add regressions against the wrong scenarios. **Suggested fix:** Update `scripts/test-lint-foreground-markers.md` to add a case-23 row for the `step-7a.sh` foreground-only happy path and shift the heredoc/backslash entries to cases 24 and 25, matching the harness comments and EOF headers.
- **Suggested revision**: Address the concern above.

### FINDING_46: **risk-integration** `scripts/test-lint-foreground-markers.sh:526-539` — The new `step-7a.sh` branch in `scripts/lint-foreground-markers.sh:349-361` is only covered by a single clean-path fixture (case 23). Unlike background denylist scripts (cases 2, 3, 5, 6, 19 in `scripts/test-lint-foreground-markers.sh:109-216`), there are no harness cases asserting violations for a missing foreground banner, missing `# Foreground required: see BASH_AUTHORING.md §4` comment, or a fence that sets `run_in_background: true` alongside `step-7a.sh`. A regression in `foreground_banner_ok_in_window`, `foreground_comment_ok_before_anchor_idx`, or the `has_rb` guard would pass `make test-lint-foreground-markers` and `make lint`. **Suggested fix:** Add three negative fixtures (mirror cases 2/3/6 semantics) that expect `missing foreground-required banner for step-7a.sh`, `missing foreground-required comment for step-7a.sh`, and `foreground-only invocation must not set run_in_background: true for step-7a.sh`, and document them in `scripts/test-lint-foreground-markers.md`.
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/test-lint-foreground-markers.sh:526-539` — The new `step-7a.sh` branch in `scripts/lint-foreground-markers.sh:349-361` is only covered by a single clean-path fixture (case 23). Unlike background denylist scripts (cases 2, 3, 5, 6, 19 in `scripts/test-lint-foreground-markers.sh:109-216`), there are no harness cases asserting violations for a missing foreground banner, missing `# Foreground required: see BASH_AUTHORING.md §4` comment, or a fence that sets `run_in_background: true` alongside `step-7a.sh`. A regression in `foreground_banner_ok_in_window`, `foreground_comment_ok_before_anchor_idx`, or the `has_rb` guard would pass `make test-lint-foreground-markers` and `make lint`. **Suggested fix:** Add three negative fixtures (mirror cases 2/3/6 semantics) that expect `missing foreground-required banner for step-7a.sh`, `missing foreground-required comment for step-7a.sh`, and `foreground-only invocation must not set run_in_background: true for step-7a.sh`, and document them in `scripts/test-lint-foreground-markers.md`.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/lint-foreground-markers.sh:354` — `foreground_comment_ok_before_anchor_idx` is passed `$merge_start_phy` (1-based index of the first physical fence line of a merged invocation), which matches the background `comment_ok_before_anchor_idx` call at `scripts/lint-foreground-markers.sh:374`. Index arithmetic (`start = anchor_idx - 5`, loop `i < anchor_idx`, array access `FG_FENCE_LINES[i - 1]`) is consistent with the background variant; no `merge_start_phy` vs `abs_anchor` mismatch was found for the step-7a path.
- **Suggested revision**: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:1418-1431` — The live Step 7a fence places the foreground comment five in-fence lines above the `step-7a.sh` anchor (after rehydration prelude), so the current SKILL.md satisfies the new linter for production paths.
- **Suggested revision**: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **architecture** `BASH_AUTHORING.md:50-75` and `scripts/lint-foreground-markers.md:7-19` — Foreground marker text in SKILL.md fences points at “BASH_AUTHORING.md §4”, but §4 still normatively documents only the background+monitor pair; the sibling linter doc also describes a single foreground contract for all denylisted scripts even though the implementation keeps dual contracts (background default, foreground only for `step-7a.sh`). These drifts predate or sit outside the step-7a harness edits and are not introduced solely by the new branch logic.
- **Suggested revision**: Address the concern above.


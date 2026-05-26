### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:328-370
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 7a token/timing ledger marks were removed from generate-code-flow-diagram.sh but not added to step-7a.sh despite plan phase 3 and step-7a.md invariants. /implement runs lose the Step 7a timing/token bucket in reports; classifier-skip paths never record diagram phase boundaries. Add best-effort token-ledger.sh and timing-ledger.sh marks in step-7a.sh before classifier/diagram work; keep generator free of duplicate marks; assert in test-step-7a.sh.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Structural harness still pins Step 7a timing mark inside generate-code-flow-diagram.sh after marks moved out. make test-implement-structure fails on this branch while make test-step-7a can pass. Repoint grep to step-7a.sh (and token-ledger if desired) instead of generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/test-step-7a.md:9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-step-7a.md misdocuments diagram-rejected as failed+warning; harness uses STATUS=skipped and no warning. Contributors “fix” working tests to match stale docs. Update test-step-7a.md to match test-step-7a.sh stub behavior (skipped status, no upsert, no warning).
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/step-7a.md:34-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Exit-code docs claim only 0/2 but script exits 1/3 on rebase conflict/failure. Readers assume flush always ran when helper exited non-zero for rebase. Document rebase non-zero exits and that pre-bump flush is skipped on those paths.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:136-225
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large inline run_log_flush duplicates former SKILL fence without a reusable helper. Future batch-list changes require editing a 400-line orchestrator and risk drift vs refresh-run-logs.sh. Add maintainer comment referencing contract; consider pre-bump-flush.sh only if a second caller appears.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/scripts/step-7a.sh:401
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] set -e enabled after rebase conflicts with script-wide best-effort error policy. A future flush line without || true could abort before emit_tail on benign failure. Remove set -e after rebase or wrap run_log_flush in consistent set +e blocks.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:367-369
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Broad SKIP_REASON glob may suppress upsert on non-sanitizer failures containing reject. Hypothetical helper-error text with reject substring skips larch:diagrams upsert incorrectly. Match explicit sanitizer REASON_TOKEN values from sanitize-mermaid-fragment.sh when editing this logic.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/scripts/step-7a.sh:396-405
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Rebase probe stdout is captured and cat'd to FD1; contract KVs are emitted on FD3 under lib-quiet. Orchestrator parsing Bash stdout for REBASE_OUTCOME misses 7a.r conflicts and may skip Conflict Resolution. Replay probe output with cat >&3 or run probe without redirect / with LARCH_QUIET_DISABLE=1 for that call.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Structure test still requires Step 7a timing mark in generate-code-flow-diagram.sh after marks were removed. make lint fails test-implement-structure on this branch. Restore marks in step-7a.sh and update the test pin, or update the assertion with documented intent.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/step-7a.sh:327-333
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 7a token/timing ledger marks are absent despite plan and step-7a.md invariants. Classifier-skip and consolidated paths omit Step 7a from timing/token reports. Add best-effort marks at step-7a.sh entry; do not duplicate inside generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/test-step-7a.sh:6
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Harness disables quiet so FD3/nested rebase propagation bugs are not exercised. make test-step-7a passes while live implement loses REBASE_OUTCOME on the parsed stream. Add a quiet-enabled case asserting REBASE_OUTCOME appears in combined output.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/implement/scripts/step-7a.sh:401-408
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] set -e after successful rebase can abort before emit_tail on unexpected flush errors. Partial KV tail and wrong exit code if an unguarded command fails inside run_log_flush. Avoid set -e through flush or guard run_log_flush with set +e.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/implement/scripts/step-7a.sh:332
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Skip breadcrumb uses printf to quiet log not contract FD. Operators do not see small-non-runtime skip line in tool output. Use emit or emit_breadcrumb with LARCH_QUIET_BREADCRUMBS.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-implement-structure.sh:264-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 7a timing-ledger mark was removed from generate-code-flow-diagram.sh and is not in step-7a.sh but the structural harness still requires it in generate-code-flow-diagram.sh. make lint runs test-implement-structure in shard-14 and fails with generate-code-flow-diagram.sh must contain Step 7a timing-ledger mark blocking merge. Restore Step 7a token/timing marks in step-7a.sh and repoint test-implement-structure.sh to grep step-7a.sh instead of generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/scripts/step-7a.sh:328-370
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required Step 7a token/timing ledger marks are missing from the consolidated helper after round 1 removed them. /implement runs that skip diagram generation never record Step 7a in token/timing reports and diverge from the plan acceptance list. Add token-ledger.sh and timing-ledger.sh mark Step 7a — code flow diagram before the classifier and assert the calls in test-step-7a.sh.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/test-step-7a.md:9
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] test-step-7a.md case 3 claims DIAGRAM_STATUS=failed and a warning but the harness expects skipped with no warning. Maintainers following the md contract will write wrong assertions or miss regressions in sanitizer handling. Update test-step-7a.md to document skipped status no warning and suppressed upsert matching test-step-7a.sh diagram-rejected.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/step-7a.sh:348-369
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Sanitizer rejection suppresses larch:diagrams upsert unlike main which always posted a placeholder comment. Tracking issues can keep a stale diagrams comment after sanitizer rejection while operators expect refreshed placeholder text. Confirm intended behavior; if parity required post placeholder on sanitizer rejection and add a harness assertion for upsert content.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/scripts/test-step-7a.sh:427-444
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness implements 12 cases but test-step-7a.md documents only 10. Contract readers miss generator-crash rebase-conflict and flush-failure-no-logs-commit coverage. Extend test-step-7a.md to list all harness cases including the three extras.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Argv handling**: `--implement-tmpdir` must be absolute; unknown flags bail with `STEP_7A_BAIL_REASON=argv`. `ISSUE_NUMBER` is still validated downstream by `tracking-issue-summary.sh` (`*[!0-9]*` rejection).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv handling**: `--implement-tmpdir` must be absolute; unknown flags bail with `STEP_7A_BAIL_REASON=argv`. `ISSUE_NUMBER` is still validated downstream by `tracking-issue-summary.sh` (`*[!0-9]*` rejection).
- **Suggested revision**: Address the concern above.

### FINDING_20: **Child invocation**: Helpers are invoked via quoted paths under `$PLUGIN_ROOT`; no `eval`, unquoted expansion of untrusted data, or dynamic command assembly beyond the pre-existing `bash -lc` redact one-liner (carried from main’s pre-bump flush).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Child invocation**: Helpers are invoked via quoted paths under `$PLUGIN_ROOT`; no `eval`, unquoted expansion of untrusted data, or dynamic command assembly beyond the pre-existing `bash -lc` redact one-liner (carried from main’s pre-bump flush).
- **Suggested revision**: Address the concern above.

### FINDING_21: **Diagram publishing**: Code-flow content only reaches `summary-diagrams.md` after `generate-code-flow-diagram.sh` + sanitizer promotion, or as fixed placeholders. Sanitizer rejection now suppresses the GitHub upsert (`COMMENT_UPSERT_SKIP`), which is stricter than main’s SKILL.md behavior and reduces risk of posting diagram payloads when generation is rejected.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Diagram publishing**: Code-flow content only reaches `summary-diagrams.md` after `generate-code-flow-diagram.sh` + sanitizer promotion, or as fixed placeholders. Sanitizer rejection now suppresses the GitHub upsert (`COMMENT_UPSERT_SKIP`), which is stricter than main’s SKILL.md behavior and reduces risk of posting diagram payloads when generation is rejected.
- **Suggested revision**: Address the concern above.

### FINDING_22: **Failure logging**: Generation failures go through `append-tool-failure.sh --redact`; upsert failures use the same pattern.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Failure logging**: Generation failures go through `append-tool-failure.sh --redact`; upsert failures use the same pattern.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Lint hardening**: `step-7a.sh` denylist + foreground-marker checks block background execution of this orchestrator (parse-only linter; no fence `eval`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Lint hardening**: `step-7a.sh` denylist + foreground-marker checks block background execution of this orchestrator (parse-only linter; no fence `eval`).
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/step-7a.sh:105-106` — `ARCHITECTURE_DIAGRAM_FILE` is still read with only `-f` gating and `cat`, then published (after `redact-secrets.sh` in `tracking-issue-summary.sh`). A same-UID writer that poisons the env var could exfiltrate arbitrary local file bytes into a tracking-issue comment. This matches pre-main SKILL.md Step 7a; the diff moves logic, not the gate. **Suggested fix:** confine reads to the session/design tmpdir (canonical path under `$IMPLEMENT_TMPDIR` or manifest) and run `sanitize-mermaid-fragment.sh` on architecture content before upsert, matching `ship-pr.sh`’s PR-body path.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/implement/scripts/step-7a.sh:295-300` — `LARCH_CLAUDE_PLUGIN_ROOT` from `session-env.sh` can repoint `$PLUGIN_ROOT` to an alternate tree before sourcing helpers. Same trust model as other `/implement` rehydration preludes (session artifacts are operator-account data, not a hostile-UID boundary). **Suggested fix:** only accept plugin roots under the known install path or validate against `realpath` + allowlist before `source`/exec.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **architecture** `skills/implement/references/pr-body-template.md:21-27` vs `step-7a.sh:103-116` — PR creation sanitizes diagram files; `larch:diagrams` composition does not re-sanitize architecture (and never did on main). Pre-existing inconsistency, not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: skills/implement/scripts/step-7a.sh:397-405
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Nested rebase-checkpoint-probe stdout is captured to a file and cat'd to the quiet log instead of FD 3. On a quiet /implement Step 7a call the orchestrator parses combined Bash stdout for REBASE_OUTCOME and CONFLICT_FILES per skills/implement/SKILL.md:130-134 but only receives emit_tail keys; rebase KVs stay in the quiet log so conflict macro routing and CONFLICT_FILES parsing can fail or fall back to git diff heuristics. Re-emit each KEY=VALUE line from rebase_out via emit_kv on the parent contract stream; remove cat-to-log as the sole relay.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/implement/scripts/test-step-7a.sh:6
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] test-step-7a runs with LARCH_QUIET_DISABLE=1 so nested probe KVs appear on captured stdout. CI passes rebase ordering and REBASE_OUTCOME assertions while production quiet mode hides those lines from the tool transcript. Add quiet-on regression cases or FD-3-only capture that fails if rebase KVs are not re-emitted.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/implement/scripts/step-7a.sh:348-352
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] STATUS=skipped from generate-code-flow-diagram sets COMMENT_UPSERT_SKIP and skips tracking-issue upsert. main always upserted larch:diagrams with Code flow diagram not available on sanitizer rejection; merged runs can leave stale diagram comments and violate byte-identical acceptance. Restore always-upsert with placeholder or document and test the intentional skip-upsert policy explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/implement/scripts/step-7a.sh:403-405
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Early exit on rebase failure emits emit_tail without running run_log_flush. After exit 1/3 from step-7a LOG_FLUSH_STATUS is empty while SKILL.md:1434 references it; operators and any parser cannot distinguish skipped flush vs ok vs degraded. Set an explicit LOG_FLUSH_STATUS on the rebase-failure path before emit_tail and document it in step-7a.md.
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: skills/implement/scripts/step-7a.md:28
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sibling doc claims probe KV pass-through but implementation captures to a file. Readers assume macro routing works via FD 3 inheritance; actual behavior depends on quiet log unless script is fixed. Update step-7a.md to describe re-emit relay or fix step-7a.sh to match the doc.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/implement/scripts/step-7a.sh:367-369
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Broad gen_skip_reason glob *sanitiz*|*reject* can suppress upsert on failed paths. A failed generation with SKIP_REASON containing reject as substring could skip upsert despite non-sanitizer failure semantics. Match explicit REASON_TOKEN values from sanitize-mermaid-fragment.sh or sanitizer-rejected only.
- **Suggested revision**: Address the concern above.

### FINDING_33: code-quality: skills/implement/scripts/step-7a.sh:358
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inconsistent append-tool-failure site labels 7a vs step-7a. execution-issues.md entries from the same helper are harder to grep and correlate in run logs. Standardize site to step-7a everywhere in step-7a.sh.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: skills/implement/scripts/step-7a.sh:328-333
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 7a token/timing ledger marks were removed from both step-7a.sh and generate-code-flow-diagram.sh in round 1 with no replacement. Timing/token reports lose the Step 7a boundary anchor; acceptance and step-7a.md invariants requiring those marks are unmet. Re-add token-ledger.sh and timing-ledger.sh mark calls for Step 7a in step-7a.sh after rehydration; assert in test-step-7a.sh.
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: skills/implement/scripts/step-7a.md:30-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Exit-code documentation omits rebase-probe propagation; behavior matches SKILL.md but not plan phase 12 exit-0 rule. Orchestrator/macro docs disagree with implementation plan; operators reading only step-7a.md mis-handle rebase RC and flush skip. Update step-7a.md exit table and plan phase 12 to match propagate-RC + conditional flush, or change step-7a.sh to exit 0 per original plan.
- **Suggested revision**: Address the concern above.

### FINDING_36: correctness: skills/implement/scripts/step-7a.sh:401
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] set -e is enabled after rebase despite plan no -e bootstrap. Unexpected failure during pre-bump flush could exit before emit_tail/KV tail. Remove post-rebase set -e; keep set +e through flush like flush-execution-issues.sh pattern.
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: skills/implement/scripts/test-step-7a.md:9
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] test-step-7a.md case 3 describes failed+warning; harness tests skipped without warning. Doc readers expect wrong DIAGRAM_STATUS and Warnings behavior vs CI harness. Align test-step-7a.md with harness or add explicit failed+sanitizer-rejected stub case.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:404-405
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] REBASE_OUTCOME failure path emits tail without LOG_FLUSH_STATUS. KV consumers may see empty LOG_FLUSH_STATUS when flush was intentionally skipped. Document or set explicit skipped-rebase LOG_FLUSH_STATUS on early exit.
- **Suggested revision**: Address the concern above.

### FINDING_39: **correctness** `skills/implement/scripts/step-7a.sh:397-406` — With `larch_quiet_init` active, contract KVs from `rebase-checkpoint-probe.sh` are emitted on the child’s FD 3 (bound to the redirect target when stdout is `>"$rebase_out"`), but `cat "$rebase_out"` writes to FD 1, which is the quiet log—not the caller-visible contract stream. `skills/implement/SKILL.md:1434` and `## Rebase Checkpoint Macro` (`skills/implement/SKILL.md:129-134`) instruct the orchestrator to parse `REBASE_OUTCOME`, `CONFLICT_FILES`, and phantom tail KVs from the combined Bash output; in production those lines land in the quiet log while only `emit_tail` KVs reach FD 3, so macro routing (conflict resolution, bail on `failed`, skip markers) can silently miss the probe envelope. The offline harness masks this because `test-step-7a.sh:6` sets `LARCH_QUIET_DISABLE=1`, where `emit_kv` falls back to stdout and command-substitution capture works. **Suggested fix:** Relay captured probe lines to the contract stream explicitly, e.g. `while IFS= read -r line; do [ -n "$line" ] && emit "$line"; done <"$rebase_out"` (or `cat "$rebase_out" >&3` when `LARCH_QUIET_PID=$$`), matching the file-capture pattern already used for `generate-code-flow-diagram.sh` (`skills/implement/scripts/step-7a.sh:334-341`) and `tracking-issue-summary.sh` (`skills/implement/scripts/step-7a.sh:375-385`); add a harness case with quiet enabled (no `LARCH_QUIET_DISABLE`) asserting `REBASE_OUTCOME=` appears on FD 3 / captured contract output.
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:397-406` — With `larch_quiet_init` active, contract KVs from `rebase-checkpoint-probe.sh` are emitted on the child’s FD 3 (bound to the redirect target when stdout is `>"$rebase_out"`), but `cat "$rebase_out"` writes to FD 1, which is the quiet log—not the caller-visible contract stream. `skills/implement/SKILL.md:1434` and `## Rebase Checkpoint Macro` (`skills/implement/SKILL.md:129-134`) instruct the orchestrator to parse `REBASE_OUTCOME`, `CONFLICT_FILES`, and phantom tail KVs from the combined Bash output; in production those lines land in the quiet log while only `emit_tail` KVs reach FD 3, so macro routing (conflict resolution, bail on `failed`, skip markers) can silently miss the probe envelope. The offline harness masks this because `test-step-7a.sh:6` sets `LARCH_QUIET_DISABLE=1`, where `emit_kv` falls back to stdout and command-substitution capture works. **Suggested fix:** Relay captured probe lines to the contract stream explicitly, e.g. `while IFS= read -r line; do [ -n "$line" ] && emit "$line"; done <"$rebase_out"` (or `cat "$rebase_out" >&3` when `LARCH_QUIET_PID=$$`), matching the file-capture pattern already used for `generate-code-flow-diagram.sh` (`skills/implement/scripts/step-7a.sh:334-341`) and `tracking-issue-summary.sh` (`skills/implement/scripts/step-7a.sh:375-385`); add a harness case with quiet enabled (no `LARCH_QUIET_DISABLE`) asserting `REBASE_OUTCOME=` appears on FD 3 / captured contract output.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `skills/implement/scripts/step-7a.sh:327-332` — The consolidated helper never calls `token-ledger.sh mark "Step 7a — code flow diagram"` / `timing-ledger.sh mark "Step 7a — code flow diagram"`. On `main`, those marks lived in `skills/implement/scripts/generate-code-flow-diagram.sh:40-41`; this branch removes them from the generator (`diff` hunk at `generate-code-flow-diagram.sh`) but does not re-home them in `step-7a.sh` (round-1 commit `0defd491` deleted the only in-helper marks). Pre-bump reports still get the Step 8 marks inside `run_log_flush` (`skills/implement/scripts/step-7a.sh:140-141`), but the Step 7a diagram window disappears from ledgers, breaking timing/token slicing for diagram generation. **Suggested fix:** Restore both marks near the start of the diagram phase in `step-7a.sh` (after session rehydration, before `is_small_non_runtime_change` / `generate-code-flow-diagram.sh`), with `|| true`, and assert their invocation order in `test-step-7a.sh`.
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:327-332` — The consolidated helper never calls `token-ledger.sh mark "Step 7a — code flow diagram"` / `timing-ledger.sh mark "Step 7a — code flow diagram"`. On `main`, those marks lived in `skills/implement/scripts/generate-code-flow-diagram.sh:40-41`; this branch removes them from the generator (`diff` hunk at `generate-code-flow-diagram.sh`) but does not re-home them in `step-7a.sh` (round-1 commit `0defd491` deleted the only in-helper marks). Pre-bump reports still get the Step 8 marks inside `run_log_flush` (`skills/implement/scripts/step-7a.sh:140-141`), but the Step 7a diagram window disappears from ledgers, breaking timing/token slicing for diagram generation. **Suggested fix:** Restore both marks near the start of the diagram phase in `step-7a.sh` (after session rehydration, before `is_small_non_runtime_change` / `generate-code-flow-diagram.sh`), with `|| true`, and assert their invocation order in `test-step-7a.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] **`set -e` at `skills/implement/scripts/step-7a.sh:401`:** It is re-enabled only for `cat "$rebase_out"` and the `rebase_rc` gate; `run_log_flush` immediately executes `set +e` at `skills/implement/scripts/step-7a.sh:144`, so flush helpers are not running under errexit. The duplicate `set +e` pairs in `run_larch_log_write` (`skills/implement/scripts/step-7a.sh:122-130`) are redundant, not harmful. Residual risk is only `cat` failing before `emit_tail` on the success path (missing capture file).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **`set -e` at `skills/implement/scripts/step-7a.sh:401`:** It is re-enabled only for `cat "$rebase_out"` and the `rebase_rc` gate; `run_log_flush` immediately executes `set +e` at `skills/implement/scripts/step-7a.sh:144`, so flush helpers are not running under errexit. The duplicate `set +e` pairs in `run_larch_log_write` (`skills/implement/scripts/step-7a.sh:122-130`) are redundant, not harmful. Residual risk is only `cat` failing before `emit_tail` on the success path (missing capture file).
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] **`capture-session-transcript.sh` rc handling (`skills/implement/scripts/step-7a.sh:186-191`):** That helper always `exit 0` (`scripts/capture-session-transcript.sh`), so the `LOG_FLUSH_STATUS=degraded` branch for non-zero rc is unreachable; behavior matches pre-consolidation SKILL semantics (status via execution-issues append + post-transcript flush).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **`capture-session-transcript.sh` rc handling (`skills/implement/scripts/step-7a.sh:186-191`):** That helper always `exit 0` (`scripts/capture-session-transcript.sh`), so the `LOG_FLUSH_STATUS=degraded` branch for non-zero rc is unreachable; behavior matches pre-consolidation SKILL semantics (status via execution-issues append + post-transcript flush).
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] **Sanitizer upsert skip vs `main`:** Skipping `larch:diagrams` upsert on `STATUS=skipped` / sanitizer-shaped `SKIP_REASON` is an intentional plan change, not a byte-identical carryover from `main` (which always upserted when `ISSUE_NUMBER` was set).
- **Reviewer**: dyn-bash-fd-propagation-output.txt
- **Concern**: - **Sanitizer upsert skip vs `main`:** Skipping `larch:diagrams` upsert on `STATUS=skipped` / sanitizer-shaped `SKIP_REASON` is an intentional plan change, not a byte-identical carryover from `main` (which always upserted when `ISSUE_NUMBER` was set).
- **Suggested revision**: Address the concern above.

### FINDING_44: **correctness** `skills/implement/scripts/step-7a.sh:348-369` — Sanitizer upsert suppression does not use the documented `SKIP_REASON` keyword gate for real rejections. `generate-code-flow-diagram.sh` emits `STATUS=skipped` with tokens such as `pipe-in-node-label` (from `scripts/sanitize-mermaid-fragment.sh:201`), which do not match `*sanitiz*|*reject*` at `step-7a.sh:367-368`. Suppression works only because the `skipped` branch sets `COMMENT_UPSERT_SKIP=true` unconditionally (`step-7a.sh:352`), so any future non-sanitizer `STATUS=skipped` would also suppress the `larch:diagrams` upsert, contrary to Round 1 Decision 2 (“ONLY skipped when the Mermaid sanitizer emits a rejection token”). **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` case; set it only when `SKIP_REASON` matches sanitizer tokens (e.g. explicit allowlist of `REASON_TOKEN` values from `sanitize-mermaid-fragment.sh`, or a `sanitizer-` / `pipe-in-node-label` prefix convention). Keep `STATUS=skipped` mapping for `DIAGRAM_STATUS` and placeholders.
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:348-369` — Sanitizer upsert suppression does not use the documented `SKIP_REASON` keyword gate for real rejections. `generate-code-flow-diagram.sh` emits `STATUS=skipped` with tokens such as `pipe-in-node-label` (from `scripts/sanitize-mermaid-fragment.sh:201`), which do not match `*sanitiz*|*reject*` at `step-7a.sh:367-368`. Suppression works only because the `skipped` branch sets `COMMENT_UPSERT_SKIP=true` unconditionally (`step-7a.sh:352`), so any future non-sanitizer `STATUS=skipped` would also suppress the `larch:diagrams` upsert, contrary to Round 1 Decision 2 (“ONLY skipped when the Mermaid sanitizer emits a rejection token”). **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` case; set it only when `SKIP_REASON` matches sanitizer tokens (e.g. explicit allowlist of `REASON_TOKEN` values from `sanitize-mermaid-fragment.sh`, or a `sanitizer-` / `pipe-in-node-label` prefix convention). Keep `STATUS=skipped` mapping for `DIAGRAM_STATUS` and placeholders.
- **Suggested revision**: Address the concern above.

### FINDING_45: **correctness** `skills/implement/scripts/test-step-7a.sh:346-356` — The `diagram-rejected` case passes for the wrong mechanism: the stub emits `STATUS=skipped` / `SKIP_REASON=pipe-in-node-label` (`test-step-7a.sh:122-124`), so the test never exercises the `*sanitiz*|*reject*` branch at `step-7a.sh:367-368`. If upsert skip relied on keywords alone, this case would still post a comment. The case also asserts `DIAGRAM_STATUS=skipped` and no `### Warnings`, while `test-step-7a.md:9` and the plan’s `diagram-rejected` spec expect `DIAGRAM_STATUS=failed` and a warning on sanitizer rejection. **Suggested fix:** Align the stub with production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) or with the plan (`STATUS=failed`, `SKIP_REASON=sanitizer-rejected`); assert upsert skip via an allowlisted `SKIP_REASON` after fixing `step-7a.sh`; add a negative case where `STATUS=skipped` with a non-sanitizer `SKIP_REASON` still upserts.
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.sh:346-356` — The `diagram-rejected` case passes for the wrong mechanism: the stub emits `STATUS=skipped` / `SKIP_REASON=pipe-in-node-label` (`test-step-7a.sh:122-124`), so the test never exercises the `*sanitiz*|*reject*` branch at `step-7a.sh:367-368`. If upsert skip relied on keywords alone, this case would still post a comment. The case also asserts `DIAGRAM_STATUS=skipped` and no `### Warnings`, while `test-step-7a.md:9` and the plan’s `diagram-rejected` spec expect `DIAGRAM_STATUS=failed` and a warning on sanitizer rejection. **Suggested fix:** Align the stub with production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) or with the plan (`STATUS=failed`, `SKIP_REASON=sanitizer-rejected`); assert upsert skip via an allowlisted `SKIP_REASON` after fixing `step-7a.sh`; add a negative case where `STATUS=skipped` with a non-sanitizer `SKIP_REASON` still upserts.
- **Suggested revision**: Address the concern above.

### FINDING_46: **correctness** `skills/implement/scripts/step-7a.sh:326-370` — Step 7a `token-ledger.sh` / `timing-ledger.sh` marks were removed from `generate-code-flow-diagram.sh` (diff removes `mark "Step 7a — code flow diagram"` at former lines 1073–1074) but are not re-added in `step-7a.sh`, despite plan Phase 3 and `step-7a.md:43` listing “token/timing marks” in phase order. Pre-bump flush still marks Step 8 (`step-7a.sh:140-141`), so timing/token reports lose the Step 7a boundary. **Suggested fix:** After session rehydration and before the classifier, add best-effort `"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 7a — code flow diagram"` and the matching `timing-ledger.sh` call; extend `test-step-7a.sh` to assert those argv lines in `calls.log`.
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:326-370` — Step 7a `token-ledger.sh` / `timing-ledger.sh` marks were removed from `generate-code-flow-diagram.sh` (diff removes `mark "Step 7a — code flow diagram"` at former lines 1073–1074) but are not re-added in `step-7a.sh`, despite plan Phase 3 and `step-7a.md:43` listing “token/timing marks” in phase order. Pre-bump flush still marks Step 8 (`step-7a.sh:140-141`), so timing/token reports lose the Step 7a boundary. **Suggested fix:** After session rehydration and before the classifier, add best-effort `"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 7a — code flow diagram"` and the matching `timing-ledger.sh` call; extend `test-step-7a.sh` to assert those argv lines in `calls.log`.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:403-406` — On rebase probe non-zero exit, the helper `exit "$rebase_rc"` before `run_log_flush`, so pre-bump flush does not run on conflict. `test-step-7a.sh:437-444` encodes that behavior; it may be intentional for macro routing but diverges from plan text saying the helper exits 0 except argv errors.
- **Suggested revision**: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] On `main`, `skills/implement/SKILL.md` always upserted `larch:diagrams` when `ISSUE_NUMBER` was set, including after sanitizer rejection (`STATUS=skipped` with a placeholder). This branch suppresses upsert for all `STATUS=skipped` outcomes; that matches the issue plan but conflicts with the stated “byte-identical `larch:diagrams`” acceptance criterion.
- **Reviewer**: dyn-stub-model-accuracy-output.txt
- **Concern**: - On `main`, `skills/implement/SKILL.md` always upserted `larch:diagrams` when `ISSUE_NUMBER` was set, including after sanitizer rejection (`STATUS=skipped` with a placeholder). This branch suppresses upsert for all `STATUS=skipped` outcomes; that matches the issue plan but conflicts with the stated “byte-identical `larch:diagrams`” acceptance criterion.
- **Suggested revision**: Address the concern above.


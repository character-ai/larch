### FINDING_1: code-quality: skills/design/references/flags.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --partition bullet claims hard triggers route to Split-path automatically. Hard plans still show AskUserQuestion Split/Cancel before Split-path; only partition-flag skips the prompt. Reword: hard → Split/Cancel prompt first; partition → direct Split-path when HARD_TRIGGER_FIRED=false.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/design/references/approval-gates.md:108
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Gate B prose still documents removed soft Step 2b.5 Continue path. After Gate B re-emit an orchestrator loading approval-gates may offer Continue with current scope on plans that no longer have a soft branch contradicting SKILL.md Step 2b.5. Rewrite Gate B Step 2b.5 paragraph: hard AskUserQuestion Split/Cancel only partition without hard routes direct to Split-path otherwise under-threshold breadcrumb.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: README.md:61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stale --partition prose still describes a Step 2b.5 partition prompt path. Users reading README expect an AskUserQuestion soft/partition prompt; runtime now jumps straight to Split-path without Continue. Rewrite the README /design row to say --partition routes directly to the decomposition panel when no hard trigger fires.
- **Suggested revision**: Address the concern above.

### FINDING_4: `6624f0e5` — Remove FILES_COUNT and soft-trigger machinery from `/design` plan-size check (8 files; functional change)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `6624f0e5` — Remove FILES_COUNT and soft-trigger machinery from `/design` plan-size check (8 files; functional change)
- **Suggested revision**: Address the concern above.

### FINDING_5: `5aca7759` — `chore(larch-logs)` design run flush (excluded per review scope rules)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `5aca7759` — `chore(larch-logs)` design run flush (excluded per review scope rules) Security review focuses on commit `6624f0e5`. ## Summary This change removes soft plan-size metrics (`FILES_COUNT`, `SOFT_TRIGGER_FIRED`, soft thresholds) from `check-plan-size.sh`, drops orchestrator-only semantic-soft branching in Step 2b.5, and routes `--partition` / `partition_requested` directly to Split-path without a Step 2b.5 `AskUserQuestion`. The shell helper still only reads a plan file with fixed `awk`/`grep` patterns and emits fixed KV tokens; no new shell interpolation, deserialization, network, or secret-handling paths were added.
- **Suggested revision**: Address the concern above.

### FINDING_6: **Plan-content influence reduced:** Removing `SEMANTIC_SOFT_ESTIMATE` and mechanical soft triggers means plan text can no longer nudge Step 2b.5 toward a sprawl prompt via file-count or orchestrator discretion at this step. That is a security-positive workflow hardening, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Plan-content influence reduced:** Removing `SEMANTIC_SOFT_ESTIMATE` and mechanical soft triggers means plan text can no longer nudge Step 2b.5 toward a sprawl prompt via file-count or orchestrator discretion at this step. That is a security-positive workflow hardening, not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_7: **`--partition` auto-Split-path:** The new partition branch (`skills/design/SKILL.md` item 5) skips the former soft-branch `AskUserQuestion`, but `partition_requested` is still sourced only from argv → `write-run-params.sh` / jq merge into `$DESIGN_TMPDIR/run-params.json`, not from plan body parsing. Hard triggers still require Split/Cancel confirmation. Residual risk is limited to a session where an attacker can already pass `-p` or tamper with `run-params.json` inside `DESIGN_TMPDIR`—the same trust boundary that existed before this diff, now with one fewer confirmation gate when `-p` was explicitly chosen.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--partition` auto-Split-path:** The new partition branch (`skills/design/SKILL.md` item 5) skips the former soft-branch `AskUserQuestion`, but `partition_requested` is still sourced only from argv → `write-run-params.sh` / jq merge into `$DESIGN_TMPDIR/run-params.json`, not from plan body parsing. Hard triggers still require Split/Cancel confirmation. Residual risk is limited to a session where an attacker can already pass `-p` or tamper with `run-params.json` inside `DESIGN_TMPDIR`—the same trust boundary that existed before this diff, now with one fewer confirmation gate when `-p` was explicitly chosen.
- **Suggested revision**: Address the concern above.

### FINDING_8: **`check-plan-size.sh`:** `--plan-file` / `$DESIGN_TMPDIR/plan.txt` arbitrary read is unchanged from main; not introduced by this branch.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`check-plan-size.sh`:** `--plan-file` / `$DESIGN_TMPDIR/plan.txt` arbitrary read is unchanged from main; not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/design/scripts/check-plan-size.sh` — `--plan-file` accepts any readable path without canonicalization under a design root; a caller that passes attacker-controlled paths could use the helper for arbitrary file reads (line counts / trailer validation only). Pre-existing; unchanged by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `skills/design/SKILL.md:221-233` — `partition_requested` persistence uses jq OR-merge on `run-params.json` in `DESIGN_TMPDIR`. Writable tmpdir tampering could force Split-path on later Step 2b.5 re-entries; idempotent decompose sentinels mitigate repeat filing but not initial dispatch cost. Pre-existing persistence pattern; partition branch now auto-enters Split-path when the flag is true.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/design/references/approval-gates.md:108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Gate B doc still describes removed soft Continue path and stub Split-path. After Gate B re-emit orchestrator may offer Continue with current scope or treat Split as failing stub though SKILL.md removed soft branch. Rewrite Gate B Step 2b.5 subsection to hard AskUserQuestion partition direct Split-path and current exit semantics.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/design/references/approval-gates.md:108
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Gate B still documents removed Step 2b.5 soft Split/Continue behavior and outdated Split-path stub semantics. After Gate B plan revision an agent following approval-gates.md may offer or expect Continue on moderate plans though SKILL.md only has hard AskUserQuestion partition direct routing or under-threshold breadcrumb. Rewrite the Gate B Step 2b.5 sentence to match current SKILL.md branches and real decomposition panel outcomes.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: README.md:61
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] README still describes --partition as forcing a partition prompt path. Operators expect an intermediate AskUserQuestion partition prompt that Step 2b.5 no longer performs. Update README /design row to state --partition routes directly to Split-path when no hard trigger per flags.md.
- **Suggested revision**: Address the concern above.


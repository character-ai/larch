# Review Round 3

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 5

## Accepted Findings

### FINDING_11: risk-integration: skills/implement/scripts/write-final-report.sh:345-382
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New bail-time manifest updates lack coverage in skills/implement/scripts/test-write-final-report.sh. A regression in OUTCOME classification, larch-log.sh manifest flags, or hard-fail behavior could ship unnoticed until production bail teardown. Extend test-write-final-report.sh with fixtures asserting steps_ran fields and manifest CLI failure handling.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:198-207 scripts/verify-run-log-completeness.sh:217-220
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Nonempty steps_ran without step9a1 + bail heading branch is untested. Audit and verify could drift or break the partial-manifest edge without CI signal. Add a paired audit + verify fixture covering manifest_steps_ran_nonempty_without_step9a1.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:131-161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] jq failure on manifest.json collapses to steps_ran_obj="{}" so _rf_steps_ran_empty is true Corrupt manifest plus bail-shaped final-summary can make required-file-presence pass while step9a1 artifacts are missing Only treat steps_ran as empty after successful JSON parse; do not use echo "{}" on jq parse failure for bail heuristics
- **Suggested revision**: Address the concern above.


### FINDING_20: **correctness** `skills/implement/scripts/write-final-report.sh:356-358` — Round 2 narrowed the guard for stamping `steps_ran.step9a1=false` to “`run-statistics.md` missing” only, dropping the prior conjunction with missing `oos-issues.ndjson`. That disagrees with the Step 9a.1 bail-time wording in `skills/implement/SKILL.md` (it defines “before Step 9a.1” as no `run-statistics.md` **and** no pre-gate `oos-issues.ndjson` on disk) and with `audit-scan-run.sh`’s `_rf_condition_met` `step9a1` branch, where the empty-`steps_ran` bail shortcut returns “not reached” only when **neither** file exists (`198-203:.claude/skills/audit-runs/scripts/audit-scan-run.sh`). With only `run-statistics.md` absent but `oos-issues.ndjson` present, the audit path still treats `step9a1` as in play and can flag missing `run-statistics.md`, while a manifest carrying `step9a1=false` makes `_rf_steps_ran_false` short-circuit and **suppresses** that required-file failure—so genuinely incomplete post-OOS runs can be misclassified as passing. **Suggested fix:** Reinstate the conjunctive artifact check (only emit `steps_ran.step9a1=false` when both `run-statistics.md` and `oos-issues.ndjson` are absent, unless you deliberately revise the contract and update `audit-scan-run.sh`, `verify-run-log-completeness.sh`, tests, and `SKILL.md` in lockstep).
- **Reviewer**: dyn-manifest-integrity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:356-358` — Round 2 narrowed the guard for stamping `steps_ran.step9a1=false` to “`run-statistics.md` missing” only, dropping the prior conjunction with missing `oos-issues.ndjson`. That disagrees with the Step 9a.1 bail-time wording in `skills/implement/SKILL.md` (it defines “before Step 9a.1” as no `run-statistics.md` **and** no pre-gate `oos-issues.ndjson` on disk) and with `audit-scan-run.sh`’s `_rf_condition_met` `step9a1` branch, where the empty-`steps_ran` bail shortcut returns “not reached” only when **neither** file exists (`198-203:.claude/skills/audit-runs/scripts/audit-scan-run.sh`). With only `run-statistics.md` absent but `oos-issues.ndjson` present, the audit path still treats `step9a1` as in play and can flag missing `run-statistics.md`, while a manifest carrying `step9a1=false` makes `_rf_steps_ran_false` short-circuit and **suppresses** that required-file failure—so genuinely incomplete post-OOS runs can be misclassified as passing. **Suggested fix:** Reinstate the conjunctive artifact check (only emit `steps_ran.step9a1=false` when both `run-statistics.md` and `oos-issues.ndjson` are absent, unless you deliberately revise the contract and update `audit-scan-run.sh`, `verify-run-log-completeness.sh`, tests, and `SKILL.md` in lockstep).
- **Suggested revision**: Address the concern above.



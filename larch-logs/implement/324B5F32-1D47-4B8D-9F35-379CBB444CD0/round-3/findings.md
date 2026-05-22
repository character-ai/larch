### FINDING_1: code-quality: .claude/skills/audit-runs/scripts/audit-scan-run.sh:159-207
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Alternate bail signal from plan (empty steps_ran + missing pr_number) not implemented; only heading suffix + empty object (+ partial-manifest branch). Early-aborted run with empty steps_ran and no terminal-suffix match on the first non-empty final-summary line could still be classified as step9a1-reached in direct mode and falsely fail required-file-presence for missing run-statistics. Add pr_number null/empty probe gated on empty steps_ran with tests, or document the narrowed contract if pr_number is intentionally unused.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:198-207
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bail + nonempty steps_ran without step9a1 returns not-reached for all step9a1-gated rows. A run could miss oos-issues.ndjson while still reporting pass for that row whenever the bail heading matches, run-statistics is absent, and steps_ran lacks step9a1. Decouple skip logic so oos-issues remains enforced when appropriate, or document intentional forgiveness of all step9a1 artifacts on bail-labelled partial manifests.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/verify-run-log-completeness.sh:105-168 vs .claude/skills/audit-runs/scripts/audit-scan-run.sh:143-168
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Audit uses jq/shell while verify uses Python for the same bail predicates, increasing drift risk. Future token or empty-object rule changes need edits in two languages and risk subtle parity bugs. Optionally extract shared shell predicates sourced by both scripts, or keep as-is and rely on mirrored regression tests (already added).
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/implement/scripts/write-final-report.sh:345-382
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Manifest honesty updates are skipped when COMMENT_ONLY is true. Comment-only finalization paths may still emit ambiguous steps_ran for downstream tooling that does not use audit fallbacks. Move manifest updates outside the COMMENT_ONLY guard when safe, or explicitly exempt comment-only runs in SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/verify-run-log-completeness.sh:209-225
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pre-existing step9a1 OR-chain treats final-summary presence as reach signal; this branch was not introduced by the bail fix. N/A Leave unchanged unless redesigning step inference globally.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:200-207 scripts/verify-run-log-completeness.sh:213-219
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Empty steps_ran bail shortcut for step9a1 requires both run-statistics.md and oos-issues.ndjson absent so bailed runs with only oos-issues.ndjson still fail run-statistics.md. steps_ran {} final-summary terminal bail line oos-issues.ndjson present run-statistics.md missing yields required-file-presence fail for run-statistics.md. Extend bail logic or document intentional residual failures.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: plan both
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan required pr_number missing/null as alternate bail signal when steps_ran is empty; code only inspects final-summary first line plus explicit steps_ran and nonempty_without_step9a1. Empty steps_ran corrupted or non-canonical final-summary without bail suffix but pr_number absent may still false-positive run-statistics.md. Add pr_number probe or align plan text with implementation.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/scripts/write-final-report.sh:347-381
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Terminal outcome steps_ran updates are skipped when run_dir/manifest.json is missing. If manifest missing on terminal path run logs stay ambiguous. Comment impossibility or fail create manifest when missing.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: plan
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan names write-manifest.sh as primary touch; fix is in write-final-report.sh. Minor plan vs code name drift. Update plan template to actual bail closure file.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1840-1865
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Tests use jq piped to head -1 for scan JSON lines. Order change could make assertions flaky. Prefer jq -s first match or stable sort if tests ever flake.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/implement/scripts/write-final-report.sh:345-382
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New bail-time manifest updates lack coverage in skills/implement/scripts/test-write-final-report.sh. A regression in OUTCOME classification, larch-log.sh manifest flags, or hard-fail behavior could ship unnoticed until production bail teardown. Extend test-write-final-report.sh with fixtures asserting steps_ran fields and manifest CLI failure handling.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:198-207 scripts/verify-run-log-completeness.sh:217-220
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Nonempty steps_ran without step9a1 + bail heading branch is untested. Audit and verify could drift or break the partial-manifest edge without CI signal. Add a paired audit + verify fixture covering manifest_steps_ran_nonempty_without_step9a1.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: docs/plan vs scripts/run-log-terminal-outcomes.inc.bash
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Feature text mentioned pr_number missing/null as bail signal OR branch; code/tests use final-summary suffix only. Legacy or malformed trees might still false-positive if they do not match heading heuristics. Implement and test pr_number OR or document the narrowed signal set as an explicit closed decision.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] code-quality: scripts/test-verify-run-log-completeness.sh:98-260
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate Test 15 numbering pre-exists outside the new test block. Minor maintainer confusion only. Renumber in an unrelated cleanup if useful.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:148-161 plus scripts/verify-run-log-completeness.sh:127-146
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Required-file gating now consults final-summary first-line suffix when steps_ran is empty. A contributor who can rewrite committed run-log files could add a terminal bail-style first line while omitting run-statistics.md and leaving steps_ran empty, converting an audit completeness failure into a pass without touching manifest honesty fields. Document the trust model (repo-integrity for final-summary) and continue to rely on explicit steps_ran updates from write-final-report for authoritative skips; optionally tighten policy later if logs must be machine-verifiable beyond git trust.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security: skills/implement/scripts/write-final-report.sh:7-9
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Additional source under PLUGIN_ROOT mirrors existing lib-quiet sourcing. No new attack class beyond trusting plugin directory contents. None; keep CLAUDE_PLUGIN_ROOT pointed at the real plugin tree in sensitive environments.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:131-161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] jq failure on manifest.json collapses to steps_ran_obj="{}" so _rf_steps_ran_empty is true Corrupt manifest plus bail-shaped final-summary can make required-file-presence pass while step9a1 artifacts are missing Only treat steps_ran as empty after successful JSON parse; do not use echo "{}" on jq parse failure for bail heuristics
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:159-161;scripts/verify-run-log-completeness.sh:186-216
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Planned bail probe included manifest pr_number missing/null as an alternate bail signal alongside final-summary terminal suffixes; implementation only keys off final-summary + empty steps_ran (plus a separate nonempty-steps_ran-without-step9a1 branch). A run with steps_ran {} and no terminal-suffix match on the first final-summary line but a genuinely pre-PR bail manifest shape implied by the plan would still be classified like the old default-true path for direct step9a1 rows, reviving false positives the plan text tried to close. Narrow and implement pr_number logic with schema guards, or revise the plan to drop that OR and rely on final-summary + explicit steps_ran writes.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] architecture: <TMPDIR>/round-3/diff.txt;local git refs
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff empty and local main equals HEAD while origin/main lags; branch vs main review required substituting origin/main...HEAD. Automated plan-fidelity workflows that only read diff.txt or diff against local main can report no changes when the implement branch is already merged locally. Point the sidecar at the correct ref or regenerate diff.txt from origin/main...HEAD.
- **Suggested revision**: Address the concern above.

### FINDING_20: **correctness** `skills/implement/scripts/write-final-report.sh:356-358` — Round 2 narrowed the guard for stamping `steps_ran.step9a1=false` to “`run-statistics.md` missing” only, dropping the prior conjunction with missing `oos-issues.ndjson`. That disagrees with the Step 9a.1 bail-time wording in `skills/implement/SKILL.md` (it defines “before Step 9a.1” as no `run-statistics.md` **and** no pre-gate `oos-issues.ndjson` on disk) and with `audit-scan-run.sh`’s `_rf_condition_met` `step9a1` branch, where the empty-`steps_ran` bail shortcut returns “not reached” only when **neither** file exists (`198-203:.claude/skills/audit-runs/scripts/audit-scan-run.sh`). With only `run-statistics.md` absent but `oos-issues.ndjson` present, the audit path still treats `step9a1` as in play and can flag missing `run-statistics.md`, while a manifest carrying `step9a1=false` makes `_rf_steps_ran_false` short-circuit and **suppresses** that required-file failure—so genuinely incomplete post-OOS runs can be misclassified as passing. **Suggested fix:** Reinstate the conjunctive artifact check (only emit `steps_ran.step9a1=false` when both `run-statistics.md` and `oos-issues.ndjson` are absent, unless you deliberately revise the contract and update `audit-scan-run.sh`, `verify-run-log-completeness.sh`, tests, and `SKILL.md` in lockstep).
- **Reviewer**: dyn-manifest-integrity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:356-358` — Round 2 narrowed the guard for stamping `steps_ran.step9a1=false` to “`run-statistics.md` missing” only, dropping the prior conjunction with missing `oos-issues.ndjson`. That disagrees with the Step 9a.1 bail-time wording in `skills/implement/SKILL.md` (it defines “before Step 9a.1” as no `run-statistics.md` **and** no pre-gate `oos-issues.ndjson` on disk) and with `audit-scan-run.sh`’s `_rf_condition_met` `step9a1` branch, where the empty-`steps_ran` bail shortcut returns “not reached” only when **neither** file exists (`198-203:.claude/skills/audit-runs/scripts/audit-scan-run.sh`). With only `run-statistics.md` absent but `oos-issues.ndjson` present, the audit path still treats `step9a1` as in play and can flag missing `run-statistics.md`, while a manifest carrying `step9a1=false` makes `_rf_steps_ran_false` short-circuit and **suppresses** that required-file failure—so genuinely incomplete post-OOS runs can be misclassified as passing. **Suggested fix:** Reinstate the conjunctive artifact check (only emit `steps_ran.step9a1=false` when both `run-statistics.md` and `oos-issues.ndjson` are absent, unless you deliberately revise the contract and update `audit-scan-run.sh`, `verify-run-log-completeness.sh`, tests, and `SKILL.md` in lockstep).
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] **`force-merged-externally`** is a `write-final-report.sh` outcome (`135-136:skills/implement/scripts/write-final-report.sh`) but is not listed in `scripts/run-log-terminal-outcomes.inc.bash`; only relevant if such a run can finish with ambiguous `steps_ran` and missing Step 9a.1 artifacts—unlikely, but the shared “three sites in sync” comment in that inc file is worth keeping aligned whenever outcomes change.
- **Reviewer**: dyn-manifest-integrity-output.txt
- **Concern**: - **`force-merged-externally`** is a `write-final-report.sh` outcome (`135-136:skills/implement/scripts/write-final-report.sh`) but is not listed in `scripts/run-log-terminal-outcomes.inc.bash`; only relevant if such a run can finish with ambiguous `steps_ran` and missing Step 9a.1 artifacts—unlikely, but the shared “three sites in sync” comment in that inc file is worth keeping aligned whenever outcomes change.
- **Suggested revision**: Address the concern above.


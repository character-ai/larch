# Review Round 2

- Mode: `diff`
- Accepted findings: 12
- Rejected findings: 0
- Exonerated findings: 9
- Neutral findings: 0

## Accepted Findings

### FINDING_1: code-quality: skills/fix-issue/scripts/find-lock-issue.sh:158-803,.claude/skills/audit-runs/SKILL.md:106,.claude/skills/audit-runs/scripts/test-audit-runs.sh:364-385,.claude/skills/audit-runs/scripts/test-audit-runs.sh:1889-1913,skills/fix-issue/scripts/test-find-lock-issue.sh:938-960,.claude/skills/audit-runs/scripts/test-audit-runs.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Legacy audit-title exclusion path retained and threaded through skill docs, jq, and harnesses despite plan stating no backward-compat and removal of the dedicated guard in favor of has_report_prefix plus audit-report label only. Operators and future edits must maintain parallel regexes (legacy prefix vs new .* Report]) and an extra find-lock predicate forever, duplicating the simplification goal and drifting from the written plan edge-case note. If historical titles are gone, strip legacy helper, second grep branch, jq or branch, fixture 24b, and legacy prose; otherwise update the plan to justify deliberate legacy support.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:230-310;skills/fix-issue/scripts/test-find-lock-issue.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] find-lock-issue maps check-main-sync stdout/exit codes but test-find-lock-issue.sh never exercises blocked/probe-error/unexpected-exit branches. Mis-parsed SYNC_STATUS or wrong umbrella KV emission could block locks or leak locks without harness regression detection. Add sterile-repo fixtures forcing check-main-sync exits 1/2 and assert stdout KV + no lock calls.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/check-main-sync.md:76
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Primary Callers bullet claims find-lock-issue fail-opens probe-error and allows lock acquisition, contradicting line 17 and find-lock-issue.sh. A maintainer or future “consistency” edit could weaken the pre-lock gate to match the wrong doc line, reintroducing silent lock acquisition when main-sync classification failed but origin/main exists. Rewrite the find-lock-issue bullet to describe conditional fail-closed vs fail-open behavior and keep it aligned with find-lock-issue.md and the script.
- **Suggested revision**: Address the concern above.


### FINDING_18: architecture: skills/fix-issue/scripts/find-lock-issue.sh:8180-8257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _emit_dirty_tree_pre_lock_abort now invokes check-main-sync.sh which can git reset --hard origin/main after a clean-tree pass, mixing eligibility probing with destructive repo mutation under a dirty-tree-oriented name. Operator on clean local main with unpushed chore(larch-logs) flush commits ahead of stale origin/main runs find-lock-issue; main is silently rewound to cached origin/main, dropping local-only SHAs without a dedicated confirmation or obvious breadcrumb. Split sync from dirty-tree naming, emit explicit KV on reset, document the destructive branch in fix-issue pre-lock contracts and tests.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:8197-8254
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Successful main auto-reset returns through the same helper as a cleanliness success without an operator-visible reset signal. Downstream steps proceed while branch moved without an auditable KV line, complicating post-mortems when later git operations fail for non-obvious reasons. Emit SYNC_STATUS/reset markers on stdout (KV) and cover with a harness fixture.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/fix-issue/scripts/find-lock-issue.sh:154-163,800
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Legacy audit-title guard reintroduced as has_legacy_run_logs_audit_report_bracket_prefix OR has_report_prefix despite plan calling for sole reliance on has_report_prefix plus label and stating no backward-compat. An operator following only the written plan expects zero secondary title-shape logic after migration; the branch still encodes a parallel legacy matcher and new fixture 24b proves that path. Remove legacy helper and disjunct if plan stands; otherwise amend the plan issue to require legacy exclusion explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_26: architecture: .claude/skills/audit-runs/SKILL.md:106;.claude/skills/audit-runs/scripts/test-audit-runs.sh:598-622;.claude/skills/audit-runs/scripts/test-audit-runs.md:543-544
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Skill and harness document and test a legacy anti-recursion union conflicting with plan edge case no backward-compat. Documentation and tests promise behavior (legacy union) the plan says is unnecessary, confusing future migrations and review checklists. Single-regex documentation and tests matching plan, or update plan with legacy retention rationale and sunset criteria.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:230-257;skills/fix-issue/scripts/find-lock-issue.md:11;.claude/skills/audit-runs/scripts/audit-scan-run.sh;.claude/skills/audit-runs/scans.tsv;CHANGELOG.md;Makefile
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Substantial changes outside the seven-item audit-title plan appear in the same branch diff. A plan-fidelity pass against only the supplied audit-title checklist cannot account for main-sync gating, OOS silent-drop scan, and other merged features. Split PRs or extend the plan so every shipped change maps to an enumerated requirement.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/fix-issue/scripts/find-lock-issue.sh:161-163
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Legacy grep uses prefix ^\[Run Logs Audit Report without anchoring the historical Report-token boundary. A hypothetical title like [Run Logs Audit Reporting ...] is rejected as legacy audit noise even if it were a legitimate tracking issue. Tighten the legacy regex to the historical timestamp form or document the broader exclusion as intentional.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/fix-issue/scripts/find-lock-issue.sh:161-162
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Legacy audit-title grep is a prefix of any word starting with Report (Reporting/Reported/etc.), so /fix-issue can refuse legitimate issues. Issue titled e.g. [Run Logs Audit Reporting] … is classified as report-prefix ineligible though it is not the historical run-logs audit title format. Tighten to the historical shape (e.g. ^\[Run Logs Audit Report[[:space:]]) and mirror in audit-runs tests/SKILL jq/docs.
- **Suggested revision**: Address the concern above.


### FINDING_6: architecture: .claude/skills/audit-runs/SKILL.md:106 plus test-audit-runs.md:20 plus find-lock-issue.sh:159-163
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Docs/plan disagree on whether legacy audit-title handling is still required. Operators read conflicting migration guidance vs the implementation plan edge case. Align SKILL/test prose with the chosen policy; remove legacy docs if code drops legacy matching.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:504-583
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New high-severity oos-silent-drop scan lacks test-audit-runs.sh fixtures and audit-scan-run.md contract text. Registry/case drift or NDJSON shape regressions ship without make lint signal; scan behavior is harder to refactor safely. Add hermetic pass/skip/fail tests and document NDJSON fields in audit-scan-run.md per edit-in-sync checklist.
- **Suggested revision**: Address the concern above.



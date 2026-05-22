### FINDING_1: code-quality: skills/fix-issue/scripts/find-lock-issue.sh:158-803,.claude/skills/audit-runs/SKILL.md:106,.claude/skills/audit-runs/scripts/test-audit-runs.sh:364-385,.claude/skills/audit-runs/scripts/test-audit-runs.sh:1889-1913,skills/fix-issue/scripts/test-find-lock-issue.sh:938-960,.claude/skills/audit-runs/scripts/test-audit-runs.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Legacy audit-title exclusion path retained and threaded through skill docs, jq, and harnesses despite plan stating no backward-compat and removal of the dedicated guard in favor of has_report_prefix plus audit-report label only. Operators and future edits must maintain parallel regexes (legacy prefix vs new .* Report]) and an extra find-lock predicate forever, duplicating the simplification goal and drifting from the written plan edge-case note. If historical titles are gone, strip legacy helper, second grep branch, jq or branch, fixture 24b, and legacy prose; otherwise update the plan to justify deliberate legacy support.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/fix-issue/scripts/find-lock-issue.sh:798-803
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unified error text references the generic [... Report] bracket rule even when only the legacy prefix matcher rejects the title. A maintainer comparing the error to find-lock-issue.md's [... Report] description may conclude the script misfired because the legacy title lacks that bracket-ending shape. Split or reword the error so legacy-shaped run-logs audit titles are described accurately.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/fix-issue/scripts/find-lock-issue.sh:161-163
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Legacy grep uses prefix ^\[Run Logs Audit Report without anchoring the historical Report-token boundary. A hypothetical title like [Run Logs Audit Reporting ...] is rejected as legacy audit noise even if it were a legitimate tracking issue. Tighten the legacy regex to the historical timestamp form or document the broader exclusion as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: Makefile (unrelated commits in same branch range)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Branch bundles additional commits (e.g. #2540 fix, harness list changes) beyond the audit-title rename. Reviewers must spend time filtering unrelated diffs when assessing the audit-title work. Keep future PRs scoped to one logical change or call out the bundle explicitly in the PR description.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/fix-issue/scripts/find-lock-issue.sh:161-162
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Legacy audit-title grep is a prefix of any word starting with Report (Reporting/Reported/etc.), so /fix-issue can refuse legitimate issues. Issue titled e.g. [Run Logs Audit Reporting] … is classified as report-prefix ineligible though it is not the historical run-logs audit title format. Tighten to the historical shape (e.g. ^\[Run Logs Audit Report[[:space:]]) and mirror in audit-runs tests/SKILL jq/docs.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: .claude/skills/audit-runs/SKILL.md:106 plus test-audit-runs.md:20 plus find-lock-issue.sh:159-163
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Docs/plan disagree on whether legacy audit-title handling is still required. Operators read conflicting migration guidance vs the implementation plan edge case. Align SKILL/test prose with the chosen policy; remove legacy docs if code drops legacy matching.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/fix-issue/scripts/find-lock-issue.sh:695-804
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Legacy audit-shaped titles without audit-report label now pass umbrella detection before report-prefix rejection. Theoretical behavior change vs the old early has_run_logs_audit_report_title gate if umbrella logic ever engaged on such a title. Move legacy rejection earlier or accept/document the new ordering explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: CHANGELOG.md / Makefile / audit-scan-run.sh / check-main-sync.sh / larch-logs/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Branch bundles multiple features beyond the audit-title rename plan. Review noise and harder bisect; not a per-line correctness bug in audit-title.sh. Confirm intentional single-PR bundling for release process.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:504-583
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New high-severity oos-silent-drop scan lacks test-audit-runs.sh fixtures and audit-scan-run.md contract text. Registry/case drift or NDJSON shape regressions ship without make lint signal; scan behavior is harder to refactor safely. Add hermetic pass/skip/fail tests and document NDJSON fields in audit-scan-run.md per edit-in-sync checklist.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:230-310;skills/fix-issue/scripts/test-find-lock-issue.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] find-lock-issue maps check-main-sync stdout/exit codes but test-find-lock-issue.sh never exercises blocked/probe-error/unexpected-exit branches. Mis-parsed SYNC_STATUS or wrong umbrella KV emission could block locks or leak locks without harness regression detection. Add sterile-repo fixtures forcing check-main-sync exits 1/2 and assert stdout KV + no lock calls.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:364-374;1906
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Permissive anti-recursion regex ^\[Run Logs Audit .* Report\] matches arbitrary middle text; test 58c encodes that breadth. Rare legitimate issue titles in that shape could be misclassified as audit noise in gh JSON classification or excluded from fix-issue alongside generic report-prefix logic. Tighten middle token to timestamp-shaped grammar or document accepted false-positive rate.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:161-162;800
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Legacy has_legacy_run_logs_audit_report_bracket_prefix remains despite plan text calling for relying only on has_report_prefix after title migration. None functionally if legacy titles truly extinct; otherwise this is extra safety not reflected in the written plan. Align written plan/issue text with the kept legacy union or delete the helper if policy is strict zero-backcompat.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] architecture: (branch vs main aggregate diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multiple unrelated feature areas and run-log flush land in one branch diff, increasing review coupling. Reviewers must mentally partition failures to the right subsystem when CI breaks. Split future PRs by feature surface when feasible (workflow guidance only).
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.md (not in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] EXIT-5 caller-kind documentation may lag ship-pr.sh tokens per prior review chatter. Operators cross-reading two sources may pick wrong resume token. Doc-only follow-up outside this change set.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/check-main-sync.md:76
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Primary Callers bullet claims find-lock-issue fail-opens probe-error and allows lock acquisition, contradicting line 17 and find-lock-issue.sh. A maintainer or future “consistency” edit could weaken the pre-lock gate to match the wrong doc line, reintroducing silent lock acquisition when main-sync classification failed but origin/main exists. Rewrite the find-lock-issue bullet to describe conditional fail-closed vs fail-open behavior and keep it aligned with find-lock-issue.md and the script.
- **Suggested revision**: Address the concern above.

### FINDING_16: security: SECURITY.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] SECURITY.md not updated while new destructive git behavior and differing probe-error postures land. Operators and downstream consumers lack a canonical documented trust boundary for auto-reset, preflight fail-open vs pre-lock fail-closed, and related OOS/audit mechanics. Add a concise SECURITY.md section covering check-main-sync reset preconditions and caller-specific probe-error semantics.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/preflight.sh:90-93
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] preflight fail-opens on SYNC_STATUS=probe-error after fetch, unlike find-lock-issue when origin/main exists. If check-main-sync cannot classify ahead commits but local main actually carries risky ahead state, preflight may still proceed into rebase/other steps without the stricter fail-closed posture used before /fix-issue locks. Confirm intent; if not acceptable, add a second probe, stderr banner, or structured warning so ambiguous states are visible before work continues.
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: skills/fix-issue/scripts/find-lock-issue.sh:8180-8257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _emit_dirty_tree_pre_lock_abort now invokes check-main-sync.sh which can git reset --hard origin/main after a clean-tree pass, mixing eligibility probing with destructive repo mutation under a dirty-tree-oriented name. Operator on clean local main with unpushed chore(larch-logs) flush commits ahead of stale origin/main runs find-lock-issue; main is silently rewound to cached origin/main, dropping local-only SHAs without a dedicated confirmation or obvious breadcrumb. Split sync from dirty-tree naming, emit explicit KV on reset, document the destructive branch in fix-issue pre-lock contracts and tests.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:8197-8254
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Successful main auto-reset returns through the same helper as a cleanliness success without an operator-visible reset signal. Downstream steps proceed while branch moved without an auditable KV line, complicating post-mortems when later git operations fail for non-obvious reasons. Emit SYNC_STATUS/reset markers on stdout (KV) and cover with a harness fixture.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/fix-issue/scripts/find-lock-issue.sh:8143-8149
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Legacy audit title grep uses a broad ^\[Run Logs Audit Report prefix (case-insensitive). A non-audit title like [Run Logs Audit Reporting] … is refused as a report-style issue despite normal labels. Tighten the legacy regex toward the historical [Run Logs Audit Report <ts>] shape or document collateral exclusion.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: .claude/skills/audit-runs/SKILL.md:109-110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New anti-recursion regex uses greedy .* between Audit and Report inside the bracket. Legitimate issues with audit-shaped recreational titles can be excluded from proposed_new_issues duplicate search, increasing duplicate filings. Narrow the middle token or combine with label-aware filtering in operator instructions.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: skills/fix-issue/scripts/find-lock-issue.sh:8124-8134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment describes lowercase report] while matching is case-insensitive. Readers may misunderstand case behavior when debugging exclusions. Align comment wording with grep -qiE semantics.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:8518-8570
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Large OOS disposition invariant and NEVER additions from the #2540/#2551 line of work. Not part of the audit-title rename feature; separate behavioral contract expansion. Track/review under the implement/OOS issue PR, not the audit-title change.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh (oos-silent-drop case)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New scan couples audit runs to git history and multiple OOS artifacts. Orthogonal integration risk to the title-format work. Review with the OOS-silent-drop change owner or issue scope.
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


### FINDING_2: code-quality: CHANGELOG.md:17-18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New lint is documented under ### Fixed rather than ### Added. Release-note readers may misread a new enforcement surface as only a bugfix. Split Added vs Fixed bullets or use ### Changed with clear wording.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-lint-awk-multibyte-regex.sh:103-108
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Clean fixture does not assert empty stderr. Lint could emit non-rule-id warnings and still pass the clean case. Assert stderr is empty or lacks the lint-awk-multibyte-regex: prefix.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/lint-awk-multibyte-regex.sh:167-200,258-271
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rule 1 scans all non-comment shell lines without heredoc context. A shell heredoc documenting awk -v label='テスト' triggers awk-v-nonascii even though the line is not executable awk code, blocking an unrelated PR. Track shell heredoc spans for Rule 1 or tighten matching to executable command contexts only.
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: scripts/ship-pr.sh:1754-1811
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] _stage_and_push_ci_fixes was modified despite plan "No change to _stage_and_push_ci_fixes" Plan reviewers and downstream callers assume the helper is untouched; the global _SAPCF_EFFECTIVE_HEAD side channel is undeclared in the plan Document the hook in the plan/acceptance or refactor to compare HEAD only in run_ci_fix_vendor after the helper returns
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/ship-pr.sh:1811-1932
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] HEAD-non-advance compares baseline_head to _SAPCF_EFFECTIVE_HEAD before refresh-run-logs, not post-_stage_and_push HEAD as the plan specifies. Vendor noop and no Fix CI failure commit, but refresh-run-logs commits larch logs: effective_head equals baseline_head while final_head advances, causing spurious first-fixer-non-health and exit 3. Compare baseline_head to final_head after _stage_and_push_ci_fixes (or move the effective snapshot past refresh); add a harness where refresh commits and vendor is noop expecting rc 0.
- **Suggested revision**: Address the concern above.



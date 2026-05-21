# Review Round 2

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 0
- Exonerated findings: 18
- Neutral findings: 0

## Accepted Findings

### FINDING_11: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1746-1765
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] C.2 version-window logic has no harness beyond isolated semver jq. Closed-only suppression vs recurrence can regress in operator automation with no failing test. Add table-driven fixture mapping fix_shipped_version/unknown vs audited_versions[] to skip|propose per SKILL.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:196-207
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq pipeline failures coerced to count 0 via 2>/dev/null and || echo 0 Corrupt review-findings-full.jsonl yields pass for oos-category-mangle instead of error/skip Emit error NDJSON on jq failure or remove silent zero fallback
- **Suggested revision**: Address the concern above.


### FINDING_26: **correctness** `.claude/skills/audit-runs/SKILL.md:126-129` — The suppression rule compares `fix_shipped_version` to every audited `larch_version` after the same normalization (“require three **integer** components `MAJOR.MINOR.PATCH`”), but it never defines what to do when a value cannot be parsed into exactly three integers (for example pre-release suffixes like `34.0.0-rc1`, unexpected extra dotted segments, or odd `larch_version` strings from older manifests). Without an explicit rule (treat parse failures as `unknown`, drop that run from the “every” comparison, or always treat as in-scope), an operator or LLM can vacuously satisfy “strictly greater than every audited `larch_version``” by treating failed parses as “no comparable versions,” wrongly suppressing a `proposed_new_issues` recurrence. **Suggested fix:** Add one sentence: if either side fails the three-integer parse, treat that side’s comparable value as `unknown` for the inequality (or conservatively force the `unknown` branch that always proposes), and record that in `version_window_checks`.
- **Reviewer**: dyn-version-window-logic-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/SKILL.md:126-129` — The suppression rule compares `fix_shipped_version` to every audited `larch_version` after the same normalization (“require three **integer** components `MAJOR.MINOR.PATCH`”), but it never defines what to do when a value cannot be parsed into exactly three integers (for example pre-release suffixes like `34.0.0-rc1`, unexpected extra dotted segments, or odd `larch_version` strings from older manifests). Without an explicit rule (treat parse failures as `unknown`, drop that run from the “every” comparison, or always treat as in-scope), an operator or LLM can vacuously satisfy “strictly greater than every audited `larch_version``” by treating failed parses as “no comparable versions,” wrongly suppressing a `proposed_new_issues` recurrence. **Suggested fix:** Add one sentence: if either side fails the three-integer parse, treat that side’s comparable value as `unknown` for the inequality (or conservatively force the `unknown` branch that always proposes), and record that in `version_window_checks`.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1693-1729` — The skip-filing session-summary stub correctly omits the **Augmentations** block (matching SKILL’s “omit empty **Augmentations** table section”), but the test only checks the decision line and two skipped per-finding rows; nothing asserts that `**Augmentations**` / the augmentations table header is absent, so a regression that always emits an empty augmentations table would not be caught. **Suggested fix:** add negative assertions (e.g. `! grep -qF '**Augmentations**'` or equivalent) on `sum60` for the “no augmentation rows” case.
- **Reviewer**: dyn-test-gap-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1693-1729` — The skip-filing session-summary stub correctly omits the **Augmentations** block (matching SKILL’s “omit empty **Augmentations** table section”), but the test only checks the decision line and two skipped per-finding rows; nothing asserts that `**Augmentations**` / the augmentations table header is absent, so a regression that always emits an empty augmentations table would not be caught. **Suggested fix:** add negative assertions (e.g. `! grep -qF '**Augmentations**'` or equivalent) on `sum60` for the “no augmentation rows” case.
- **Suggested revision**: Address the concern above.


### FINDING_34: **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:221-263` — Test 10’s sample audit body still omits `version_window_checks`, which the updated SKILL treats as always-present frontmatter alongside proposals; the test only round-trips a few legacy keys, so parser/tooling drift around the new block is unguarded. **Suggested fix:** add `version_window_checks: []` (and optionally one representative row) to the fixture and assert it survives the same extraction path used elsewhere, or add a dedicated small YAML parse check.
- **Reviewer**: dyn-test-gap-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:221-263` — Test 10’s sample audit body still omits `version_window_checks`, which the updated SKILL treats as always-present frontmatter alongside proposals; the test only round-trips a few legacy keys, so parser/tooling drift around the new block is unguarded. **Suggested fix:** add `version_window_checks: []` (and optionally one representative row) to the fixture and assert it survives the same extraction path used elsewhere, or add a dedicated small YAML parse check.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1731-1744
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Session-summary tests only model missing AUDIT_REPORT_NUMBER; they do not assert the SKILL branch that skips session-summary after a filed audit report when step 2 zero-findings short-circuit runs. A regression that always posts gh issue comment whenever AUDIT_REPORT_NUMBER is set would not be caught; zero-findings path is untested. Add a hermetic predicate test for (report filed AND zero_findings_short_circuit) -> skip comment per SKILL.md step 4.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:426-429
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] category-stats mangled_count still counts non-canonical categories across all phases while oos-category-mangle and counter deltas use plan-review accepted only. Run with code-review prose categories: oos-category-mangle passes but category-stats shows mangled>0; consumers equating the two fields misread severity. Align mangled_count jq with scan_oos_category_mangle filters or rename/clarify the broader metric in NDJSON and docs.
- **Suggested revision**: Address the concern above.



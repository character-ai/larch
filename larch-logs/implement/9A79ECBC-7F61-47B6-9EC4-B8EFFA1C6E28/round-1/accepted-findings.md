### FINDING_1: **Important** `correctness` [scripts/measure-realized-cost.sh:70](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:70) misses nested timing-report skill rows. The regex only accepts rows whose second column starts with `Step`, but committed reports contain nested rows like `larch-logs/implement/D8850B1D-CA58-40FA-B570-F3214490BF23/timing-report.md:14-16` where the second column starts with `review Step`, so `review` invocations are omitted when no `timing-report.json` exists. This underreports realized prompt cost for nested skills such as `review` and `design`. Accept optional `<skill> Step` in the second column and normalize the first cell by stripping the `↳` marker before resolving `skills/<skill>/SKILL.md`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [scripts/measure-realized-cost.sh:70](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:70) misses nested timing-report skill rows. The regex only accepts rows whose second column starts with `Step`, but committed reports contain nested rows like `larch-logs/implement/D8850B1D-CA58-40FA-B570-F3214490BF23/timing-report.md:14-16` where the second column starts with `review Step`, so `review` invocations are omitted when no `timing-report.json` exists. This underreports realized prompt cost for nested skills such as `review` and `design`. Accept optional `<skill> Step` in the second column and normalize the first cell by stripping the `↳` marker before resolving `skills/<skill>/SKILL.md`.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/measure-realized-cost.sh:52-54
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Run discovery uses larch-logs/*/* instead of the plan-scoped larch-logs/implement/*. Any new larch-logs/<kind>/<run>/ trees with manifest/timing files will be aggregated into the same skill/issue metrics, blending unrelated run kinds and skewing rankings. Limit traversal to larch-logs/implement/* (and any other categories explicitly named in the plan) rather than all two-level paths under larch-logs.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` [scripts/measure-realized-cost.sh:112](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:112) emits a TSV schema that does not match the requested contract. The feature asks for `skill,invocations,tokens_per_invocation,realized_tokens`, but the script inserts `issues_observed` as field 3, so a consumer reading column 3 as `tokens_per_invocation` gets issue counts instead. Remove `issues_observed` from the default output, or explicitly version/document a wider schema and update the feature contract.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` [scripts/measure-realized-cost.sh:112](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:112) emits a TSV schema that does not match the requested contract. The feature asks for `skill,invocations,tokens_per_invocation,realized_tokens`, but the script inserts `issues_observed` as field 3, so a consumer reading column 3 as `tokens_per_invocation` gets issue counts instead. Remove `issues_observed` from the default output, or explicitly version/document a wider schema and update the feature contract.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: larch-logs/measure-md-cost/2026-05-18.tsv (committed)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Large generated TSV committed though not listed as a deliverable in the implementation plan. Extra churn/size and confusion about whether the file is authoritative or just a sample run. Omit from git, gitignore pattern, or explicitly justify as a checked-in baseline in the plan.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: larch-logs/measure-md-cost/2026-05-18.tsv:1-1291
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Committed large generated measurement TSV ships in the repo. Parallel branches or repeated same-day runs collide on a date-stamped path; CI never regenerates or validates the snapshot so it can silently go stale. Prefer .gitignore under larch-logs/measure-md-cost/ or a documented manual baseline policy without auto-committing every run output.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/measure-realized-cost.sh:100-106
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unknown skill paths are skipped with no warning. Timing lists design or custom slugs with no SKILL.md on disk vanish from TSV; report looks healthy but omits work. Log stderr for skipped skills or emit a comment row / companion file listing skips.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/measure-realized-cost.sh:59-83
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bare except pass on timing/manifest parse. Corrupt JSON yields empty skills with no error line. Log exception summary to stderr or increment a parse_errors counter column.
- **Suggested revision**: Address the concern above.


### FINDING_29: security: scripts/measure-md-cost.sh:8-10 scripts/measure-ngram-duplication.sh:8-10 scripts/measure-realized-cost.sh:8-10 scripts/measure-references-heatmap.sh:8-10
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] LARCH_MEASURE_DATE is interpolated into OUT_FILE without sanitization; Python resolves parents and replaces the final path. Setting LARCH_MEASURE_DATE=../../../../tmp/pwned causes output (and temp file placement) outside the intended larch-logs subtree, enabling overwrite of arbitrary writable files. Validate date as YYYY-MM-DD only or build output path in Python and assert resolved path stays under OUT_DIR.
- **Suggested revision**: Address the concern above.


### FINDING_30: security: scripts/measure-ngram-duplication.sh:33-47
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] @ import targets from CLAUDE.md allow relative segments (e.g. ../) before path join. An attacker-controlled CLAUDE.md can reference ../host-secret.md; the script reads and fingerprints text outside the repository into the duplication report. Reject .. and absolute paths; resolve and require path under repo root before read.
- **Suggested revision**: Address the concern above.


### FINDING_31: security: scripts/measure-realized-cost.sh:34-42 scripts/measure-realized-cost.sh:89-104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Skill names from JSON/Markdown are not constrained before use as path components under skills/ or .claude/skills/. A malicious timing-report entry with skill ../.. causes pathlib to resolve to files outside the skill directories; token counts leak content from unintended paths. Whitelist skill slugs or resolve candidate paths and verify they lie under the skill root directories.
- **Suggested revision**: Address the concern above.



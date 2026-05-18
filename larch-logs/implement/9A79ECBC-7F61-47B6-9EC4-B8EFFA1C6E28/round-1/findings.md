### FINDING_1: **Important** `correctness` [scripts/measure-realized-cost.sh:70](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:70) misses nested timing-report skill rows. The regex only accepts rows whose second column starts with `Step`, but committed reports contain nested rows like `larch-logs/implement/D8850B1D-CA58-40FA-B570-F3214490BF23/timing-report.md:14-16` where the second column starts with `review Step`, so `review` invocations are omitted when no `timing-report.json` exists. This underreports realized prompt cost for nested skills such as `review` and `design`. Accept optional `<skill> Step` in the second column and normalize the first cell by stripping the `↳` marker before resolving `skills/<skill>/SKILL.md`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [scripts/measure-realized-cost.sh:70](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:70) misses nested timing-report skill rows. The regex only accepts rows whose second column starts with `Step`, but committed reports contain nested rows like `larch-logs/implement/D8850B1D-CA58-40FA-B570-F3214490BF23/timing-report.md:14-16` where the second column starts with `review Step`, so `review` invocations are omitted when no `timing-report.json` exists. This underreports realized prompt cost for nested skills such as `review` and `design`. Accept optional `<skill> Step` in the second column and normalize the first cell by stripping the `↳` marker before resolving `skills/<skill>/SKILL.md`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` [scripts/measure-realized-cost.sh:112](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:112) emits a TSV schema that does not match the requested contract. The feature asks for `skill,invocations,tokens_per_invocation,realized_tokens`, but the script inserts `issues_observed` as field 3, so a consumer reading column 3 as `tokens_per_invocation` gets issue counts instead. Remove `issues_observed` from the default output, or explicitly version/document a wider schema and update the feature contract.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` [scripts/measure-realized-cost.sh:112](<OPERATOR_REPO_PATH>/scripts/measure-realized-cost.sh:112) emits a TSV schema that does not match the requested contract. The feature asks for `skill,invocations,tokens_per_invocation,realized_tokens`, but the script inserts `issues_observed` as field 3, so a consumer reading column 3 as `tokens_per_invocation` gets issue counts instead. Remove `issues_observed` from the default output, or explicitly version/document a wider schema and update the feature contract.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement/9A79ECBC-7F61-47B6-9EC4-B8EFFA1C6E28/manifest.json
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] issue_number 2283 in a run log tied to a different issue id than the #2241 measurement context. Misleading only if someone assumes manifest issue always matches the feature issue; pre-existing flush semantics. Adjust only if run-log provenance for this PR should reference #2241.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: .github/workflows/ci.yaml (lint jobs)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] tiktoken is not installed in CI Python env. Only matters once CI is asked to execute the measurement scripts. Install tiktoken in the job that runs smoke tests if added later.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: implementation_plan measure-realized-cost bullet vs scripts/measure-realized-cost.sh:104-105
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan text says SKILL.md byte counts; code and docs use tiktoken token counts. Readers following only the plan narrative may expect byte-based columns or validations. Align the implementation plan wording with token-based measurement.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/measure-md-cost.sh:93-98
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Tmpfile not removed on crash before replace. Stray .tmp.measure-md-cost.* files after OOM/kill. Trap EXIT to unlink tmp_name on failure.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/measure-realized-cost.sh:52-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Glob larch-logs/*/* ingests any two-level run layout. Future non-implement logs with same filenames pollute aggregates. Restrict to larch-logs/implement/*/ or filter by manifest schema_version or parent dir name.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/measure-ngram-duplication.sh:29-30
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] git ls-files stderr not redirected unlike sibling measure-md-cost.sh. Noisy or confusing errors when git metadata is missing in edge environments. Match stderr handling to measure-md-cost.sh if desired.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: feature_description (2) vs scripts/measure-ngram-duplication.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Ticket text still requires a shell/awk helper; implementation uses embedded Python. Strict ticket acceptance that insists on awk could reject the PR despite working Python. Update the ticket or document that the implementation plan superseded the shell/awk requirement.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/measure-md-cost.sh:95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Python literal path\ttier splits as path + TAB + ier so header column is wrong. Next run writes second column name ier; parsers expecting tier break; committed 2026-05-18.tsv header does not match script output (artifact drift). Use explicit tabs around tier e.g. fh.write("path\t" + "tier\tbytes\ttokens\tlines\th2_count\n") or equivalent so tier is not glued to escape.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/measure-ngram-duplication.sh:25-27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Unvalidated int env for ngram size and limit. ngram_size 0 or negative breaks intuition or raises. Clamp ngram_size and min_files to >=1 and limit to >=0 with clear errors.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/measure-ngram-duplication.sh:52-61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] N-grams are word-token 6-grams, not character 6-grams. Character-level duplication signals can rank differently or be absent from the top-50 list versus a character shingle definition. Align spec with word n-grams or implement character n-grams if required.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/measure-ngram-duplication.sh:64-69
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Ranking score uses occurrences times ngram word count not character shingle length. Stakeholders interpreting shingle_length as characters get a different top-50 order. Define score explicitly in docs or code and lock with a small golden test.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/measure-realized-cost.sh:111-114
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Extra TSV column issues_observed not in the feature description column list. Downstream tooling expecting exactly four columns may mis-align fields. Remove column or amend the published contract.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/measure-realized-cost.sh:52-54
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Run discovery uses larch-logs/*/* instead of the plan-scoped larch-logs/implement/*. Any new larch-logs/<kind>/<run>/ trees with manifest/timing files will be aggregated into the same skill/issue metrics, blending unrelated run kinds and skewing rankings. Limit traversal to larch-logs/implement/* (and any other categories explicitly named in the plan) rather than all two-level paths under larch-logs.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/measure-realized-cost.sh:52-87
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Invocations dedupe skills per run directory via a set, ignoring repeated per_step rows in timing-report.json. Example: larch-logs/implement/A27BC9B0-BED1-458D-AD66-5CFAA390B766/timing-report.json has many per_step rows with skill implement; the script counts implement once per run, so invocations and realized_tokens scale with runs not timing steps. Count per_step (or clarify column semantics and rename); document which grain is authoritative.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/measure-realized-cost.sh:52-87
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] per_run set dedupes multiple per_step rows for same skill. Multi-step implement runs count as one invocation; realized_tokens is a lower bound vs per-step loads. Document invocations=runs_with_skill or count len(per_step rows) per skill if per-step cost is intended.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/measure-realized-cost.sh:56-86
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Invocations increment once per skill per run because skills_in_run is a set. If invocations are meant to follow timing-report rows (multiple per_step entries per skill), realized_tokens is far too low versus repeated steps in a single run. Define whether an invocation is per run or per timing step; if per step, count rows (or another explicit rule) instead of set membership.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/measure-references-heatmap.sh:68-76
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Read tool name matched case-sensitively only. Transcripts using different casing for the Read tool under-count. Compare normalized tool names or allow a case-insensitive match.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: larch-logs/measure-md-cost/2026-05-18.tsv (committed)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Large generated TSV committed though not listed as a deliverable in the implementation plan. Extra churn/size and confusion about whether the file is authoritative or just a sample run. Omit from git, gitignore pattern, or explicitly justify as a checked-in baseline in the plan.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: larch-logs/measure-md-cost/2026-05-18.tsv:1-1291
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Committed large generated measurement TSV ships in the repo. Parallel branches or repeated same-day runs collide on a date-stamped path; CI never regenerates or validates the snapshot so it can silently go stale. Prefer .gitignore under larch-logs/measure-md-cost/ or a documented manual baseline policy without auto-committing every run output.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/measure-md-cost.sh:1-101 scripts/measure-ngram-duplication.sh:1-80 scripts/measure-realized-cost.sh:1-118 scripts/measure-references-heatmap.sh:1-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI job executes the measurement scripts; only static linters may touch the bash surface. Embedded Python can regress (JSONL shape timing reports session transcripts) while PR stays green. Add a minimal smoke test or Makefile target invoked by the existing test-harness workflow.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/measure-realized-cost.sh:100-106
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Unknown skill paths are skipped with no warning. Timing lists design or custom slugs with no SKILL.md on disk vanish from TSV; report looks healthy but omits work. Log stderr for skipped skills or emit a comment row / companion file listing skips.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/measure-realized-cost.sh:112-114 scripts/measure-references-heatmap.sh:87-90
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] TSV fields (skill, rel) are written without escaping tabs/newlines. Crafted log strings inject extra TSV columns or lines and break consumers that assume a strict schema. Strip or reject \t \r \n in key fields or use JSON/CSV with proper quoting.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/measure-realized-cost.sh:52
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scans all larch-logs/*/* run-shaped dirs, broader than implement/* in the plan text. Future non-implement subtrees with manifest/timing files could be included unintentionally. Restrict glob to implement/ and explicitly listed siblings.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/measure-realized-cost.sh:52-74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Scanner globs all larch-logs/*/* run directories not only larch-logs/implement/*/. Future alternate log trees could skew aggregates versus the issue #2241 wording. Narrow the glob or document intentional inclusion of all run families.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/measure-realized-cost.sh:59-83
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bare except pass on timing/manifest parse. Corrupt JSON yields empty skills with no error line. Log exception summary to stderr or increment a parse_errors counter column.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/measure-realized-cost.sh:68-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] timing-report.md skill extraction is regex-coupled to a specific pipe-table shape. Table format drift yields empty skills_in_run for MD-only runs, skewing aggregates. Keep JSON-first and document or validate MD format.
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


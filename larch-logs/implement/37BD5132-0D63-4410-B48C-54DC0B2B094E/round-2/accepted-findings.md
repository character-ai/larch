### FINDING_1: code-quality: .claude/rules/gh-body-file.md:92-159
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate Dynamic Bodies sections repeat redaction guidance. Maintainers see conflicting or redundant instructions when the rule injects on edit. Merge into one Dynamic bodies and redaction section.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] mktemp failure reuses ISSUE_LIST_FAILED KV reserved for gh issue list failures Audit orchestrator treats TMPDIR/mktemp failure as list API failure and retries or reports the wrong failure class Emit a distinct KV (e.g. BODY_FILE_FAILED) and update audit-close-priors.md plus SKILL.md contract text
- **Suggested revision**: Address the concern above.


### FINDING_14: security: skills/report-tokens/scripts/run-analysis.sh:1031-1045
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New rule requires redaction before public gh body writes; migration writes unredacted analysis to temp file and posts it Token/tmpdir material may sit on disk in /tmp and ship to GitHub without redact-secrets.sh despite rule guidance Pipe body through redact-secrets.sh and redact-tmpdir-paths.sh before tempfile write or document an explicit exemption
- **Suggested revision**: Address the concern above.


### FINDING_16: code-quality: .claude/rules/gh-body-file.md:91-104,149-159
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate Dynamic Bodies / redaction sections Rule readers see repeated guidance; maintenance edits may update only one copy Merge into a single Dynamic Bodies and Redaction section
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/report-tokens/scripts/run-analysis.sh:1024-1041
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New gh-body-file rule requires redaction for dynamic bodies; create_report_issue only switches argv shape. Analysis issue bodies may still post unredacted paths/secrets from aggregated issue data. Pipe body through redact-secrets.sh and redact-tmpdir-paths.sh before tempfile write.
- **Suggested revision**: Address the concern above.


### FINDING_21: **architecture** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1668` — This branch changes the Test 45 `gh` stub to forbid inline `--body` and require `--body-file`, but `test-audit-runs.sh` is not listed in the rule frontmatter while its contract sibling `audit-close-priors.md` is (and that `.md`’s Edit-in-sync clause explicitly tells maintainers to update `test-audit-runs.sh` when `gh` flow changes). Future stub regressions can be reintroduced without the rule firing on the file maintainers are directed to edit. **Suggested fix:** Add `.claude/skills/audit-runs/scripts/test-audit-runs.sh` to `paths:` (and optionally a short note in `audit-close-priors.md` that the harness enforces the file-backed contract).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1668` — This branch changes the Test 45 `gh` stub to forbid inline `--body` and require `--body-file`, but `test-audit-runs.sh` is not listed in the rule frontmatter while its contract sibling `audit-close-priors.md` is (and that `.md`’s Edit-in-sync clause explicitly tells maintainers to update `test-audit-runs.sh` when `gh` flow changes). Future stub regressions can be reintroduced without the rule firing on the file maintainers are directed to edit. **Suggested fix:** Add `.claude/skills/audit-runs/scripts/test-audit-runs.sh` to `paths:` (and optionally a short note in `audit-close-priors.md` that the harness enforces the file-backed contract).
- **Suggested revision**: Address the concern above.


### FINDING_22: **architecture** `scripts/test-design-log-publish.sh:16-266` — The diff extends this harness with `--body-file` enforcement for `gh pr create`, and `scripts/design-log-publish.md` documents the harness at lines 117–118, but `scripts/test-design-log-publish.sh` is absent from `paths:`. The production caller (`scripts/design-log-publish.sh`) is covered; the regression surface that guards argv shape is not, so test-only edits can weaken the migration without injection. **Suggested fix:** Add `scripts/test-design-log-publish.sh` to `paths:` (pair with the already-listed `scripts/design-log-publish.{sh,md}`).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `scripts/test-design-log-publish.sh:16-266` — The diff extends this harness with `--body-file` enforcement for `gh pr create`, and `scripts/design-log-publish.md` documents the harness at lines 117–118, but `scripts/test-design-log-publish.sh` is absent from `paths:`. The production caller (`scripts/design-log-publish.sh`) is covered; the regression surface that guards argv shape is not, so test-only edits can weaken the migration without injection. **Suggested fix:** Add `scripts/test-design-log-publish.sh` to `paths:` (pair with the already-listed `scripts/design-log-publish.{sh,md}`).
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mktemp failure reuses ISSUE_LIST_FAILED KV. Automation treats a body-file setup failure as a list failure. Use a distinct failure key or accurate REASON without ISSUE_LIST_FAILED.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-49
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] mktemp failure reuses ISSUE_LIST_FAILED KV reserved for gh issue list failures /tmp full after successful issue list: stdout shows ISSUE_LIST_FAILED=true; SKILL.md:311 tells operator gh issue list failed; retries mis-target API/auth instead of disk/TMPDIR Introduce a separate failure KV or stderr-only exit; do not emit ISSUE_LIST_FAILED for mktemp; update audit-close-priors.md and audit-runs/SKILL.md if adding a key
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/report-tokens/scripts/run-analysis.sh:1140-1169
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] create_report_issue uses --body-file but CI never exercises issue creation test-report-tokens-recompute.sh sets LARCH_REPORT_TOKENS_NO_ISSUE=1; reverting Python to inline --body would pass CI Add stub-gh harness asserting --body-file and no inline --body when issue creation runs
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/report-tokens/scripts/run-analysis.sh:838-1051
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] create_report_issue posts analysis_text (cache_path, plot paths, aggregates) via --body-file without redact-tmpdir-paths.sh or redact-secrets.sh despite new gh-body-file rule Operator runs report-tokens against a public repo; created analysis issue body contains absolute paths like <OPERATOR_REPO_PATH>/larch-report-tokens.XXXXXX/... exposing username and local session layout on GitHub Pipe body through redact-tmpdir-paths.sh and redact-secrets.sh before writing the temp file, mirroring apply-combination.sh / create-pr.sh
- **Suggested revision**: Address the concern above.



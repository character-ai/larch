### FINDING_1: code-quality: .claude/rules/gh-body-file.md:92-159
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate Dynamic Bodies sections repeat redaction guidance. Maintainers see conflicting or redundant instructions when the rule injects on edit. Merge into one Dynamic bodies and redaction section.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/report-tokens/scripts/run-analysis.sh:1024-1041
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New gh-body-file rule requires redaction for dynamic bodies; create_report_issue only switches argv shape. Analysis issue bodies may still post unredacted paths/secrets from aggregated issue data. Pipe body through redact-secrets.sh and redact-tmpdir-paths.sh before tempfile write.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mktemp failure reuses ISSUE_LIST_FAILED KV. Automation treats a body-file setup failure as a list failure. Use a distinct failure key or accurate REASON without ISSUE_LIST_FAILED.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Committed literal has no EOF newline; acceptance text was ambiguous. Editor normalization could change upstream comment bytes vs prior inline literal. Document no-trailing-newline invariant or verify gh preserves bytes and lock with a test.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/compose-tally-record.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Not in gh-body-file paths frontmatter. Future tally gh edits miss the file-backed-body reminder. Add paths when touching those scripts (per rule maintenance clause).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: AGENTS.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No cross-link to gh-body-file or create-pr --body-file. Contributors rely on AGENTS without the new PR-creation guardrail. Add one sentence pointing to the rule and scripts/create-pr.sh.
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

### FINDING_10: security: skills/design/SKILL.md:1044-1046
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Step 5d --body-file trusts CLAUDE_PLUGIN_ROOT to resolve the committed literal path Misconfigured or attacker-controlled CLAUDE_PLUGIN_ROOT on an operator machine could cause gh to post arbitrary file contents to public upstream issue #2672 when gates pass Verify resolved path is a regular file under the expected plugin install root before gh issue comment
- **Suggested revision**: Address the concern above.

### FINDING_11: security: .claude/rules/gh-body-file.md:85-90
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Process-substitution example may skip redaction checkpoint for dynamic bodies Authors copy --body-file <(printf '%s' "$body") for large session-derived bodies and publish unredacted content Restrict example to fixed literals or show redaction before substitution; prefer mktemp + redact + --body-file path
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] mktemp failure reuses ISSUE_LIST_FAILED KV reserved for gh issue list failures Audit orchestrator treats TMPDIR/mktemp failure as list API failure and retries or reports the wrong failure class Emit a distinct KV (e.g. BODY_FILE_FAILED) and update audit-close-priors.md plus SKILL.md contract text
- **Suggested revision**: Address the concern above.

### FINDING_13: architecture: scripts/design-log-publish.sh:440-456
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Post-commit pre-push mktemp/printf failure drops worktree without recovery ref or stderr preservation Design log commit exists only on disposable branch after body-file setup fails; operator sees PUBLISH_OK=false with no recovery hint unlike push-failure path Mirror push-failure recovery ref + stderr on mktemp/printf failure after commit; document in design-log-publish.md
- **Suggested revision**: Address the concern above.

### FINDING_14: security: skills/report-tokens/scripts/run-analysis.sh:1031-1045
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New rule requires redaction before public gh body writes; migration writes unredacted analysis to temp file and posts it Token/tmpdir material may sit on disk in /tmp and ship to GitHub without redact-secrets.sh despite rule guidance Pipe body through redact-secrets.sh and redact-tmpdir-paths.sh before tempfile write or document an explicit exemption
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Committed literal has no trailing newline gh --body-file may normalize EOF and change upstream comment bytes vs historical inline post Verify gh behavior once or document byte-identical expectation after smoke test
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: .claude/rules/gh-body-file.md:91-104,149-159
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate Dynamic Bodies / redaction sections Rule readers see repeated guidance; maintenance edits may update only one copy Merge into a single Dynamic Bodies and Redaction section
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] architecture: .claude/skills/combine-issues/scripts/apply-combination.sh:100-101
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inline gh issue close --comment not covered by new rule Unchanged; different gh flag family than --body/--notes Extend rule scope in a follow-up if close comments should be file-backed
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/SKILL.md:311
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SKILL under-documents CLOSE_FAILED on exit 0 Pre-existing partial-close ambiguity not worsened by body-file change Update SKILL Close Prior Reports when touching audit-runs orchestration
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: .claude/rules/gh-body-file.md:2-39
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Frontmatter lists 37 paths while acceptance criterion 1 documents 33. Sign-off against acceptance item 1 fails literally even though coverage improved. Reconcile acceptance/plan YAML with the 37-path discovered set.
- **Suggested revision**: Address the concern above.

### FINDING_20: **architecture** `skills/research/SKILL.md:352-356` — The rule’s `paths:` frontmatter omits `skills/research/SKILL.md`, which documents a prompt-orchestrated `--body-file` handoff to `/larch:issue` (same class of surface as `skills/issue/SKILL.md`). Edits to research issue filing will not receive the path-triggered `gh-body-file` reminder, leaving a silent coverage gap next to the listed issue skill. **Suggested fix:** Add `skills/research/SKILL.md` to `.claude/rules/gh-body-file.md` `paths:` (alphabetically with the other SKILL.md entries).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `skills/research/SKILL.md:352-356` — The rule’s `paths:` frontmatter omits `skills/research/SKILL.md`, which documents a prompt-orchestrated `--body-file` handoff to `/larch:issue` (same class of surface as `skills/issue/SKILL.md`). Edits to research issue filing will not receive the path-triggered `gh-body-file` reminder, leaving a silent coverage gap next to the listed issue skill. **Suggested fix:** Add `skills/research/SKILL.md` to `.claude/rules/gh-body-file.md` `paths:` (alphabetically with the other SKILL.md entries).
- **Suggested revision**: Address the concern above.

### FINDING_21: **architecture** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1668` — This branch changes the Test 45 `gh` stub to forbid inline `--body` and require `--body-file`, but `test-audit-runs.sh` is not listed in the rule frontmatter while its contract sibling `audit-close-priors.md` is (and that `.md`’s Edit-in-sync clause explicitly tells maintainers to update `test-audit-runs.sh` when `gh` flow changes). Future stub regressions can be reintroduced without the rule firing on the file maintainers are directed to edit. **Suggested fix:** Add `.claude/skills/audit-runs/scripts/test-audit-runs.sh` to `paths:` (and optionally a short note in `audit-close-priors.md` that the harness enforces the file-backed contract).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1668` — This branch changes the Test 45 `gh` stub to forbid inline `--body` and require `--body-file`, but `test-audit-runs.sh` is not listed in the rule frontmatter while its contract sibling `audit-close-priors.md` is (and that `.md`’s Edit-in-sync clause explicitly tells maintainers to update `test-audit-runs.sh` when `gh` flow changes). Future stub regressions can be reintroduced without the rule firing on the file maintainers are directed to edit. **Suggested fix:** Add `.claude/skills/audit-runs/scripts/test-audit-runs.sh` to `paths:` (and optionally a short note in `audit-close-priors.md` that the harness enforces the file-backed contract).
- **Suggested revision**: Address the concern above.

### FINDING_22: **architecture** `scripts/test-design-log-publish.sh:16-266` — The diff extends this harness with `--body-file` enforcement for `gh pr create`, and `scripts/design-log-publish.md` documents the harness at lines 117–118, but `scripts/test-design-log-publish.sh` is absent from `paths:`. The production caller (`scripts/design-log-publish.sh`) is covered; the regression surface that guards argv shape is not, so test-only edits can weaken the migration without injection. **Suggested fix:** Add `scripts/test-design-log-publish.sh` to `paths:` (pair with the already-listed `scripts/design-log-publish.{sh,md}`).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `scripts/test-design-log-publish.sh:16-266` — The diff extends this harness with `--body-file` enforcement for `gh pr create`, and `scripts/design-log-publish.md` documents the harness at lines 117–118, but `scripts/test-design-log-publish.sh` is absent from `paths:`. The production caller (`scripts/design-log-publish.sh`) is covered; the regression surface that guards argv shape is not, so test-only edits can weaken the migration without injection. **Suggested fix:** Add `scripts/test-design-log-publish.sh` to `paths:` (pair with the already-listed `scripts/design-log-publish.{sh,md}`).
- **Suggested revision**: Address the concern above.

### FINDING_23: **architecture** `skills/review-and-fix/scripts/review-and-fix.sh:682-692` — `skills/review-and-fix/scripts/review-and-fix.{sh,md}` are in `paths:` but contain no `gh … --body` / `--notes` invocation (only `write-tally.sh --body-file`). That inflates the trigger surface without matching the rule’s stated “every `gh … --body`” scope and can dilute trust in the frontmatter as an exhaustive caller map. **Suggested fix:** Either remove `skills/review-and-fix/scripts/review-and-fix.{sh,md}` from `paths:` or add a frontmatter comment in the rule body clarifying that `paths:` also lists adjacent body-file helpers when they sit on the same edit path as `gh` callers—prefer removal unless review-and-fix is expected to gain direct `gh` body writes soon.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `skills/review-and-fix/scripts/review-and-fix.sh:682-692` — `skills/review-and-fix/scripts/review-and-fix.{sh,md}` are in `paths:` but contain no `gh … --body` / `--notes` invocation (only `write-tally.sh --body-file`). That inflates the trigger surface without matching the rule’s stated “every `gh … --body`” scope and can dilute trust in the frontmatter as an exhaustive caller map. **Suggested fix:** Either remove `skills/review-and-fix/scripts/review-and-fix.{sh,md}` from `paths:` or add a frontmatter comment in the rule body clarifying that `paths:` also lists adjacent body-file helpers when they sit on the same edit path as `gh` callers—prefer removal unless review-and-fix is expected to gain direct `gh` body writes soon.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] All production `gh … --body-file` / `--notes-file` call sites touched by the branch (`audit-close-priors.sh`, `design-log-publish.sh`, `run-analysis.sh`, `skills/design/SKILL.md` Step 5d) are represented in `paths:`; no remaining inline `gh --body` / `gh --notes` in `.sh`/`.py` production code was found.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - All production `gh … --body-file` / `--notes-file` call sites touched by the branch (`audit-close-priors.sh`, `design-log-publish.sh`, `run-analysis.sh`, `skills/design/SKILL.md` Step 5d) are represented in `paths:`; no remaining inline `gh --body` / `gh --notes` in `.sh`/`.py` production code was found.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Round-2 review expanded coverage versus the plan snapshot (37 paths vs. planned 33), including `.claude/skills/audit-runs/SKILL.md` and `.claude/skills/combine-issues/…`—appropriate given real `gh issue create --body-file` usage in `apply-combination.sh`.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - Round-2 review expanded coverage versus the plan snapshot (37 paths vs. planned 33), including `.claude/skills/audit-runs/SKILL.md` and `.claude/skills/combine-issues/…`—appropriate given real `gh issue create --body-file` usage in `apply-combination.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] `.claude/rules/gh-body-file.md:92-159` duplicates redaction/`create-pr.sh` guidance under both “Dynamic Bodies” and “Dynamic Bodies and Redaction” (maintenance drift in the rule text, not path coverage).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - `.claude/rules/gh-body-file.md:92-159` duplicates redaction/`create-pr.sh` guidance under both “Dynamic Bodies” and “Dynamic Bodies and Redaction” (maintenance drift in the rule text, not path coverage).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] `skills/design/references/l3-velocity-deferral-comment.txt` lands without a final newline (`\ No newline at end of file` in the diff); likely a correctness/byte-identity concern rather than frontmatter architecture.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - `skills/design/references/l3-velocity-deferral-comment.txt` lands without a final newline (`\ No newline at end of file` in the diff); likely a correctness/byte-identity concern rather than frontmatter architecture.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] The diff includes committed `larch-logs/implement/…` run artifacts; unrelated to `paths:` design but adds noise to the PR.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - The diff includes committed `larch-logs/implement/…` run artifacts; unrelated to `paths:` design but adds noise to the PR.
- **Suggested revision**: Address the concern above.


### FINDING_12: [OUT_OF_SCOPE] architecture: repo-wide
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No CI guard for inline gh --body/--notes outside rule paths. New script outside frontmatter can reintroduce #2830 class failures without path-triggered reminder. Future issue: pre-commit grep or agent-lint (explicitly out of scope for this PR).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/design-log-publish.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Operational exit-0 vs set -e non-zero split predates this PR. Printf/disk errors can still yield non-zero exit unlike PUBLISH_OK=false paths. Separate hardening issue if callers need uniform exit semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] **Nit** `scripts/design-log-publish.sh:147-149` — Plan FINDING_28 specified the trap-safe one-liner `[ -n "${PR_BODY_TMP:-}" ] && rm -f "$PR_BODY_TMP" 2>/dev/null || true`; the branch uses an equivalent `if [ -n ... ]; then rm ...; fi` block. No behavioral gap; stylistic deviation from the prescribed snippet only.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Nit** `scripts/design-log-publish.sh:147-149` — Plan FINDING_28 specified the trap-safe one-liner `[ -n "${PR_BODY_TMP:-}" ] && rm -f "$PR_BODY_TMP" 2>/dev/null || true`; the branch uses an equivalent `if [ -n ... ]; then rm ...; fi` block. No behavioral gap; stylistic deviation from the prescribed snippet only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] **Nit** `.claude/rules/gh-body-file.md:39` — Plan title sketch used an em dash (`— File-Backed Only`); the landed H1 uses a hyphen. Cosmetic only.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** `.claude/rules/gh-body-file.md:39` — Plan title sketch used an em dash (`— File-Backed Only`); the landed H1 uses a hyphen. Cosmetic only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Plan acceptance item 1 says “33 alphabetized path entries” while the plan YAML and implementation both list **34** paths. Implementation matches the YAML list; the “33” figure is an acceptance-text typo, not a missing path.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. Plan acceptance item 1 says “33 alphabetized path entries” while the plan YAML and implementation both list **34** paths. Implementation matches the YAML list; the “33” figure is an acceptance-text typo, not a missing path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] **Flush/close before `gh`:** Exiting the `with` block closes the handle and flushes buffers, so `subprocess.run(..., --body-file, body_path)` sees a complete on-disk file; no defect there.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **Flush/close before `gh`:** Exiting the `with` block closes the handle and flushes buffers, so `subprocess.run(..., --body-file, body_path)` sees a complete on-disk file; no defect there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] **`subprocess.run` exceptions:** With `check=False`, non-zero `gh` exit does not raise; if `subprocess.run` does raise (e.g. `gh` missing), `body_path` is already bound and `finally` still unlinks correctly.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **`subprocess.run` exceptions:** With `check=False`, non-zero `gh` exit does not raise; if `subprocess.run` does raise (e.g. `gh` missing), `body_path` is already bound and `finally` still unlinks correctly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] **`f.write(body)` reachability:** `body` is an in-memory `str` from `analysis_text` and `json.dumps`; write failures are uncommon but plausible under disk pressure or very large reports—low operational impact (orphan files under `$TMPDIR`), but worth fixing for correctness symmetry with the bash `mktemp`+trap migrations elsewhere in the PR.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **`f.write(body)` reachability:** `body` is an in-memory `str` from `analysis_text` and `json.dumps`; write failures are uncommon but plausible under disk pressure or very large reports—low operational impact (orphan files under `$TMPDIR`), but worth fixing for correctness symmetry with the bash `mktemp`+trap migrations elsewhere in the PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] The scout-requested compliant callers (`scripts/tracking-issue-summary.{sh,md}`, `skills/issue/scripts/create-one.{sh,md}`, `skills/review-and-fix/scripts/review-and-fix.{sh,md}`, `.github/workflows/release-tag.yaml`, `scripts/gh-pr-body-update.{sh,md}`, `scripts/ship-pr.{sh,md}`, `scripts/clarify-comment-post.{sh,md}`, `scripts/plan-block-write.{sh,md}`) are all present in the frontmatter; required-pattern examples at `.claude/rules/gh-body-file.md:74-93` correctly bless both `--body-file - <<'EOF'` stdin heredocs and `--body-file <(…)` process substitution, and forbidden-pattern examples at `.claude/rules/gh-body-file.md:93-101` match the intended prohibitions.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - The scout-requested compliant callers (`scripts/tracking-issue-summary.{sh,md}`, `skills/issue/scripts/create-one.{sh,md}`, `skills/review-and-fix/scripts/review-and-fix.{sh,md}`, `.github/workflows/release-tag.yaml`, `scripts/gh-pr-body-update.{sh,md}`, `scripts/ship-pr.{sh,md}`, `scripts/clarify-comment-post.{sh,md}`, `scripts/plan-block-write.{sh,md}`) are all present in the frontmatter; required-pattern examples at `.claude/rules/gh-body-file.md:74-93` correctly bless both `--body-file - <<'EOF'` stdin heredocs and `--body-file <(…)` process substitution, and forbidden-pattern examples at `.claude/rules/gh-body-file.md:93-101` match the intended prohibitions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] `skills/research/SKILL.md:355` documents `--body-file` only as an `/issue` Skill-tool argument (indirect `gh` path through `create-one.sh`, which is already covered); lower risk than the missing combine-issues and audit-runs surfaces above.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - `skills/research/SKILL.md:355` documents `--body-file` only as an `/issue` Skill-tool argument (indirect `gh` path through `create-one.sh`, which is already covered); lower risk than the missing combine-issues and audit-runs surfaces above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] `skills/design/references/decompose-panel.md:179` documents `gh issue comment --body-file` but is not listed; `skills/design/scripts/decompose-file-issues.{sh,md}` are covered, so script edits still get the rule.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - `skills/design/references/decompose-panel.md:179` documents `gh issue comment --body-file` but is not listed; `skills/design/scripts/decompose-file-issues.{sh,md}` are covered, so script edits still get the rule.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] No remaining runtime inline `gh … --body` / `--notes` callers were found in shipped scripts after this branch’s migrations; the path-coverage gaps above are the main architectural weakness in an otherwise aligned change set.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - No remaining runtime inline `gh … --body` / `--notes` callers were found in shipped scripts after this branch’s migrations; the path-coverage gaps above are the main architectural weakness in an otherwise aligned change set.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=0 Result=rejected


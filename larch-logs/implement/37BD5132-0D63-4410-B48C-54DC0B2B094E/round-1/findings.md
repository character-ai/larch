### FINDING_1: code-quality: scripts/design-log-publish.sh:451-458
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mktemp failure handler references PUSH_DONE recovery before push ever runs Maintainers may think a failed body mktemp after push leaves RECOVERY_BRANCH; with current ordering that branch is dead Remove or comment the unreachable PUSH_DONE recovery in the mktemp failure path
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Committed Step 5d constant likely includes a POSIX trailing newline unlike the old inline --body literal. If gh preserves file bytes verbatim, the upstream #2672 comment body may differ by one trailing newline from pre-PR behavior. Verify gh behavior or write the file without a trailing newline via printf '%s' if byte parity is required.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] create_report_issue() only unlinks the temp body file in finally after a successful with/write; write failures can leak delete=False temp files. A disk-full or I/O error during f.write(body) exits before finally, leaving larch-report-tokens-body-* on disk. Assign body_path on open and always unlink in finally/except, or use delete=True with an explicit flush before gh reads the file.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: .claude/rules/gh-body-file.md:3-36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Rule frontmatter has 34 paths; plan acceptance #1 says 33. No runtime failure; acceptance checklist may be marked incomplete incorrectly. Align acceptance text with the actual 34-path frontmatter.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1652
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Test 45 gh stub does not assert --body-file after audit-close-priors migration A future edit reintroduces gh issue comment --body "Superseded…"; Test 45 still passes and CI stays green Extend Test 45 stub to forbid --body require --body-file and optionally cmp temp file body
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: .claude/rules/gh-body-file.md:66-93
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New rule prescribes mktemp/Write/--body-file patterns without requiring redact-secrets.sh or redact-tmpdir-paths.sh before public gh writes Assistant follows gh-body-file.md to post a session-derived plan or token report via gh issue comment --body-file without running the redaction pipeline used elsewhere Add a Dynamic bodies subsection referencing SECURITY.md and requiring redact-secrets.sh (and tmpdir-path redaction where applicable) before any gh network write; point PR creation to scripts/create-pr.sh
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Committed Step 5d body likely includes a POSIX trailing newline not present in the former inline --body literal. First post after deploy may differ by one byte from every prior #2672 deferral comment; breaks acceptance "no trailing newline drift" and strict fixed-literal comparisons. Create the file without a final newline (printf '%s' …) or add a byte-exact cmp test against the old inline string.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] mktemp has no error handling while set -e is enabled. TMPDIR exhaustion after a successful gh issue list exits 1 with no CLOSED_NUMBER/CLOSE_FAILED contract lines. Add mktemp || { … } with structured stderr/stdout before exit.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:1627-1652
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Test 45 was not updated though audit-close-priors.md requires sync when gh call flow changes. Future reintroduction of inline --body in audit-close-priors.sh still passes Test 45. Extend the gh stub to reject --body and require --body-file (mirror test-design-log-publish.sh).
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Temp body file cleanup only runs after successful write completes the with block. f.write failure on a large analysis body leaves a delete=False tempfile on disk. Single try/finally around write+gh+unlink, or delete=True with guaranteed finally unlink.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/design-log-publish.sh:451-458
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] mktemp failure handler checks PUSH_DONE but mktemp now runs before push. Misleading recovery logic may cause a wrong fix if push is reordered later. Remove dead PUSH_DONE branch or document why it is unreachable.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] architecture: repo-wide
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No CI guard for inline gh --body/--notes outside rule paths. New script outside frontmatter can reintroduce #2830 class failures without path-triggered reminder. Future issue: pre-commit grep or agent-lint (explicitly out of scope for this PR).
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/design-log-publish.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Operational exit-0 vs set -e non-zero split predates this PR. Printf/disk errors can still yield non-zero exit unlike PUBLISH_OK=false paths. Separate hardening issue if callers need uniform exit semantics.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] **Nit** `scripts/design-log-publish.sh:147-149` — Plan FINDING_28 specified the trap-safe one-liner `[ -n "${PR_BODY_TMP:-}" ] && rm -f "$PR_BODY_TMP" 2>/dev/null || true`; the branch uses an equivalent `if [ -n ... ]; then rm ...; fi` block. No behavioral gap; stylistic deviation from the prescribed snippet only.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Nit** `scripts/design-log-publish.sh:147-149` — Plan FINDING_28 specified the trap-safe one-liner `[ -n "${PR_BODY_TMP:-}" ] && rm -f "$PR_BODY_TMP" 2>/dev/null || true`; the branch uses an equivalent `if [ -n ... ]; then rm ...; fi` block. No behavioral gap; stylistic deviation from the prescribed snippet only.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] **Nit** `.claude/rules/gh-body-file.md:39` — Plan title sketch used an em dash (`— File-Backed Only`); the landed H1 uses a hyphen. Cosmetic only.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Nit** `.claude/rules/gh-body-file.md:39` — Plan title sketch used an em dash (`— File-Backed Only`); the landed H1 uses a hyphen. Cosmetic only.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Plan acceptance item 1 says “33 alphabetized path entries” while the plan YAML and implementation both list **34** paths. Implementation matches the YAML list; the “33” figure is an acceptance-text typo, not a missing path.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. Plan acceptance item 1 says “33 alphabetized path entries” while the plan YAML and implementation both list **34** paths. Implementation matches the YAML list; the “33” figure is an acceptance-text typo, not a missing path.
- **Suggested revision**: Address the concern above.

### FINDING_17: **correctness** `skills/report-tokens/scripts/run-analysis.sh:1031-1049` — The `try`/`finally` that calls `os.unlink(body_path)` sits *after* the `with tempfile.NamedTemporaryFile(..., delete=False)` block, not around it. If `f.write(body)` raises (e.g. `OSError` from a full disk on a large analysis + JSON body), the `with` exits with that exception and the `try`/`finally` never runs, so the temp file is left on disk. The scout’s `NameError` in `finally` does **not** occur on that path (`finally` is skipped), but the leak is still a real, reachable failure-mode regression introduced by this change. **Suggested fix:** Set `body_path = None` before the `with`, assign `body_path = f.name` immediately on entry (before `f.write`), and wrap both the write and `subprocess.run` in one `try`/`finally` that unlinks when `body_path is not None` (same pattern as `if body_path: try: os.unlink(body_path) except OSError: pass`).
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **correctness** `skills/report-tokens/scripts/run-analysis.sh:1031-1049` — The `try`/`finally` that calls `os.unlink(body_path)` sits *after* the `with tempfile.NamedTemporaryFile(..., delete=False)` block, not around it. If `f.write(body)` raises (e.g. `OSError` from a full disk on a large analysis + JSON body), the `with` exits with that exception and the `try`/`finally` never runs, so the temp file is left on disk. The scout’s `NameError` in `finally` does **not** occur on that path (`finally` is skipped), but the leak is still a real, reachable failure-mode regression introduced by this change. **Suggested fix:** Set `body_path = None` before the `with`, assign `body_path = f.name` immediately on entry (before `f.write`), and wrap both the write and `subprocess.run` in one `try`/`finally` that unlinks when `body_path is not None` (same pattern as `if body_path: try: os.unlink(body_path) except OSError: pass`).
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] **Flush/close before `gh`:** Exiting the `with` block closes the handle and flushes buffers, so `subprocess.run(..., --body-file, body_path)` sees a complete on-disk file; no defect there.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **Flush/close before `gh`:** Exiting the `with` block closes the handle and flushes buffers, so `subprocess.run(..., --body-file, body_path)` sees a complete on-disk file; no defect there.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] **`subprocess.run` exceptions:** With `check=False`, non-zero `gh` exit does not raise; if `subprocess.run` does raise (e.g. `gh` missing), `body_path` is already bound and `finally` still unlinks correctly.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **`subprocess.run` exceptions:** With `check=False`, non-zero `gh` exit does not raise; if `subprocess.run` does raise (e.g. `gh` missing), `body_path` is already bound and `finally` still unlinks correctly.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] **`f.write(body)` reachability:** `body` is an in-memory `str` from `analysis_text` and `json.dumps`; write failures are uncommon but plausible under disk pressure or very large reports—low operational impact (orphan files under `$TMPDIR`), but worth fixing for correctness symmetry with the bash `mktemp`+trap migrations elsewhere in the PR.
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **`f.write(body)` reachability:** `body` is an in-memory `str` from `analysis_text` and `json.dumps`; write failures are uncommon but plausible under disk pressure or very large reports—low operational impact (orphan files under `$TMPDIR`), but worth fixing for correctness symmetry with the bash `mktemp`+trap migrations elsewhere in the PR.
- **Suggested revision**: Address the concern above.

### FINDING_21: **architecture** `.claude/rules/gh-body-file.md:2-36` — The new rule’s `paths:` frontmatter is marketed as the grep-discovered, exhaustive injection surface, but it omits `.claude/skills/combine-issues/scripts/apply-combination.sh`, a live runtime caller that invokes `gh issue create … --body-file` at lines 83–85. Edits to that script therefore bypass the path-triggered reminder, recreating the same silent-coverage failure mode the PR fixed for `run-analysis.sh` and `audit-close-priors.sh`. **Suggested fix:** Add `.claude/skills/combine-issues/scripts/apply-combination.sh` and its prompt-side sibling `.claude/skills/combine-issues/SKILL.md` (lines 48–55 document the `--body-file` contract) to the alphabetized `paths:` list in `.claude/rules/gh-body-file.md`.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md:2-36` — The new rule’s `paths:` frontmatter is marketed as the grep-discovered, exhaustive injection surface, but it omits `.claude/skills/combine-issues/scripts/apply-combination.sh`, a live runtime caller that invokes `gh issue create … --body-file` at lines 83–85. Edits to that script therefore bypass the path-triggered reminder, recreating the same silent-coverage failure mode the PR fixed for `run-analysis.sh` and `audit-close-priors.sh`. **Suggested fix:** Add `.claude/skills/combine-issues/scripts/apply-combination.sh` and its prompt-side sibling `.claude/skills/combine-issues/SKILL.md` (lines 48–55 document the `--body-file` contract) to the alphabetized `paths:` list in `.claude/rules/gh-body-file.md`.
- **Suggested revision**: Address the concern above.

### FINDING_22: **architecture** `.claude/rules/gh-body-file.md:2-36` — The frontmatter includes `.claude/skills/audit-runs/scripts/audit-close-priors.{sh,md}` but not `.claude/skills/audit-runs/SKILL.md`, even though that skill file contains normative, copy-pasteable `gh issue comment … --body-file` instructions for augmentation comments (line 144) and the post-report session summary (line 172). An agent editing `/audit-runs` orchestration will not see the new rule while the skill still teaches direct `gh` body posting, leaving a prompt-side regression vector back to inline `--body`. **Suggested fix:** Add `.claude/skills/audit-runs/SKILL.md` to `paths:` alongside the existing audit-close-priors entries.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md:2-36` — The frontmatter includes `.claude/skills/audit-runs/scripts/audit-close-priors.{sh,md}` but not `.claude/skills/audit-runs/SKILL.md`, even though that skill file contains normative, copy-pasteable `gh issue comment … --body-file` instructions for augmentation comments (line 144) and the post-report session summary (line 172). An agent editing `/audit-runs` orchestration will not see the new rule while the skill still teaches direct `gh` body posting, leaving a prompt-side regression vector back to inline `--body`. **Suggested fix:** Add `.claude/skills/audit-runs/SKILL.md` to `paths:` alongside the existing audit-close-priors entries.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] The scout-requested compliant callers (`scripts/tracking-issue-summary.{sh,md}`, `skills/issue/scripts/create-one.{sh,md}`, `skills/review-and-fix/scripts/review-and-fix.{sh,md}`, `.github/workflows/release-tag.yaml`, `scripts/gh-pr-body-update.{sh,md}`, `scripts/ship-pr.{sh,md}`, `scripts/clarify-comment-post.{sh,md}`, `scripts/plan-block-write.{sh,md}`) are all present in the frontmatter; required-pattern examples at `.claude/rules/gh-body-file.md:74-93` correctly bless both `--body-file - <<'EOF'` stdin heredocs and `--body-file <(…)` process substitution, and forbidden-pattern examples at `.claude/rules/gh-body-file.md:93-101` match the intended prohibitions.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - The scout-requested compliant callers (`scripts/tracking-issue-summary.{sh,md}`, `skills/issue/scripts/create-one.{sh,md}`, `skills/review-and-fix/scripts/review-and-fix.{sh,md}`, `.github/workflows/release-tag.yaml`, `scripts/gh-pr-body-update.{sh,md}`, `scripts/ship-pr.{sh,md}`, `scripts/clarify-comment-post.{sh,md}`, `scripts/plan-block-write.{sh,md}`) are all present in the frontmatter; required-pattern examples at `.claude/rules/gh-body-file.md:74-93` correctly bless both `--body-file - <<'EOF'` stdin heredocs and `--body-file <(…)` process substitution, and forbidden-pattern examples at `.claude/rules/gh-body-file.md:93-101` match the intended prohibitions.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `skills/research/SKILL.md:355` documents `--body-file` only as an `/issue` Skill-tool argument (indirect `gh` path through `create-one.sh`, which is already covered); lower risk than the missing combine-issues and audit-runs surfaces above.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - `skills/research/SKILL.md:355` documents `--body-file` only as an `/issue` Skill-tool argument (indirect `gh` path through `create-one.sh`, which is already covered); lower risk than the missing combine-issues and audit-runs surfaces above.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] `skills/design/references/decompose-panel.md:179` documents `gh issue comment --body-file` but is not listed; `skills/design/scripts/decompose-file-issues.{sh,md}` are covered, so script edits still get the rule.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - `skills/design/references/decompose-panel.md:179` documents `gh issue comment --body-file` but is not listed; `skills/design/scripts/decompose-file-issues.{sh,md}` are covered, so script edits still get the rule.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] No remaining runtime inline `gh … --body` / `--notes` callers were found in shipped scripts after this branch’s migrations; the path-coverage gaps above are the main architectural weakness in an otherwise aligned change set.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - No remaining runtime inline `gh … --body` / `--notes` callers were found in shipped scripts after this branch’s migrations; the path-coverage gaps above are the main architectural weakness in an otherwise aligned change set.
- **Suggested revision**: Address the concern above.


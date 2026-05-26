### FINDING_1: code-quality: scripts/design-log-publish.sh:451-458
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mktemp failure handler references PUSH_DONE recovery before push ever runs Maintainers may think a failed body mktemp after push leaves RECOVERY_BRANCH; with current ordering that branch is dead Remove or comment the unreachable PUSH_DONE recovery in the mktemp failure path
- **Suggested revision**: Address the concern above.


### FINDING_10: architecture: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Temp body file cleanup only runs after successful write completes the with block. f.write failure on a large analysis body leaves a delete=False tempfile on disk. Single try/finally around write+gh+unlink, or delete=True with guaranteed finally unlink.
- **Suggested revision**: Address the concern above.


### FINDING_17: **correctness** `skills/report-tokens/scripts/run-analysis.sh:1031-1049` — The `try`/`finally` that calls `os.unlink(body_path)` sits *after* the `with tempfile.NamedTemporaryFile(..., delete=False)` block, not around it. If `f.write(body)` raises (e.g. `OSError` from a full disk on a large analysis + JSON body), the `with` exits with that exception and the `try`/`finally` never runs, so the temp file is left on disk. The scout’s `NameError` in `finally` does **not** occur on that path (`finally` is skipped), but the leak is still a real, reachable failure-mode regression introduced by this change. **Suggested fix:** Set `body_path = None` before the `with`, assign `body_path = f.name` immediately on entry (before `f.write`), and wrap both the write and `subprocess.run` in one `try`/`finally` that unlinks when `body_path is not None` (same pattern as `if body_path: try: os.unlink(body_path) except OSError: pass`).
- **Reviewer**: dyn-python-tempfile-safety-output.txt
- **Concern**: - **correctness** `skills/report-tokens/scripts/run-analysis.sh:1031-1049` — The `try`/`finally` that calls `os.unlink(body_path)` sits *after* the `with tempfile.NamedTemporaryFile(..., delete=False)` block, not around it. If `f.write(body)` raises (e.g. `OSError` from a full disk on a large analysis + JSON body), the `with` exits with that exception and the `try`/`finally` never runs, so the temp file is left on disk. The scout’s `NameError` in `finally` does **not** occur on that path (`finally` is skipped), but the leak is still a real, reachable failure-mode regression introduced by this change. **Suggested fix:** Set `body_path = None` before the `with`, assign `body_path = f.name` immediately on entry (before `f.write`), and wrap both the write and `subprocess.run` in one `try`/`finally` that unlinks when `body_path is not None` (same pattern as `if body_path: try: os.unlink(body_path) except OSError: pass`).
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Committed Step 5d constant likely includes a POSIX trailing newline unlike the old inline --body literal. If gh preserves file bytes verbatim, the upstream #2672 comment body may differ by one trailing newline from pre-PR behavior. Verify gh behavior or write the file without a trailing newline via printf '%s' if byte parity is required.
- **Suggested revision**: Address the concern above.


### FINDING_21: **architecture** `.claude/rules/gh-body-file.md:2-36` — The new rule’s `paths:` frontmatter is marketed as the grep-discovered, exhaustive injection surface, but it omits `.claude/skills/combine-issues/scripts/apply-combination.sh`, a live runtime caller that invokes `gh issue create … --body-file` at lines 83–85. Edits to that script therefore bypass the path-triggered reminder, recreating the same silent-coverage failure mode the PR fixed for `run-analysis.sh` and `audit-close-priors.sh`. **Suggested fix:** Add `.claude/skills/combine-issues/scripts/apply-combination.sh` and its prompt-side sibling `.claude/skills/combine-issues/SKILL.md` (lines 48–55 document the `--body-file` contract) to the alphabetized `paths:` list in `.claude/rules/gh-body-file.md`.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md:2-36` — The new rule’s `paths:` frontmatter is marketed as the grep-discovered, exhaustive injection surface, but it omits `.claude/skills/combine-issues/scripts/apply-combination.sh`, a live runtime caller that invokes `gh issue create … --body-file` at lines 83–85. Edits to that script therefore bypass the path-triggered reminder, recreating the same silent-coverage failure mode the PR fixed for `run-analysis.sh` and `audit-close-priors.sh`. **Suggested fix:** Add `.claude/skills/combine-issues/scripts/apply-combination.sh` and its prompt-side sibling `.claude/skills/combine-issues/SKILL.md` (lines 48–55 document the `--body-file` contract) to the alphabetized `paths:` list in `.claude/rules/gh-body-file.md`.
- **Suggested revision**: Address the concern above.


### FINDING_22: **architecture** `.claude/rules/gh-body-file.md:2-36` — The frontmatter includes `.claude/skills/audit-runs/scripts/audit-close-priors.{sh,md}` but not `.claude/skills/audit-runs/SKILL.md`, even though that skill file contains normative, copy-pasteable `gh issue comment … --body-file` instructions for augmentation comments (line 144) and the post-report session summary (line 172). An agent editing `/audit-runs` orchestration will not see the new rule while the skill still teaches direct `gh` body posting, leaving a prompt-side regression vector back to inline `--body`. **Suggested fix:** Add `.claude/skills/audit-runs/SKILL.md` to `paths:` alongside the existing audit-close-priors entries.
- **Reviewer**: dyn-rule-path-coverage-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md:2-36` — The frontmatter includes `.claude/skills/audit-runs/scripts/audit-close-priors.{sh,md}` but not `.claude/skills/audit-runs/SKILL.md`, even though that skill file contains normative, copy-pasteable `gh issue comment … --body-file` instructions for augmentation comments (line 144) and the post-report session summary (line 172). An agent editing `/audit-runs` orchestration will not see the new rule while the skill still teaches direct `gh` body posting, leaving a prompt-side regression vector back to inline `--body`. **Suggested fix:** Add `.claude/skills/audit-runs/SKILL.md` to `paths:` alongside the existing audit-close-priors entries.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] create_report_issue() only unlinks the temp body file in finally after a successful with/write; write failures can leak delete=False temp files. A disk-full or I/O error during f.write(body) exits before finally, leaving larch-report-tokens-body-* on disk. Assign body_path on open and always unlink in finally/except, or use delete=True with an explicit flush before gh reads the file.
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



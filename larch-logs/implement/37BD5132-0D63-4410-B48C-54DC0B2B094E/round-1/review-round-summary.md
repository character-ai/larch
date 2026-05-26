# Review Round 1

- Mode: `diff`
- 10 accepted, 2 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/design-log-publish.sh:451-458
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mktemp failure handler references PUSH_DONE recovery before push ever runs Maintainers may think a failed body mktemp after push leaves RECOVERY_BRANCH; with current ordering that branch is dead Remove or comment the unreachable PUSH_DONE recovery in the mktemp failure path
- **Suggested revision**: Address the concern above.


### FINDING_10: architecture: skills/report-tokens/scripts/run-analysis.sh:1031-1049
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Temp body file cleanup only runs after successful write completes the with block. f.write failure on a large analysis body leaves a delete=False tempfile on disk. Single try/finally around write+gh+unlink, or delete=True with guaranteed finally unlink.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/design-log-publish.sh:451-458
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] mktemp failure handler checks PUSH_DONE but mktemp now runs before push. Misleading recovery logic may cause a wrong fix if push is reordered later. Remove dead PUSH_DONE branch or document why it is unreachable.
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


### FINDING_4: correctness: .claude/rules/gh-body-file.md:3-36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Rule frontmatter has 34 paths; plan acceptance #1 says 33. No runtime failure; acceptance checklist may be marked incomplete incorrectly. Align acceptance text with the actual 34-path frontmatter.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: .claude/skills/audit-runs/scripts/audit-close-priors.sh:47-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] mktemp has no error handling while set -e is enabled. TMPDIR exhaustion after a successful gh issue list exits 1 with no CLOSED_NUMBER/CLOSE_FAILED contract lines. Add mktemp || { … } with structured stderr/stdout before exit.
- **Suggested revision**: Address the concern above.



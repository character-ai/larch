### FINDING_1: **code-quality** `.claude/skills/audit-runs/SKILL.md:16` — The Usage fence shows `/audit-runs …` while the work is described elsewhere as `/larch:audit-runs`, so an operator following only this file may invoke the wrong slash command or think the skill is wired under a different name. **Suggested fix:** Use the canonical invocable name in the Usage block (or one line that states the alias relationship explicitly).
- **Reviewer**: dyn-content-encoding-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/SKILL.md:16` — The Usage fence shows `/audit-runs …` while the work is described elsewhere as `/larch:audit-runs`, so an operator following only this file may invoke the wrong slash command or think the skill is wired under a different name. **Suggested fix:** Use the canonical invocable name in the Usage block (or one line that states the alias relationship explicitly).
- **Suggested revision**: Address the concern above.


### FINDING_10: architecture: skills/fix-issue/scripts/find-lock-issue.sh:699-821
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Label is sole machine guard for audit reports because has_report_prefix does not match the standard audit title (test-audit-runs.sh:594-616). Missing audit-report label leaves a standard audit title pickable by /fix-issue. Add a secondary title-based exclusion for the stable audit prefix or enforce label at filing time with verification.
- **Suggested revision**: Address the concern above.


### FINDING_11: architecture: skills/fix-issue/scripts/find-lock-issue.sh:940-944
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Auto-pick audit-report skip uses the same jq -e pattern per candidate row. When inner jq errors, bash skips continue and the candidate is processed as unlabeled, risking lock acquisition on an audit-report issue if labels could not be read. Distinguish jq exit 1 (false) from other exits; on other exits emit ERROR and exit 2 or skip fail-closed.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.md:52-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness explicitly not wired into make lint. Regression risk for verbal-description and guard logic without CI. Add a Makefile target mirroring test-find-lock-issue when feasible.
- **Suggested revision**: Address the concern above.


### FINDING_13: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:435-436
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] bad_body uses literal backslash-n not newline. Test intent slightly misleading though assertion still holds. Use $'…' for real newlines if needed.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: .claude/skills/audit-runs/SKILL.md:41-43
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Concurrency preflight uses gh issue list --search 'created:>5m'. If relative 5m is unsupported or ignored the guard mis-fires (false block or false allow). Replace with verified search syntax or filter createdAt in jq after --json.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: .claude/skills/audit-runs/SKILL.md:66 vs .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] NS-retry scan prose mentions *-first-pass.txt but scans.tsv only lists *-ns-retry*.txt. Anyone implementing scans from TSV alone may omit NS-retry-related first-pass sidecars the table still calls out. Extend scans.tsv or edit the table so registry and prose match.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: .claude/skills/audit-runs/scans.tsv:6
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] codex-round1-adherence pattern uses round-[2-9] only. Run logs with round-10+ would not match the registry row for Codex-in-round-2+ detection. Extend the pattern to cover multi-digit round directories or document the single-digit limitation as intentional.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/fix-issue/scripts/find-lock-issue.sh:699-707
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Explicit-path audit-report jq check is fail-open on jq/JSON failure per comment. Corrupt ISSUE_JSON or jq failure skips the block so a labeled audit-report issue may continue. Exit 2 on jq failure or tighten contract vs comment.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/fix-issue/scripts/find-lock-issue.sh:699-707
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Explicit-path audit-report jq is fail-open on jq or JSON failure. Malformed ISSUE_JSON or jq failure skips label rejection; explicit /fix-issue could lock an audit-report issue. Fail-closed on jq error or separate labels-only fetch with strict handling.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/fix-issue/scripts/find-lock-issue.sh:699-707
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Explicit-path audit-report jq uses fail-open on jq/JSON failure per comment. Malformed ISSUE_JSON or jq failure skips label rejection; explicit /fix-issue could lock an audit-report issue. Fail-closed on jq error or separate labels-only fetch with strict handling.
- **Suggested revision**: Address the concern above.


### FINDING_2: **code-quality** `.claude/skills/audit-runs/SKILL.md:36` — Pre-flight step 2 documents `gh repo view <--repo> --json url`, which reads like invalid or placeholder-corrupted CLI text (`<--repo>` is not a standard `gh` operand pattern and is easy to mis-copy). **Suggested fix:** Match established repo wording (for example `gh repo view -R owner/name --json url` or `gh repo view owner/name --json url` with a clear variable for the `--repo` argument).
- **Reviewer**: dyn-content-encoding-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/SKILL.md:36` — Pre-flight step 2 documents `gh repo view <--repo> --json url`, which reads like invalid or placeholder-corrupted CLI text (`<--repo>` is not a standard `gh` operand pattern and is easy to mis-copy). **Suggested fix:** Match established repo wording (for example `gh repo view -R owner/name --json url` or `gh repo view owner/name --json url` with a clear variable for the `--repo` argument).
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: .claude/skills/audit-runs/SKILL.md:15-16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Usage shows /audit-runs while larch skills are commonly invoked as /larch:skillname. Users may not discover the dev skill from docs alone. Document the canonical /larch:audit-runs invocation or show both forms.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: .claude/skills/audit-runs/SKILL.md:19-23
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Usage shows /audit-runs while catalog/feature use /larch:audit-runs. Wrong slash command leaves operators thinking the skill is missing or mis-invoked. Align Usage with the registered command name (note alias only if real).
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: .claude/skills/audit-runs/SKILL.md:37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Concurrency guard example uses gh issue list with --search 'created:>5m'. Operators may get ineffective concurrency protection or surprising refusals if GitHub search does not interpret the relative window as intended. Use an explicit UTC timestamp in the search string or a documented REST filter.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.md:52-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] test-audit-runs not wired into make lint / CI harness shards. CI never runs the new tests; broken harness or stale assertions go unnoticed. Add Makefile target plus test-harnesses shard wiring and agent-lint excludes if required.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:194-196;skills/fix-issue/scripts/test-audit-runs.sh:610-616
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Label-only exclusion; canonical audit titles do not match has_report_prefix. Missing audit-report label on an audit-shaped issue leaves it pickable. Add optional title guard or keep as strict ops discipline with docs only.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:699-707,940-944
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] audit-report label gates are fail-open when jq fails or labels are not a JSON array. A gh/jq glitch or unexpected labels shape skips exclusion; /fix-issue may lock or auto-pick an audit-report issue despite policy. Parse labels in a fail-closed step: require successful JSON decode and array-typed labels before eligibility; exit 2 if labels cannot be verified.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: skills/fix-issue/scripts/find-lock-issue.sh:940-945
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Auto-pick label jq uses jq -e; parse failure does not treat row as audit-report. Corrupt issue_row could bypass audit-report skip. Fail-closed or visible error when label classification cannot run.
- **Suggested revision**: Address the concern above.


### FINDING_3: **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:171` — `bad_body="## Summary\nNo frontmatter here"` does not produce a newline between the two fragments in Bash (double-quoted strings do not treat `\n` as a line break), so the test data does not reflect the stated “missing frontmatter” shape as literally as the label suggests, even though the assertion can still pass because there is no `---` block. **Suggested fix:** Use `$'## Summary\nNo frontmatter here'` or a real multi-line assignment so the fixture matches real issue-body layout.
- **Reviewer**: dyn-content-encoding-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:171` — `bad_body="## Summary\nNo frontmatter here"` does not produce a newline between the two fragments in Bash (double-quoted strings do not treat `\n` as a line break), so the test data does not reflect the stated “missing frontmatter” shape as literally as the label suggests, even though the assertion can still pass because there is no `---` block. **Suggested fix:** Use `$'## Summary\nNo frontmatter here'` or a real multi-line assignment so the fixture matches real issue-body layout.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** `.claude/skills/audit-runs/SKILL.md:37` — The concurrency guard tells operators to run `gh issue list ... --search 'created:>5m'`. GitHub issue search `created:` qualifiers are normally absolute timestamps (`created:>YYYY-MM-DD` / full ISO-style dates), so `>5m` is very likely not interpreted as “created in the last five minutes,” which would make the guard ineffective or brittle depending on how `gh` forwards the query. **Suggested fix:** Document a syntax that GitHub’s search actually accepts (absolute cutoff computed in-shell) or drop `--search` in favor of listing recent `audit-report` issues and filtering with `jq` on `createdAt` against “now − 5 minutes.”
- **Reviewer**: dyn-content-encoding-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/SKILL.md:37` — The concurrency guard tells operators to run `gh issue list ... --search 'created:>5m'`. GitHub issue search `created:` qualifiers are normally absolute timestamps (`created:>YYYY-MM-DD` / full ISO-style dates), so `>5m` is very likely not interpreted as “created in the last five minutes,” which would make the guard ineffective or brittle depending on how `gh` forwards the query. **Suggested fix:** Document a syntax that GitHub’s search actually accepts (absolute cutoff computed in-shell) or drop `--search` in favor of listing recent `audit-report` issues and filtering with `jq` on `createdAt` against “now − 5 minutes.”
- **Suggested revision**: Address the concern above.


### FINDING_8: architecture: .claude/skills/audit-runs/SKILL.md:15-17
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Usage shows /audit-runs while feature brief names /larch:audit-runs. Runbooks or allowlists keyed on /larch:audit-runs may not map to the documented command; mixed messaging vs repo docs that use bare /skill paths. Align Usage (and any cross-links) with the real resolved slash form(s), documenting both if both work.
- **Suggested revision**: Address the concern above.


### FINDING_9: architecture: skills/fix-issue/scripts/find-lock-issue.sh:699-706
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Label exclusion uses jq -e inside bash if with stderr discarded; comment says fail-open on parse error. If jq errors or JSON shape is unexpected while the issue is otherwise eligible, the script does not exit 2 and may proceed toward umbrella or lock paths for an audit-report issue. Treat jq failures as eligibility failures (distinct exit code path) or validate labels with a dedicated jq program that errors loudly.
- **Suggested revision**: Address the concern above.



# Review Round 1

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 4
- Exonerated findings: 14
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **architecture** `.claude/skills/audit-runs/SKILL.md:13-30` — Usage and Args document that `--no-fix-issues` is gone, but the skill never tells the orchestrator to treat a present `--no-fix-issues` as a hard usage error, while the updated harness in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:354-377` pins exactly that rejection contract. That splits the “removed flag” behavior across a test-only stub and markdown, so a legacy invocation can be silently ignored instead of failing fast, and the harness is not a faithful stand-in for anything the skill text requires. **Suggested fix:** Add an explicit Args or Pre-flight bullet: if any argv token is `--no-fix-issues`, refuse with a clear usage error (flag removed); keep the harness aligned with that single normative sentence.
- **Reviewer**: dyn-user-gate-completeness-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/SKILL.md:13-30` — Usage and Args document that `--no-fix-issues` is gone, but the skill never tells the orchestrator to treat a present `--no-fix-issues` as a hard usage error, while the updated harness in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:354-377` pins exactly that rejection contract. That splits the “removed flag” behavior across a test-only stub and markdown, so a legacy invocation can be silently ignored instead of failing fast, and the harness is not a faithful stand-in for anything the skill text requires. **Suggested fix:** Add an explicit Args or Pre-flight bullet: if any argv token is `--no-fix-issues`, refuse with a clear usage error (flag removed); keep the harness aligned with that single normative sentence.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: .claude/skills/audit-runs/SKILL.md:119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Augmentation step documents bare gh issue comment without --body-file. Multi-line markdown tables and special characters are easy to mis-quote in inline gh invocations; risk of failed posts or accidental shell metacharacter expansion compared to prior body-file pattern. Document gh issue comment N --body-file path.tmp matching create-one.sh style.
- **Suggested revision**: Address the concern above.


### FINDING_2: **architecture** `.claude/skills/audit-runs/SKILL.md:199-207` — The new `## Output to chat` section lists the body, URL, and short-circuit vs 3-way prompt but does not restate the sequencing precondition spelled out in `### Post-report user prompt` (lines 112–114: only after the new audit report is filed and **Close Prior Reports** has run). An orchestrator that jumps to the tail section could emit the chat contract before superseding/closing prior `audit-report` issues, which is inconsistent with the earlier gate even though it is not a bug-issue auto-file path. **Suggested fix:** Open `## Output to chat` with the same one-line precondition as `### Post-report user prompt` (after filing and after prior-report handling), so ordering is single-sourced.
- **Reviewer**: dyn-user-gate-completeness-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/SKILL.md:199-207` — The new `## Output to chat` section lists the body, URL, and short-circuit vs 3-way prompt but does not restate the sequencing precondition spelled out in `### Post-report user prompt` (lines 112–114: only after the new audit report is filed and **Close Prior Reports** has run). An orchestrator that jumps to the tail section could emit the chat contract before superseding/closing prior `audit-report` issues, which is inconsistent with the earlier gate even though it is not a bug-issue auto-file path. **Suggested fix:** Open `## Output to chat` with the same one-line precondition as `### Post-report user prompt` (after filing and after prior-report handling), so ordering is single-sourced.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:374-427` — Test 15 only exercises the all-empty proposal case; there is no complementary case where `proposed_new_issues` or `proposed_augmentations` is non-empty (including asymmetric mixes such as one list empty and the other populated), so the harness never proves the post-report path emits the 3-way prompt instead of the short-circuit line. **Suggested fix:** Add one or two fixtures (e.g. non-empty `proposed_new_issues` with `proposed_augmentations: []`, and the reverse) and assert `audit_report_post_report_chat_block` output contains the 3-way question substring and does not contain `No findings — no bug issues to file.`
- **Reviewer**: dyn-test-coverage-gap-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:374-427` — Test 15 only exercises the all-empty proposal case; there is no complementary case where `proposed_new_issues` or `proposed_augmentations` is non-empty (including asymmetric mixes such as one list empty and the other populated), so the harness never proves the post-report path emits the 3-way prompt instead of the short-circuit line. **Suggested fix:** Add one or two fixtures (e.g. non-empty `proposed_new_issues` with `proposed_augmentations: []`, and the reverse) and assert `audit_report_post_report_chat_block` output contains the 3-way question substring and does not contain `No findings — no bug issues to file.`
- **Suggested revision**: Address the concern above.



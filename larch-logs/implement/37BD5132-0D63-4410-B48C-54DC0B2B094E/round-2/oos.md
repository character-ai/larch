### FINDING_17: [OUT_OF_SCOPE] architecture: .claude/skills/combine-issues/scripts/apply-combination.sh:100-101
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inline gh issue close --comment not covered by new rule Unchanged; different gh flag family than --body/--notes Extend rule scope in a follow-up if close comments should be file-backed
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/SKILL.md:311
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SKILL under-documents CLOSE_FAILED on exit 0 Pre-existing partial-close ambiguity not worsened by body-file change Update SKILL Close Prior Reports when touching audit-runs orchestration
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_20: **architecture** `skills/research/SKILL.md:352-356` — The rule’s `paths:` frontmatter omits `skills/research/SKILL.md`, which documents a prompt-orchestrated `--body-file` handoff to `/larch:issue` (same class of surface as `skills/issue/SKILL.md`). Edits to research issue filing will not receive the path-triggered `gh-body-file` reminder, leaving a silent coverage gap next to the listed issue skill. **Suggested fix:** Add `skills/research/SKILL.md` to `.claude/rules/gh-body-file.md` `paths:` (alphabetically with the other SKILL.md entries).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `skills/research/SKILL.md:352-356` — The rule’s `paths:` frontmatter omits `skills/research/SKILL.md`, which documents a prompt-orchestrated `--body-file` handoff to `/larch:issue` (same class of surface as `skills/issue/SKILL.md`). Edits to research issue filing will not receive the path-triggered `gh-body-file` reminder, leaving a silent coverage gap next to the listed issue skill. **Suggested fix:** Add `skills/research/SKILL.md` to `.claude/rules/gh-body-file.md` `paths:` (alphabetically with the other SKILL.md entries).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] All production `gh … --body-file` / `--notes-file` call sites touched by the branch (`audit-close-priors.sh`, `design-log-publish.sh`, `run-analysis.sh`, `skills/design/SKILL.md` Step 5d) are represented in `paths:`; no remaining inline `gh --body` / `gh --notes` in `.sh`/`.py` production code was found.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - All production `gh … --body-file` / `--notes-file` call sites touched by the branch (`audit-close-priors.sh`, `design-log-publish.sh`, `run-analysis.sh`, `skills/design/SKILL.md` Step 5d) are represented in `paths:`; no remaining inline `gh --body` / `gh --notes` in `.sh`/`.py` production code was found.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] Round-2 review expanded coverage versus the plan snapshot (37 paths vs. planned 33), including `.claude/skills/audit-runs/SKILL.md` and `.claude/skills/combine-issues/…`—appropriate given real `gh issue create --body-file` usage in `apply-combination.sh`.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - Round-2 review expanded coverage versus the plan snapshot (37 paths vs. planned 33), including `.claude/skills/audit-runs/SKILL.md` and `.claude/skills/combine-issues/…`—appropriate given real `gh issue create --body-file` usage in `apply-combination.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] `.claude/rules/gh-body-file.md:92-159` duplicates redaction/`create-pr.sh` guidance under both “Dynamic Bodies” and “Dynamic Bodies and Redaction” (maintenance drift in the rule text, not path coverage).
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - `.claude/rules/gh-body-file.md:92-159` duplicates redaction/`create-pr.sh` guidance under both “Dynamic Bodies” and “Dynamic Bodies and Redaction” (maintenance drift in the rule text, not path coverage).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] `skills/design/references/l3-velocity-deferral-comment.txt` lands without a final newline (`\ No newline at end of file` in the diff); likely a correctness/byte-identity concern rather than frontmatter architecture.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - `skills/design/references/l3-velocity-deferral-comment.txt` lands without a final newline (`\ No newline at end of file` in the diff); likely a correctness/byte-identity concern rather than frontmatter architecture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] The diff includes committed `larch-logs/implement/…` run artifacts; unrelated to `paths:` design but adds noise to the PR.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - The diff includes committed `larch-logs/implement/…` run artifacts; unrelated to `paths:` design but adds noise to the PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/compose-tally-record.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Not in gh-body-file paths frontmatter. Future tally gh edits miss the file-backed-body reminder. Add paths when touching those scripts (per rule maintenance clause).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] code-quality: AGENTS.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No cross-link to gh-body-file or create-pr --body-file. Contributors rely on AGENTS without the new PR-creation guardrail. Add one sentence pointing to the rule and scripts/create-pr.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


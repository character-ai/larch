### FINDING_1: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-tally-plan-review.sh:157-160
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness failure strings still describe empty voters as 'NEUTRAL' / 'neutral quorum'. File not modified on branch; messages diverge from renamed JUDGE_ERROR semantics. Update messages when editing that test file.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-tally-plan-review.sh:157-160
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test harness failure strings still say NEUTRAL/neutral quorum for empty voter files; not updated with JERR/JUDGE_ERROR vocabulary. File not modified on this branch; only terminology drift vs new tally headers. Optional follow-up: align messages with JUDGE_ERROR/JERR naming for consistent operator debugging.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-tally-plan-review.sh:158-160
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Failure strings still reference NEUTRAL for a JUDGE_ERROR-era tally. File not touched by this branch diff. Update strings if touching that harness in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-tally-plan-review.sh:158-160
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Fail messages still say NEUTRAL / neutral quorum for empty voter files. Unchanged file; same terminology drift as the renamed parser-fallback concept. Optional follow-up: align wording with JUDGE_ERROR for cross-harness consistency.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/**
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Historical logs retain old NEUT column and NEUTRAL= vote tally format. Old sessions look inconsistent with new tool output; not a runtime bug. Refresh logs only if the project intentionally updates archived examples.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/** (committed run logs)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Historical voting-tally.md and diag sidecars use old NEUT column and NEUTRAL= / neutral_count= strings. Pre-existing shipped logs; not a runtime regression. Rely on docs/run-logs.md distinction; accept mixed formats when comparing across plugin versions.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/design/scripts/tally-plan-review.md:19
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Awkward quorum doc phrase non-JUDGE_ERROR response count. Readers may confuse panel quorum with per-finding parsed-vote counts or with finding-level neutral. Reword to explicit panel-level eligible-voter basis without the ambiguous noun phrase.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review/scripts/test-tally-code-votes.sh:289-292
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale failure message still says neutral quorum after JUDGE_ERROR/JERR rename. When this assertion fails in CI, logs mislead a reader into thinking the case is about finding-level neutral ties rather than per-judge JUDGE_ERROR counts and a rejected outcome row. Rename the printf failure text to reference JERR/JUDGE_ERROR or rejected-row wording consistent with the case title.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/review/scripts/test-tally-code-votes.sh:291
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Failure message still says 'neutral quorum row missing' for the 1 YES / 2 parser-fallback rejected row assertion. When the grep fails the operator may think finding-level neutral/tie semantics broke instead of per-judge JERR counts. Reword to JERR/JUDGE_ERROR or 'two empty voter outputs'.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review/scripts/test-tally-code-votes.sh:291
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stale failure message still says neutral quorum after NEUTRAL→JUDGE_ERROR rename. When the assertion fails, operators grep CI logs for neutral and misread the failure mode as quorum/neutral instead of missing JERR/rejected row. Update printf text to describe JERR/JUDGE_ERROR or rejected vote row.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/review/scripts/test-tally-code-votes.sh:291
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale harness failure message still says neutral quorum after JUDGE_ERROR rename. Failing grep mislabels the failing condition as neutral/tie semantics instead of missing-parser-vote / JERR column. Rename printf to reference JERR or per-finding tally row wording.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/test-tally-code-votes.sh:279-291
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Failure printf still says neutral quorum row missing after JUDGE_ERROR rename. When the voting-tally row assertion fails, CI/local logs point to wrong semantics and slow down debugging. Update the FAIL printf to describe the JERR/rejected row expectation (match the updated case title).
- **Suggested revision**: Address the concern above.


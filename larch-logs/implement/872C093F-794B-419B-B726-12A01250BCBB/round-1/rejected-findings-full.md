### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/review/scripts/test-findings-classification.sh:63-83
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fixture B omits explicit vote-tally baseline check per plan. classify_result could change while classification columns look correct. Assert ACCEPTED_COUNT/FINDING_1_OUTCOME against a fully-rated baseline run.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: security: skills/review/scripts/tally-code-votes.sh:199-223
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] finding_id column is written without tab/newline sanitization unlike reviewer_slots. Relaxed ballot IDs or corrupted block filenames could shift TSV columns or confuse spreadsheet consumers of committed larch-logs artifacts. Sanitize or strictly validate finding_id to the FINDING_N/OOS_N grammar before append.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: correctness: skills/review/scripts/test-findings-classification.sh:130-144
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fixture F omits missing-line parser vs vote_for_id divergence. Future refactor can reintroduce dual-parser tally/TSV skew without CI signal. Add fixture for absent vote line: tally judge_error count vs TSV empty vN_vote.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: risk-integration: skills/review/scripts/test-findings-classification.sh:130-144
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fixture F does not exercise tally single-parse path (FINDING_14). Future split of vote_for_id vs parser in tally could diverge silently. Add tally-driven fixture asserting parser and vote_for_id agree for all ballot ids in effective voter files.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


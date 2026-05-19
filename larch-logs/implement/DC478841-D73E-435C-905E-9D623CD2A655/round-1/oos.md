### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:37-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Awk FS=: plus clearing $1 can lose embedded colons in rare reviewer strings. Long reviewer tokens containing extra ':' characters may print a corrupted attribution; unchanged extraction logic in this PR. If needed later, join $2..NF with ':' instead of rebuilding $0 from fields.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.sh:37-47
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] FS=: splits on all colons in a line; unusual reviewer strings with extra colons may parse poorly. Rare malformed or pathological attribution values could truncate or skew extracted text. Only change if you decide to support multi-colon values; out of scope for this anchoring fix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:419-428 and skills/review/scripts/tally-code-votes.sh:477-487
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate basename normalization helpers (norm_base vs norm) in one script. Increases drift risk if normalization rules ever diverge. Refactor to a single shared awk snippet or shell-sourced fragment; not required for this PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh:37-47
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Colon inside reviewer attribution truncates remainder when FS is : Attribution value like foo:bar prints only foo Pre-existing; fix by parsing first : only or joining fields if ever required
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/tally-plan-review.sh:222
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-review tally uses reviewer_for_block without a dedicated harness in this PR Non-canonical plan ballot attribution would map to unknown in the plan scoreboard; not exercised beyond unit tests Accept protocol-enforced format or add a small tally-plan-review fixture if drift is a concern
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.sh:456-459
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fragile NDJSON output path extraction via regex. Unusual JSON shapes could mis-parse output basenames for dead-slot rows. Pre-existing; consider a real JSON filter if this becomes security- or integrity-critical.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] security: skills/review/scripts/tally-code-votes.sh:320
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] reviewer TSV field is not normalized for embedded tabs/newlines. Malicious or accidental attribution text could break TSV structure for downstream tools. Not introduced by this diff; sanitize or reject control characters when writing score_rows if you harden this path later.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected


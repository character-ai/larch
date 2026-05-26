### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/parse-judge-vote-and-rating.sh:52-70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Axis-like tokens in rationale without -- delimiter are parsed as ratings. Judge line FINDING_N: YES ... reviewer noted QUALITY=weak with no -- records weak as parsed quality. Strengthen prompt discipline or tighten parser to ignore tokens after vote block without -- delimiter.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: security: skills/design/scripts/tally-plan-review.sh:274-344
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Committed findings-classification.tsv cells are sanitized only for tabs/newlines, not spreadsheet formula prefixes from untrusted judge/ballot text. An operator opens the published TSV in Excel/Sheets; a cell beginning with =cmd| or similar could execute a formula injection chain from malicious judge output. Prefix or escape formula-leading characters in every string cell at TSV write time; add harness coverage for =/+/-/@ prefixes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: security: skills/design/scripts/tally-plan-review.sh:50-91,289-344
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --findings-classification-out has no symlink or under-tmpdir containment check before atomic write. A same-UID writer replaces the round TSV path with a symlink; tally mv follows it and overwrites an attacker-chosen file. Resolve output with pwd -P, reject symlinks, optionally require path under $DESIGN_TMPDIR/plan-review/.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/tally-plan-review.sh:303-337
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] write_findings_classification double-calls vote_for_id and spawns parse-judge-vote-and-rating.sh per voter per finding Large ballots pay redundant subprocess and awk cost; vote parsing logic is duplicated in one loop Cache vote_for_id per (id,p); reuse for counts and TSV; reduce parser invocations
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/design/scripts/tally-plan-review.sh:324-329
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] vN_vote uses vote_for_id while ratings use parse-judge-vote-and-rating with -- delimiter scoping. Rationale after -- containing vote-like tokens could yield different vote in vN_vote vs PARSED_VOTE/voting_result. Prefer PARSED_VOTE for vN_vote when set; add delimiter-scoping parity harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/parse-judge-vote-and-rating.sh:83-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four separate awk splits after awk already emitted a TSV line Minor unnecessary subprocess churn in a hot helper Split the single awk line with one read or one awk -F pass
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


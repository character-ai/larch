### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: TSV string cells are not protected against spreadsheet formulas
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Published TSV string fields can begin with spreadsheet formula prefixes such as `=`, `+`, `-`, or `@`, which can execute when opened in spreadsheet tools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Parser embeds ballot IDs in awk regexes without escaping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `parse-judge-vote-and-rating.sh` places `ballot_id` into an awk regex without metacharacter escaping, so crafted direct CLI input can alter matching semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Parser does not tolerate punctuation or split rating-axis tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Axis validation only accepts single whitespace-delimited tokens, so trailing punctuation or split tokens produce empty axis cells and `PARSED_UNCERTAIN=true` despite an otherwise valid vote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Harness shard 9 may be overloaded
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-findings-classification` was added to `test-harnesses-9` without visible shard rebalancing, which may push shard 9 over the CI time budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: Tally output path is not contained under design tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--findings-classification-out` lacks a containment check against canonical `--design-tmpdir`, so a mis-invoked tally can write outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0


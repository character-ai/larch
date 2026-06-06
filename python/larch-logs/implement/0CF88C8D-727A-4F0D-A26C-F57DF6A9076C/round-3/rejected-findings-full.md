### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: skills/issue/scripts/test-parse-input.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-requested end-to-end filing coverage via parse-input is absent (plan testing strategy). Gate may pass and blocks normalize, but no test proves /issue batch parser accepts producer output from legacy FINDING normalization. Add parse-input smoke test with normalized ### OOS_1: block derived from legacy FINDING header fixture.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/lib-vote-tally.sh:421-443; skills/shared/scripts/oos-serialize.sh:29-51; skills/implement/scripts/oos-non-security-block-count.awk:17-20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Security routing logic triplicated across Python, serialize awk, and counter awk without a shared authority. One site gets a format tweak (e.g. backtick-wrapped focus-area) while others lag, reintroducing security leak or false gate failures. Centralize security-routing detection; make serializers/counters thin consumers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1460-1478
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant second is_security_block call and duplicate error branches in the skipped-OOS path. Extra Python subprocess per skipped block and confusing control flow for maintainers. Use the first classifier result in the else branch; normalize without re-invoking.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: skills/shared/scripts/normalize-oos-block-header.md:5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract omits oos-serialize.sh even though serialize performs the same rewrite inline. Docs mislead future editors about which paths perform canonical header normalization. List oos-serialize as a caller or delegate serialize to the shared script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


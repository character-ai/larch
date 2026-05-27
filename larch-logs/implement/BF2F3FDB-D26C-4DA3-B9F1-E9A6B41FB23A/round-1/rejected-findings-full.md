### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Design top-chat emit contract remains prose-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: CI can grep prose, but cannot verify that the live orchestrator actually reads and pastes the full summary body into top chat. A manual smoke or tighter mechanical mechanism is still needed to catch paraphrase, cost-line-only output, or halted emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Retired design gating prose can partially reappear undetected
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Negative greps in `scripts/test-render-cost-line-callsites.sh` omit close variants of retired cost/gating/mechanism text, so partial reintroduction could evade the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


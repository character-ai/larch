### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Review-round slots are consumed before panel success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3 persists the review-round count before launching the panel. Crashes or kills can consume cap slots without producing fresh panel findings, eventually forcing approval from stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: timing-ledger fallback acceptance is not implemented literally
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan/acceptance text requires a `timing-ledger.sh` fallback chain, but `scripts/timing-ledger.sh` itself does not read `run-params`. The behavior may work through sibling timing-report readers, but the literal acceptance bullet remains unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: Classification reader hides parse/read failures behind exit 0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/read-design-classification.sh` always exits 0 and prints `HARD` on read or parse failure, with only a stderr warning. Automation checking `$?` can treat failures as success and silently apply HARD caps/emphasis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Gate C still offers re-run at review cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate C’s cap-aware option list is prose-only while Step 3 is the only mechanical guard. Operators can still be shown a Re-run option at cap, then lose a turn when Step 3 immediately short-circuits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


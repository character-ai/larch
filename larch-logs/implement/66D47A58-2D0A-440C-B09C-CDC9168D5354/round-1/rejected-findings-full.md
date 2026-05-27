### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Gate B boolean parsing does not coerce corrupt values
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `jq -r '.manual_gate_b // false'` does not coerce non-boolean JSON, so corrupt `run-params.json` can route Gate B to the wrong mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Gate B branching lacks automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No automated test exercises Gate B auto-apply versus manual branching, so string pins and manual smoke may miss regressions in the default mode flip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Apply-all merges reviewer prose without untrusted-data handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Apply-all merges `accepted-plan-findings.md` into `plan.txt` without the same untrusted-data handling as `ballot.txt`, so instruction-like reviewer prose could steer downstream implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Gate C summary mode may hide auto-applied changes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: For large plans, Gate C may show only an outline after auto-apply has revised `plan.txt`, so the operator can approve without seeing applied finding changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: Discussion rollback lacks artifact cleanup steps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If a user discusses further and rejects an auto-applied finding, stale `accepted-plan-findings.md` state can cause the next Gate B auto-apply to apply it again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: Plan acceptance blocker wiring is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance requires issue `#2667` to be blocked by `#2930` after PR open, but the diff has no blocker wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Cross-tier Gate B invariant is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The cross-tier paragraph duplicates tier-uniform Gate B content, increasing the chance future edits update one copy but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: git apply --recount may loosen live apply semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Using `git apply --recount` for live apply may accept corrupt hunks that strict apply would reject, unexpectedly mutating `plan.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Tier-4 fallback is not surfaced as degraded after earlier validation failures
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After invalid-patch tiers, tier 4 can fully rewrite `plan.txt` and continue as `ok-fallback` without clearly surfacing degraded confidence in Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: merge_tier4_status lacks plan-precedence harness coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-tier4-state-machine-output.txt
- **Severity**: latent
- **Concern**: `merge_tier4_status` uses numeric ranks rather than the documented case table. Reviewers disagree on whether behavior is currently correct, but both point to missing regression coverage for precedence invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-tier4-state-machine-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Python extraction policy diverges from planned awk strip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `extract_patch` is implemented as a larger Python helper with selection behavior beyond the planned awk preamble strip, adding a dependency and creating plan-fidelity ambiguity around multi-patch outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


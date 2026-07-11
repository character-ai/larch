### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Require committed regression coverage for every producer path and the gate
- **Reviewer(s)**: dyn-dyn-gate-sequencing
- **Severity**: major
- **Concern**: The retained text only says “test the producer and gate together,” which could be satisfied by a one-off manual smoke check rather than committed regression coverage. A later producer-path regression could therefore ship without failing the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-sequencing: Name a committed regression explicitly, e.g. “add a regression test that runs every live producer path and the gate together,” and cite that test requirement in the `- Why:` line (or restore a parser-visible `- Guidance:` bullet if you split rationale from normative rules again).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

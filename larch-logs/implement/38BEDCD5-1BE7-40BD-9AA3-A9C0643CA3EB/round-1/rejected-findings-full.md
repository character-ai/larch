### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Empty stripped scope anchor silently disables anchoring
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A plan-only feature file can strip to whitespace, producing empty scope-anchor blocks while prompts still claim binding issue scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Marker normalization misses some severity-prefixed Concern forms
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scope-marker-output.txt
- **Severity**: latent
- **Concern**: The detector may miss tagged findings when collect-style Concern text begins with unrecognized severity brackets such as `[blocking] [SCOPE-REDUCTION]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-scope-marker-output.txt: Add a collect fixture plus a call to `check-scope-reduction-marker.sh` on the emitted block.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Unrelated PR line-count feature is bundled with scope-anchor work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The `#3506` PR line-count work is mixed into the `#3482` scope-anchor change, complicating review, bisect, and rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Inline dedup / marker helper scripts increase drift risk
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Runtime-generated dedup Python and repeated tagged-block helper subprocess code make future marker-rule changes error-prone across loop and aggregation paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


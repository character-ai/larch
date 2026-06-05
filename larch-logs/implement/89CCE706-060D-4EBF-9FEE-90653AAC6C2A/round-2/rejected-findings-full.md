### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Reviewer basename/static-slug normalization is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Reviewer output basename normalization and static slug detection are implemented in multiple scripts. Drift in phase/retry suffix handling or static basename rules could make threshold counting, coverage attribution, and vote tallying disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Coverage gate hardcodes static archetype slugs separately from dispatch authority
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `review-core.sh` hardcodes the four required static archetypes instead of consuming the dispatch-panel authority. Adding or renaming a static archetype in dispatch without updating coverage can make review-core require the wrong lenses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Threshold never-launched padding is unreachable because intended and launched counts are identical
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `review-core.sh` passes identical intended-slot and launched-slot counts to the threshold script, so the threshold script’s never-launched padding path never runs. A manifest row that fails to launch without dropped-slot or collector evidence may not increment failed slots unless another gate catches it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Threshold counting can mis-handle duplicate normalized basenames or disagreeing statuses
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-waterfall-routing-output.txt
- **Severity**: latent
- **Concern**: `check-reviewer-failure-threshold.sh` can undercount or overcount when collector rows and phase/retry output files normalize to the same basename but carry different statuses. Collector duplicates can inflate failures, while collector OK plus failed phase artifacts can hide failures unless the script merges to one worst-status outcome per normalized base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-waterfall-routing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


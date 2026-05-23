### [rejected] FINDING_3

### FINDING_3: `CHANGELOG` may hide the harness fix from readers who only scan the dated release section
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The harness fix is documented under Unreleased while the `42.0.3` section cites a different closed issue, so operators scanning only the dated `42.0.3` Changed bullets may miss the harness leak fix until the next release unless the note is mirrored or `#2617` is cited where the change actually ships.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0


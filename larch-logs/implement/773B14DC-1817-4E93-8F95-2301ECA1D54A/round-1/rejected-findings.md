### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Attached-long `--file` operands bypass parent-ascent handling
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-awk-segments
- **Severity**: important
- **Concern**: `--file../VALUE` tokens are not normalized, so pattern-file parsing can miss parent-ascent values and misclassify the following token as a path. On pipe-fed segments, that can skip both the parent-ascent and no-path checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-awk-segments: Treat attached-long `--fileVALUE` the same as `-fVALUE` and `--file=VALUE` (strip the `--file` prefix and run `has_parent_ascent_segment()` on the remainder), and add regression fixtures for split, equals, attached-short, and attached-long `--file` forms on both plain and pipe-fed segments.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0


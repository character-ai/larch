### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Conditional span over-attribution across clause boundaries and multi-follow lines
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-closure-classifier
- **Severity**: important
- **Concern**: The clause matcher can associate the wrong path with the qualifier because it spans too broadly across separate citations and repeated `follow` directives on the same line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Bound the match to clause delimiters or use a clause extractor that stops at the trigger’s own directive.
  - From dyn-dyn-closure-classifier: Bound the clause to the operand immediately before the matched `only <connector>` (last `.md` before the qualifier), or emit one `DirectiveMatch` per verb–path–qualifier triple; add a multi-`follow` line regression test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0


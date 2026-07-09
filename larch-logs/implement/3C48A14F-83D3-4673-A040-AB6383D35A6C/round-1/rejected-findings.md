### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: shared invariant grammar still aliases `INV-*`
- **Reviewer(s)**: dyn-dyn-convention-lint
- **Severity**: major
- **Concern**: The parity fixture claims `INV-*` stays rejected, but it only asserts `identifier != "INV-Depth-1"`. The shared `INVARIANT_HEADING_RE` still matches `### INV-Depth-1: …` as `I-NV-Depth-1`, so reader, indexer, and `finditer` all accept that alias while `INV-*` is not actually excluded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-convention-lint: Tighten the canonical invariant pattern so `INV-` cannot match as `I-…` (for example require `(?<!IN)I-` or an explicit negative lookahead for `INV-`), then assert that no indexed or reader ID starts with `INV` or equals the `I-NV-…` alias for the fixture heading.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0


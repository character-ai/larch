### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Cursor Grok pricing omits the Teams surcharge
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: `("cursor", "grok-4.5")` is priced at 2.00 / 0.50 / 6.00 without the Teams surcharge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Cursor bucket validation mishandles nonstandard bucket shapes
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_cursor_bucket_counts` rejects integer-valued floats such as `1000.0`, causing valid model-aware data to fall back to blended pricing. The shared helper also validates bucket values but not model keys, so malformed non-string keys may be treated as valid detailed data. Validate integer-normalizable counts and accepted model-key types, with fallback coverage for invalid shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Grok-only detailed pricing and source-shape gating need stronger guarantees
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Grok-only CLI flags or model buckets should enter detailed pricing through `u_detail_present`, emit Composer, Grok, and Auto component keys—including zero-valued Composer and Auto—and sum those components to `CURSOR_COST`. Separately, treating any detailed flag presence as a detailed source shape can change the legacy wire format for all-zero detailed inputs; source-shape validation should be distinct from flag presence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Rendered Cursor lane splits lack focused regression tests
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Renderers and PR summaries should gate lane splits on component availability rather than monetary truthiness, but focused coverage is missing for detailed Cursor cost lines—including `$0.00` components—and top-runs aggregate/lane formatting. Aggregate-only grammar should also be explicitly preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

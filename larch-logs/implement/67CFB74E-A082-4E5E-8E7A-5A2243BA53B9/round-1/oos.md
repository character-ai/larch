### FINDING_1: [OUT_OF_SCOPE] architecture read/parse round-trip gap
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The architectural-invariants read path is inconsistent across sibling workflow invariants: some entries round-trip paragraph prose while others collapse to headings, which leaves prompts with uneven normative detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: follow-up to either reformat siblings as `- Why:` bullets or extend `parse_invariant_entries` to preserve paragraph bodies.
  - From cursor-specialist-edge-cases: Reformat siblings to `- Why:` bullets or extend `parse_invariant_entries` to preserve paragraph bodies in a follow-up PR.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_2: [OUT_OF_SCOPE] paragraph-body regression coverage gap
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The parser and current parity coverage do not fully protect the paragraph-body round-trip for I-Stale-1, so a future prose-only edit could pass diff review while silently dropping normative text on the read surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a golden test that asserts read output includes I-Stale-1 full body, or extend the parser to retain paragraph prose.
  - From cursor-specialist-testing: Add a targeted golden test asserting all four I-Stale-1 Why lines appear in read output, or file a follow-up to extend parse_invariant_entries for paragraph round-trip.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] bgjob re-entry fingerprint enforcement gap
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Some bgjob rejoin consumers still lack universal fingerprint enforcement, so stale result envs or cached verdicts could be consumed after input drift on surfaces not yet covered by note_consumable-style checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Audit rejoin consumers per the invariant mechanical-backing note and file targeted enforcement follow-ups.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false


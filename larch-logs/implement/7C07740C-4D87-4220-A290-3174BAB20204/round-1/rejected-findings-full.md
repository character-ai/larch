### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `is_bool` key list formatting vs `require_key` style in `ship-pr.sh`

- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `is_bool` for-loop key list is one long line while `require_key` uses wrapped line continuations, making future diffs and readability inconsistent when editing boolean keys beside the wrapped `require_key` block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


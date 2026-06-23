### FINDING_4: Go-through-each flow lacks Python-owned ordered finding-id enumeration
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `gate-b-finding-line` requires a numeric `FINDING_N`, but `gate-b-counts` emits only totals and the plan says to iterate "for each finding" without a Python-owned ordered ID list. Accepted artifacts can be non-contiguous because tally appends only accepted items from sorted FINDING ids (e.g. FINDING_1 and FINDING_3 when FINDING_2 was rejected). A 1..ACCEPTED_COUNT loop would call unknown id 2, fail Step 3.5, or skip FINDING_3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Have the same Python row renderer emit an ordered machine surface, such as `FINDING_IDS=1,3` from `gate-b-counts` plus ordinal/total for headers, or add a single verb that emits all one-by-one prompt lines in order. Update the Approval Gates one-by-one instructions to iterate that Python-emitted list, not an implied contiguous range.
```



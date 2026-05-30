### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:397-402
- **Concern**: Plan cites lines 397-402 as enforcing Gate A/B --snapshot-trailers / --dedup on $SKILL_MD. Scenario: Lines 397-398 grep gate-b-dedup-plan.sh on $APPROVAL_MD only; only 399-402 are $SKILL_MD snapshot/dedup pins. A reader may think 397-398 are SKILL pins and skip needed approval/discussion literal work at 403/407
- **Proposed resolution**: Reword plan Context and UPDATED test-design-structure bullets to 399-402 for $SKILL_MD; call out 397-398 as $APPROVAL_MD script-presence pins separate from the 403/407 snapshot literal tightening



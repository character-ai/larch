# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_3: cap_hit grouped test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The grouped `cap_hit` regression test checks counters, sidecars, and ledger rows but does not assert `DISPATCH_OK=true`, so some dispatch failure shapes could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Bug A rerun test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The second invocation in the Bug A rerun block does not assert `DISPATCH_OK=true`, making settlement failures harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.



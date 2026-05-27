### FINDING_3: cap_hit grouped test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The grouped `cap_hit` regression test checks counters, sidecars, and ledger rows but does not assert `DISPATCH_OK=true`, so some dispatch failure shapes could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.




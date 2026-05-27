### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: Bug A test lacks direct ledger-truncation assertion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The two-run Bug A regression relies on counters and output content but does not directly assert stale ledger rows were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: Unused first-run ledger variable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Bug A test stores `first_run_group_ledger` only for a non-empty check, creating reader noise and implying later assertions that do not exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=2

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: cap_hit grouped test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The grouped `cap_hit` regression test checks counters, sidecars, and ledger rows but does not assert `DISPATCH_OK=true`, so some dispatch failure shapes could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: Bug A rerun test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The second invocation in the Bug A rerun block does not assert `DISPATCH_OK=true`, making settlement failures harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=2

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: Phase-2 grouped cap_hit path lacks direct regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The tests cover grouped `cap_hit` dedup for the current path but do not directly exercise a phase-2 grouped `cap_hit` ledger write, leaving that branch vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2


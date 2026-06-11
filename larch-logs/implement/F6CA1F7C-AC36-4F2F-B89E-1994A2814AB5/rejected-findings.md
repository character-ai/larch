# Rejected Findings

## Round 1

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Makefile PHONY list has a phantom check-main-sync target
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-fidelity-output.txt
- **Severity**: important
- **Concern**: `.PHONY` names `test-check-main-sync-strip-body`, while the recipe and shard use `test-check-main-sync`. This creates drift and can make `make` treat the real harness incorrectly if a same-named file appears.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Replace test-check-main-sync-strip-body with test-check-main-sync.
  - From cursor-specialist-testing-output.txt: Restore test-check-main-sync and test-record-plan-review-round-timing names; re-run test-harness-shards-coverage.sh.
  - From dyn-cutover-fidelity-output.txt: Align `.PHONY` with the real target name `test-check-main-sync` (drop the `-strip-body` suffix unless a second target is added).


Vote tally: YES=1 NO=2 JUDGE_ERROR=0



## Round 2

6:FINDING_11_OUTCOME=rejected
9:FINDING_12_OUTCOME=rejected
12:FINDING_13_OUTCOME=rejected
15:FINDING_14_OUTCOME=rejected
18:FINDING_15_OUTCOME=rejected
21:FINDING_16_OUTCOME=rejected
24:FINDING_17_OUTCOME=rejected
27:FINDING_18_OUTCOME=rejected
32:FINDING_3_OUTCOME=rejected
35:FINDING_4_OUTCOME=rejected
38:FINDING_5_OUTCOME=rejected
41:FINDING_6_OUTCOME=rejected
44:FINDING_7_OUTCOME=rejected
47:FINDING_8_OUTCOME=rejected
50:FINDING_9_OUTCOME=rejected



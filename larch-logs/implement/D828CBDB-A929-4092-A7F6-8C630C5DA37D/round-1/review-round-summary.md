# Review Round 1

- Mode: `diff`
- 6 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Bug B stale sentinel recovery can skip filing new OOS
- **Reviewer(s)**: codex-specialist-correctness, dyn-dyn-oos-aggregation
- **Severity**: important
- **Concern**: Cross-session recovery still keys restored Filed URLs by `OOS_N` only, and the current prepare flow can let that stale mapping mark newly promoted blocks as already filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: "Treat sentinel maps as valid only for matching block identity, not just OOS_N; when identity cannot be proven, leave current blocks unfiled, remove the restored sentinel, and fall through to ready."
  - From dyn-dyn-oos-aggregation: "Run cross-session recovery before promotion, or gate URL recovery on `_aggregate_block_identity` (or equivalent) so sequence reuse cannot attach stale `Filed URL` lines to newly promoted blocks; only after that, evaluate unfiled blocks and apply `skip-sentinel`."


### FINDING_4: Missing regression coverage for plan-listed design prepare scenarios
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The design prepare/sentinel/pool plan scenarios around Bug B, pool-before-sentinel ordering, and cross-session cache recovery are not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Add cross-session cache plus new unfiled block test and important pool plus recovered sentinel test expecting ready"
  - From cursor-specialist-testing: "Add file_oos_prepare_main tests for each plan-listed prepare scenario including Bug B sentinel ordering"


### FINDING_5: Filed URL annotations destabilize aggregate identity
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Including Filed URL lines in aggregate identity makes an already-filed block look different on retry or resume, which can re-promote and re-file the same OOS blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: "Strip Filed URL annotation lines from aggregate identity and test annotated accepted-sink retries."
  - From codex-specialist-testing: "Strip Filed URL lines from aggregate identity and add a regression test for prepare after annotate with a sentinel and unchanged aggregate pool."


### FINDING_6: Missing review_tally serialize-then-promote regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no regression test for the emit-tally path where serialization must happen before promotion, so an ordering change could wipe promoted blocks unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add emit-tally test with OOS_ACCEPTED_COUNT>0 non-empty oos.md plus qualifying pool; assert promoted blocks survive serialize and OOS_FILING_COUNT exceeds vote count"


### FINDING_7: Missing security exclusion regression tests for the new pool path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The new pool path is not tested for security exclusion, so security OOS could leak into public filing if the holdback regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add tally/prepare tests with security plus qualifying public items asserting no pool append and no promotion"


### FINDING_9: Bug A once-only retry contract lacks a mechanized test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Repeated empty `/issue` stdout could still complete Step 5b or loop without sentinel enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add step5b orchestration/structure test for retry sentinel and second-failure halt"



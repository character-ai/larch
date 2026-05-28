### FINDING_10: main-agent-vote-required skips OOS accumulation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The `main-agent-vote-required` branch exits before `_accumulate_round_oos`, so a round with accepted OOS and main-agent vote required can leave the cumulative OOS file empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: symlinked snapshot sources produce partial forensic archives
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_snapshot_round_dir` skips symlinked sources per file instead of failing the snapshot or marking degraded, which can publish incomplete round forensic artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: unit harness misses plan-required loop cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` lacks acceptance-listed cases for OOS accumulation, dedup reset, convergence streaks, degraded streak reset, severity defaults, important-count gating, revise exit failure, and legacy golden fixtures, allowing core loop behavior to regress without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: revise sub-allowlist lacks fail-closed publish coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-log-publish` covers happy-path revise artifacts but not disallowed files under `round-N/revise`, so production publish failures from unexpected revise files may escape tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: relevant-checks omits plan-review-loop.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Changes to `skills/design/scripts/plan-review-loop.md` do not trigger the same loop or integration tests as `plan-review-loop.sh`, allowing contract drift to merge without relevant checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: SECURITY.md underdocuments published plan-review artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes plan-review publish as `findings-classification.tsv` only, while current code publishes a broader allowlist including ballots and vote outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: duplicate collector parsing can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Collector STATUS parsing exists in both `_parse_collect_records` and `_run_plan_review_round`, so future fixes may update only one path and break zero-finding or degradation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_21: Gate B routing contradicts emit-plan-failed handling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` and `SKILL.md` disagree on `emit-plan-failed`: one path treats it as manual-choice routing while another auto-applies, risking a second apply against an already revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: integration harness misses required multi-round and Gate B scenarios
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-multi-round-integration.sh` omits several plan-required scenarios, including SKILL Step 3 KV parsing, Gate B passive-summary/fallback routing, revision-failed handoff, cross-entry cleanup, plan identity, publish-failure staging checks, convergence/streak behavior, and stronger cap-hit assertions. These gaps allow Step 3 rehydration, Gate B routing, cleanup, revision failure, or cap semantics to regress while integration tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: loop can report complete without running a round
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The terminal exit after the loop is effectively unreachable for normal runs, but `--round-num` greater than `--round-cap` could skip the loop and exit successfully with `LOOP_STATUS=complete`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: cumulative accepted OOS is truncated across rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Both tally and empty-artifact paths can truncate `oos-accepted-design.md` during later rounds, losing OOS accepted in earlier rounds before Step 5b files them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: OOS accumulation includes rejected or exonerated items
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_accumulate_round_oos` merges all OOS blocks from `oos.md`, so rejected or exonerated OOS items can enter `oos-accepted-design.md` and later be filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.



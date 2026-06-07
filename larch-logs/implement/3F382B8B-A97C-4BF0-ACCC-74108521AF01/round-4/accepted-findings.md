### FINDING_10: Manual Gate C re-run can retain stale cumulative artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manual Step 3/Gate C re-entry does not consistently reset cumulative in-scope and OOS accepted artifacts, so stale prior-round findings or OOS items can be counted, summarized, or filed after a fresh review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clear cumulative accepted/OOS artifacts on manual Step 3 re-entry (new design-step3-state action or Gate C hook); preserve accumulation only for auto-continuation-entry.
  - From codex-specialist-edge-cases-output.txt: Clear oos-accepted-design.md and .oos-accepted-design.prev.md on direct-review-entry while preserving them for auto-continuation-entry.


### FINDING_12: New Makefile test target is missing from harness shards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-persist-retally-step3-env` is not included in any `test-harnesses-N` shard, so shard coverage and `make lint`/CI can fail or omit the new regression harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-persist-retally-step3-env to an appropriate harness shard and document in docs/linting.md
  - From codex-specialist-testing-output.txt: Add test-persist-retally-step3-env to an appropriate test-harnesses-N prerequisite and update docs if needed.


### FINDING_13: MainAgent re-tally can drop prior-round accepted OOS items
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: important
- **Concern**: On the `main-agent-vote-required` path, successful re-tally rewrites only current-round accepted OOS and lacks the in-scope cumulative merge equivalent, so earlier-round OOS acceptances can disappear from summary and filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: After successful MainAgent re-tally, merge `oos-accepted-design.md` into a cumulative OOS artifact the same way in-scope findings are handled (e.g., call `_accumulate_round_oos` with the saved `.oos-accepted-design.prev.md`, or add an OOS merge helper in `persist-retally-step3-env.sh` using the existing description-key dedup), and add a multi-round harness case with prior-round OOS plus a later-round `main-agent-vote-required` re-tally.



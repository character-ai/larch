### FINDING_1: Round docs imply voters always run after aggregation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/review-core.md` stage 3 still describes voter dispatch as the next step after aggregation, but the new `REASON=ok` plus `MERGED_COUNT=0` path skips voter dispatch and emits `zero-findings`. This can mislead operators debugging empty aggregate merges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: agg-zero test overmatches VOTER_ output
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/test-review-core.sh` checks the full `review-core` output for any `VOTER_` text. Future unrelated KV lines or breadcrumbs containing `VOTER_` could fail `agg-zero` even when voter dispatch was correctly skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Dynamic plan-review fallback pairing assertion is weaker than static assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-dispatch-plan-review-panel.sh` still uses a weaker dynamic fallback-group check than the new static `jq -s -e length==2` pairing assertion. Malformed dynamic slot pairings could pass when analogous static-slot bugs would be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Correctness reviewer included commit listing instead of a behavioral finding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The reviewer output entries for commits `45186750`, `16e17510`, and `6d34e1e3` are commit inventory and plan-verification prose rather than actionable behavioral risks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: Missing regression for absent MERGED_COUNT degrade path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/test-review-core.sh` lacks a stub case for `REASON=ok` with no `MERGED_COUNT` line. A future refactor could default an absent count to zero and incorrectly skip voters without failing the current `agg-zero` test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Missing regression for ok aggregate with nonzero MERGED_COUNT
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/test-review-core.sh` lacks a stub case for `REASON=ok` with `MERGED_COUNT>0`. A broadened short-circuit could skip voting for aggregates that contain findings while existing disabled-aggregator tests remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Harness contract doc omits agg-zero behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/test-review-core.md` does not document the new aggregate-zero-success stub behavior or its expected artifacts, so contributors may miss that `agg-zero` now asserts voter skipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Decompose harness uses older pairing assertion pattern
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-decompose-panel-dispatch.sh` still uses the older pairing `jq` pattern, creating the same class of false negative as the plan-review dynamic slot assertions if parity is desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Empty-merge short-circuit trusts aggregate KV without findings guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/review-core.sh` skips voter dispatch based only on aggregate env values `REASON=ok` and `MERGED_COUNT=0`. If the aggregate env is corrupt or substituted while `findings.md` still contains finding blocks, the review can finish as `zero-findings` incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Empty-merge branch does not validate attestation line content
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/review-core.sh` keys the empty-merge short-circuit on `REASON=ok` and `MERGED_COUNT=0`, not on the attestation sentinel in `findings.md`. The source marked this out of scope because the plan explicitly accepted this edge case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] REVIEW_CORE_*_SH override surface can substitute review scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `REVIEW_CORE_*_SH` environment hooks allow aggregate, voter, or tally script substitution when the implement shell environment is attacker-controlled. The source identifies this as a pre-existing trust-boundary issue amplified by the new empty-merge skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Aggregator-disabled mode still dispatches voters with MERGED_COUNT=0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LARCH_AGGREGATOR_DISABLED=1` still reaches voter dispatch even with `MERGED_COUNT=0`, causing unnecessary voter launches. The source marked this unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

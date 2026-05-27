### FINDING_10: [OUT_OF_SCOPE] Empty-merge branch does not validate attestation line content
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/review-core.sh` keys the empty-merge short-circuit on `REASON=ok` and `MERGED_COUNT=0`, not on the attestation sentinel in `findings.md`. The source marked this out of scope because the plan explicitly accepted this edge case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_11: [OUT_OF_SCOPE] REVIEW_CORE_*_SH override surface can substitute review scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `REVIEW_CORE_*_SH` environment hooks allow aggregate, voter, or tally script substitution when the implement shell environment is attacker-controlled. The source identifies this as a pre-existing trust-boundary issue amplified by the new empty-merge skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_12: [OUT_OF_SCOPE] Aggregator-disabled mode still dispatches voters with MERGED_COUNT=0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LARCH_AGGREGATOR_DISABLED=1` still reaches voter dispatch even with `MERGED_COUNT=0`, causing unnecessary voter launches. The source marked this unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_3: [OUT_OF_SCOPE] Dynamic plan-review fallback pairing assertion is weaker than static assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-dispatch-plan-review-panel.sh` still uses a weaker dynamic fallback-group check than the new static `jq -s -e length==2` pairing assertion. Malformed dynamic slot pairings could pass when analogous static-slot bugs would be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_8: [OUT_OF_SCOPE] Decompose harness uses older pairing assertion pattern
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-decompose-panel-dispatch.sh` still uses the older pairing `jq` pattern, creating the same class of false negative as the plan-review dynamic slot assertions if parity is desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted



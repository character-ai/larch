### FINDING_33: [OUT_OF_SCOPE] correctness: skills/design/scripts/record-plan-review-round-timing.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Design deferred helper lacks ledger idempotency guard present on implement helper. A future duplicate call could append two round rows for the same round number and inflate analytics. Add the same round-number dedup awk guard used in record-implement-review-round-timing.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_34: [OUT_OF_SCOPE] correctness: skills/design/scripts/plan-review-loop.sh:439-451
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] round-start-s snapshot survival is only covered by allowlist unit test. Allowlist drift or snapshot ordering changes could prune MAV start timestamps without CI catching it. Add plan-review-loop integration assert that round-start-s remains after _snapshot_terminal_exit_preserving_status on MAV path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted



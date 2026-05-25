### OOS_1: Doc-code mismatch in narrow-trigger retry regex
- **Description**: `skills/review/scripts/aggregate-findings.md` documents the narrow-trigger retry as keying only on `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`, but the regex in `_agg_pipeline_for_candidate` (in `skills/review/scripts/aggregate-findings.sh`) also matches `empty_merge_from_nonempty_input`. The cleanup in this issue does not introduce or fix this mismatch — it predates the cleanup. After deletion, the broader regex still fires when the model writes the attestation correctly and the validator rejects post-#2782; for the no-attestation sub-case, the validator emits a non-token error and no retry fires (which matches the doc). Either narrowing the regex to match the doc or updating the doc to enumerate both tokens would resolve the inconsistency. Affects: `skills/review/scripts/aggregate-findings.md` (the runtime-contract bullet) and `skills/review/scripts/aggregate-findings.sh` (the `_agg_pipeline_for_candidate` regex around the `grep -Eq` line). Doc edit is the lower-risk fix.
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design


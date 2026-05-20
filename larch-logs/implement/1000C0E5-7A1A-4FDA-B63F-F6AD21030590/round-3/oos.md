### FINDING_2: [OUT_OF_SCOPE] **correctness** — [`scripts/collect-agent-results.sh:1262-1310`](scripts/collect-agent-results.sh) — NS-retry success paths set `RESULTS[IDX]` with `REVIEWER_FILE=$ORIG_OUTPUT` only; structured publish failure for the TSV/JSONL copy leaves `STRUCTURED_SIDECAR` on the validated retry-path sidecar, which should still exist because `preserve_and_publish_ns_retry` does not remove `NS_RETRY_OUTPUT`. No stale `NS_RETRY_OUTPUT` value is written into `RESULTS[IDX]` on the success path.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.sh:1262-1310`](scripts/collect-agent-results.sh) — NS-retry success paths set `RESULTS[IDX]` with `REVIEWER_FILE=$ORIG_OUTPUT` only; structured publish failure for the TSV/JSONL copy leaves `STRUCTURED_SIDECAR` on the validated retry-path sidecar, which should still exist because `preserve_and_publish_ns_retry` does not remove `NS_RETRY_OUTPUT`. No stale `NS_RETRY_OUTPUT` value is written into `RESULTS[IDX]` on the success path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] **correctness** — [`scripts/collect-agent-results.sh:1321-1358`](scripts/collect-agent-results.sh) — `emit_summary_result` still only forwards the four summary keys; full emission still runs `with_structured_sidecar_field` then `tr '|' '\n'`. Structured NS-retry success rows keep the canonical field order `REVIEWER_FILE|TOOL|STATUS|EXIT_CODE|STRUCTURED_SIDECAR|FAILURE_REASON`; substantive NS-retry success rows omit `STRUCTURED_SIDECAR` in the pipe record and rely on the existing `with_structured_sidecar_field` pass-through / padding behavior, unchanged by this branch.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.sh:1321-1358`](scripts/collect-agent-results.sh) — `emit_summary_result` still only forwards the four summary keys; full emission still runs `with_structured_sidecar_field` then `tr '|' '\n'`. Structured NS-retry success rows keep the canonical field order `REVIEWER_FILE|TOOL|STATUS|EXIT_CODE|STRUCTURED_SIDECAR|FAILURE_REASON`; substantive NS-retry success rows omit `STRUCTURED_SIDECAR` in the pipe record and rely on the existing `with_structured_sidecar_field` pass-through / padding behavior, unchanged by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/collect-agent-results.sh:1231-1266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NS_RETRY_OUTPUT still uses ORIG_OUTPUT%.txt stripping pre-existing in this area. Unusual non .txt OUTPUT_FILE values get odd retry sibling names. Not introduced by this branch leave for a dedicated path hygiene change if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/collect-agent-results.sh:1231-1232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] NS retry path uses ORIG_OUTPUT%.txt while first_pass_sidecar_path handles non-.txt. Weird retry artifact naming when OUTPUT_FILE is not *.txt. Pre-existing; fix in a dedicated path-normalization change if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected


# Review Round 2

- Mode: `diff`
- 14 accepted, 8 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/review/scripts/aggregate-findings.md:26 SECURITY.md:81 CHANGELOG.md:12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Docs and changelog quote the attestation pattern without the leading [[:space:]]* prefix that production code uses at aggregate-findings.sh:687. An operator compares dispatcher behavior to SECURITY.md during a padded-attestation incident and concludes the gate should reject lines the running script accepts, wasting triage time. Sync aggregate-findings.md, SECURITY.md, and CHANGELOG.md to the exact ERE in aggregate-findings.sh:687 and document leading-whitespace tolerance on the attestation alternation only.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/review/scripts/aggregate-findings.md:26; SECURITY.md:81; CHANGELOG.md:12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Documentation and changelog quote a stricter --require-result-pattern than aggregate-findings.sh:687 and the harness assert. Operators debugging padded attestation or copy-pasting the ERE from SECURITY.md will expect leading whitespace to fail at the dispatcher gate; production accepts [[:space:]]* before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED. Update aggregate-findings.md SECURITY.md and CHANGELOG.md to the exact shipped ERE including [[:space:]]* on the attestation alternation.
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: skills/review/scripts/test-aggregate-findings.sh:184-191
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dead stub merge kind zero_findings_padded_attest_rejected after real-dispatcher rewrite. Maintainers may think stub path still exercises padded attestation at the pattern gate. Remove unused stub branch or document why it remains.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/review/scripts/test-aggregate-findings.sh:1230-1251
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] dispatcher_rejects_pseudo_finding_heading lacks --require-result-pattern argv assertion. Regression that removes the flag could still pass pseudo-heading fallback behavior. Add dispatch-wrapper argv log and grep for the dual-gate ERE like codex_primary_narration_routes_to_phase2_cursor.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: SECURITY.md:114; skills/review/scripts/aggregate-findings.md:26; skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented --require-result-pattern ERE omits [[:space:]]* before the attestation alternation; the script and tests use the looser form after bd1f13c8. Security reviewers or incident responders trust SECURITY.md and mis-classify which Codex/Cursor outputs pass the dispatcher gate, weakening audit of the #2881 fix. Pick one canonical ERE and sync SECURITY.md, aggregate-findings.md, aggregate-findings.sh, and test assertions.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dispatcher pattern in code allows leading whitespace before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED but aggregate-findings.md SECURITY.md and CHANGELOG.md document a stricter pattern without [[:space:]]*. An operator reads SECURITY.md and expects padded attestation to fail at the dispatcher; production accepts it (see padded-attest real-dispatch test) and only the validator decides exhaustion. Align prose in aggregate-findings.md SECURITY.md and CHANGELOG.md with the exact ERE at aggregate-findings.sh:687 or revert the code to match the documented stricter gate.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/review/scripts/aggregate-findings.sh:739-769
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] MERGE_PIPELINE_RC case has no default branch and the script ends immediately after esac. If _agg_pipeline_for_candidate ever sets an unexpected RC, the process exits without emit_result and review-core.sh sees no REASON. Add a *) branch that emits validation-failed (or validation-exhausted) via emit_result and exit 0.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] case on MERGE_PIPELINE_RC has no default branch. Unexpected MERGE_PIPELINE_RC leaves the script without emit_result; review-core may proceed with missing REASON keys. Add *) default mapping to validation-failed or dispatch-failed with emit_result and exit 0.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Live require-result-pattern adds [[:space:]]* before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED but plan step 2 CHANGELOG SECURITY and aggregate-findings.md document the narrower ERE without that prefix. Padded attestation lines pass the dispatcher per test-aggregate-findings.sh 702-727 while docs say full-line token with no leading whitespace; security and operator docs mis-predict dispatch-failed vs validation-exhausted. Align code and all cited docs to one canonical ERE or revert the bd1f13c8 widening and document padded attestation as dispatcher rejection.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/review/scripts/aggregate-findings.md:26
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Contract prose describes plan ERE and full-line attestation without leading whitespace allowance. Readers expect padded attestation to fail at pattern gate; runtime and tests accept it and map to validation-exhausted. Update the behavior bullet and pattern quote to match aggregate-findings.sh and harness assertions.
- **Suggested revision**: Address the concern above.


### FINDING_26: architecture: skills/review/scripts/test-aggregate-findings.sh:184-191
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Stub kind zero_findings_padded_attest_rejected is defined but never invoked; plan REASON matrix row lacks dedicated stub case. Plan-required stub regression for padded attestation matrix row is missing though real-dispatcher test partially covers behavior. Add stub case asserting REASON=validation-exhausted or delete unused stub kind.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/review/scripts/test-aggregate-findings.sh:1230-1251
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] pseudo-heading fallback test does not assert --require-result-pattern on the real dispatcher path. Removing --require-result-pattern from dispatch_args could regress #2881 while pseudo-heading and phase-2 fallback tests still pass. Use write_real_dispatch_wrapper plus AGGREGATE_DISPATCH_ARGV_LOG and grep for the dual-gate ERE like the codex_primary and padded-attestation cases.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/review/scripts/aggregate-findings.md:26
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Documented --require-result-pattern omits [[:space:]]* before attestation; runtime and tests use it after bd1f13c8. Operator compares padded attestation failure to docs without leading-space allowance and misdiagnoses validation-exhausted. Update aggregate-findings.md SECURITY.md and CHANGELOG to match aggregate-findings.sh:687.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] case on MERGE_PIPELINE_RC has no default; unexpected RC can exit without emit_result. Future MERGE_PIPELINE_RC=3 leaves review-core with empty REASON and stale findings.md. Add *) branch: REASON=validation-failed emit_result exit 0.
- **Suggested revision**: Address the concern above.



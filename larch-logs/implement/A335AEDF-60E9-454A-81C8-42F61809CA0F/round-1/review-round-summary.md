# Review Round 1

- Mode: `diff`
- 10 accepted, 8 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/review/scripts/test-aggregate-findings.sh:1164-1198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] codex_primary_narration test omits --require-result-pattern assertion required by plan A future regression that drops the dual-gate flag could still pass phase-2 recovery tests while narration-only Codex output is accepted at dispatch boundary Capture dispatch argv or stderr in WR and grep for --require-result-pattern and the exact ERE like sidecar-resolution case
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/review/scripts/test-aggregate-findings.sh:688-701
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Padded-attestation harness uses dispatch stub that bypasses --require-result-pattern while production gate rejects leading-whitespace attestation lines. Codex returns padded attestation only; dispatcher never accepts candidate; REASON=dispatch-failed and review continues instead of validation-exhausted exit-2 stall. Add external-stub integration test for padded attestation; align pattern (optional leading whitespace on attestation branch) or document and test dispatch-failed as terminal.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/review/scripts/test-review-core.sh:422-423
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] fix-breadcrumbs case no longer asserts consolidating-findings breadcrumb under LARCH_QUIET_BREADCRUMBS=1. Breadcrumb regression in review-core collect stage would not fail CI. Restore LARCH_QUIET_BREADCRUMBS=1 and breadcrumb assertion or remove/rename the duplicate case.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/review/scripts/test-aggregate-findings.sh:1174-1198
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] codex_primary_narration integration test omits --require-result-pattern assertion required by plan item 5f. Pattern flag could be dropped from aggregate-findings dispatch_args without failing this case. Grep dispatch stderr or stub argv log for --require-result-pattern and expected ERE in this case.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pattern gate rejects leading/trailing whitespace on attestation lines that the validator accepts via strip(). All phases return ` LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED `; dispatcher never accepts; `DISPATCH_OK=false` and voters run on unmerged findings while stub tests expect validation-exhausted. Allow `[[:space:]]*` before the attestation alternation only; add real-dispatcher regression; align aggregate-findings.md/SECURITY.md prose with gate behavior.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/review/scripts/test-aggregate-findings.sh:693-701
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Padded-attestation REASON tests use stub dispatch that does not enforce --require-result-pattern. Production and stub paths diverge; CI can pass while padded attestation mis-classifies in real runs. Mirror codex_primary_narration test with real dispatch-with-waterfall.sh and padded attestation fixture.
- **Suggested revision**: Address the concern above.


### FINDING_24: code-quality: skills/review/scripts/test-review-core.sh:422-423
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] fix-breadcrumbs test no longer asserts consolidating-findings breadcrumb. Quiet-breadcrumb regression for review-core.sh:366 can slip without CI failure. Restore LARCH_QUIET_BREADCRUMBS=1 and breadcrumb assertion or delete redundant case.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/review/scripts/test-aggregate-findings.sh:1174-1198
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] codex_primary_narration_routes_to_phase2_cursor omits plan-required assertion (f) for --require-result-pattern on the real dispatcher path. Stub-only siblings grep the pattern flag; the primary integration test does not. Removing --require-result-pattern from aggregate-findings.sh could slip through while narration→phase2 behavior still appears to work in limited runs. Add argv/stderr capture in the codex_primary block and grep for --require-result-pattern and the dual-gate ERE, mirroring test-dispatch-with-waterfall.sh.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pattern gate rejects whitespace-padded LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED lines that the post-dispatch validator accepts via line.strip(). All phases return STATUS=OK padded attestation only; dispatcher rejects every phase; REASON=dispatch-failed and voters run on unmerged findings instead of validation-exhausted stall. Allow optional leading whitespace on the attestation alternation only; add real-dispatcher padded-attestation integration test.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review/scripts/test-aggregate-findings.sh:688-701
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] zero_findings_padded_attest_rejected uses stub dispatch that bypasses the pattern gate. Production gate/validator split for padded attestation can regress without failing this test. Add write_external_tool_stubs + real dispatch-with-waterfall case for padded-only attestation across phases.
- **Suggested revision**: Address the concern above.



### FINDING_1: code-quality: skills/review/scripts/test-aggregate-findings.sh:1164-1198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] codex_primary_narration test omits --require-result-pattern assertion required by plan A future regression that drops the dual-gate flag could still pass phase-2 recovery tests while narration-only Codex output is accepted at dispatch boundary Capture dispatch argv or stderr in WR and grep for --require-result-pattern and the exact ERE like sidecar-resolution case
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review/scripts/aggregate-findings.sh:751
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] RC=1 warning text always says empty merge Preamble narrow-trigger failures log misleading execution-issues text Rename warning to narrow-trigger validator rejection or branch on stderr token
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pattern ERE duplicated across script docs SECURITY CHANGELOG and tests One-sided edit could leave dispatcher gate and docs/tests inconsistent Centralize pattern in one shell variable at top of aggregate-findings.sh
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/test-aggregate-findings.sh:337-374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_external_tool_stubs duplicates test-dispatch-with-waterfall stubs Stub behavior drift between harnesses causes false confidence Extract shared test stub helper or cross-reference single canonical stub file
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review/scripts/aggregate-findings.md:26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Behavior contract crammed into one giant bullet Harder to keep SECURITY.md and aggregate-findings.md in sync Split into shorter bullets by concern
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/aggregate-findings.sh:99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] count_finding_blocks looser than validator heading contract Pre-existing pseudo-heading edge if gate bypassed Align grep with validator when touching heading rules
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-aggregate-findings.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness doc omits new dispatcher integration coverage Contributors may not discover phase-2 fallback tests Add short section listing dispatcher-layer cases
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pattern gate rejects whitespace-padded LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED lines that the post-dispatch validator accepts via line.strip(). All phases return STATUS=OK padded attestation only; dispatcher rejects every phase; REASON=dispatch-failed and voters run on unmerged findings instead of validation-exhausted stall. Allow optional leading whitespace on the attestation alternation only; add real-dispatcher padded-attestation integration test.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review/scripts/test-aggregate-findings.sh:688-701
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] zero_findings_padded_attest_rejected uses stub dispatch that bypasses the pattern gate. Production gate/validator split for padded attestation can regress without failing this test. Add write_external_tool_stubs + real dispatch-with-waterfall case for padded-only attestation across phases.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Post-dispatch case statement has no default branch when MERGE_PIPELINE_RC is unset. Future _agg_pipeline_for_candidate edit could exit without emit_result stdout keys. Add default *) arm mapping to validation-failed with emit_result exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: skills/review/scripts/aggregate-findings.sh:536-567
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan claims attestation-only duplicate merge yields REASON=ok but validator always RC=1 for attestation + zero blocks + nonempty input. Pre-existing semantic/doc mismatch not introduced by this diff. Address separately if duplicate-only attestation should succeed validation.
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

### FINDING_15: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing optional three-phase test when Codex absent and Cursor narration-only. Phase-3 Claude fallback after double pattern miss is untested in CI. Add codex-absent + cursor-narration + claude-valid integration case asserting PHASE3_SLOTS and ALL_OUTPUT_TOOLS=claude.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.md:91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb doc predicate (LARCH_QUIET_BREADCRUMBS) does not match unconditional emit_breadcrumb call site. Operators may misconfigure breadcrumb expectations. Align review-core.md with lib-quiet gating (pre-existing).
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/test-review-core.sh:446-458
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] aggregator-validation-exhausted test uses aggregate stub not real aggregate-findings narrow-trigger path. Regression in aggregate-findings REASON mapping might not break review-core harness. Add end-to-end case wiring real aggregate stub output (pre-existing gap).
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/dispatch-with-waterfall.sh:275-278` — `STATUS=cap_hit` still bypasses `--require-result-pattern`, so a cap-hit artifact without structured headings can reach the post-dispatch validator and exit as `validation-failed` rather than triggering dispatcher fallback. Pre-existing (#2895); documented as accepted; not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** Session tmpdir trust model — `aggregator-dispatch.env`, `ALL_OUTPUT_FILES_PATH` sidecars, and `aggregate-validate.py` under `$REVIEW_TMPDIR` remain tamperable by anything with write access to the session directory (consistent with `SECURITY.md` retry-metadata posture). Candidate **content** is still gated by the python validator; this PR adds candidate **path** pinning, which is stricter than `decompose-aggregator.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/review/scripts/aggregate-findings.sh:712-714` — `ALL_OUTPUT_FILES_PATH` itself is not required to resolve under `$REVIEW_TMPDIR` before `read -r cand` (same pattern as `decompose-aggregator.sh`). Only the resolved `cand` path is canonicalized. Impact is limited to first-line reads from attacker-chosen sidecar locations when `aggregator-dispatch.env` is tampered; merge content still cannot replace `findings.md` without passing validation.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pattern gate rejects leading/trailing whitespace on attestation lines that the validator accepts via strip(). All phases return ` LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED `; dispatcher never accepts; `DISPATCH_OK=false` and voters run on unmerged findings while stub tests expect validation-exhausted. Allow `[[:space:]]*` before the attestation alternation only; add real-dispatcher regression; align aggregate-findings.md/SECURITY.md prose with gate behavior.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/test-aggregate-findings.sh:693-701
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Padded-attestation REASON tests use stub dispatch that does not enforce --require-result-pattern. Production and stub paths diverge; CI can pass while padded attestation mis-classifies in real runs. Mirror codex_primary_narration test with real dispatch-with-waterfall.sh and padded attestation fixture.
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/review/scripts/aggregate-findings.sh:687-768
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No harness for all-phase narration/pattern miss → dispatch-failed. When every tool returns plan-mode narration, review-core continues with stale findings instead of aggregator-validation-exhausted stall. Add all-phase narration stub test; document dispatch-failed as intentional non-stall in aggregate-findings.md.
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: skills/review/scripts/test-review-core.sh:422-423
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] fix-breadcrumbs test no longer asserts consolidating-findings breadcrumb. Quiet-breadcrumb regression for review-core.sh:366 can slip without CI failure. Restore LARCH_QUIET_BREADCRUMBS=1 and breadcrumb assertion or delete redundant case.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/review/scripts/test-aggregate-findings.sh:1174-1198
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] codex_primary_narration_routes_to_phase2_cursor omits plan-required assertion (f) for --require-result-pattern on the real dispatcher path. Stub-only siblings grep the pattern flag; the primary integration test does not. Removing --require-result-pattern from aggregate-findings.sh could slip through while narration→phase2 behavior still appears to work in limited runs. Add argv/stderr capture in the codex_primary block and grep for --require-result-pattern and the dual-gate ERE, mirroring test-dispatch-with-waterfall.sh.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: CHANGELOG.md:12
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] CHANGELOG bullet is vaguer than the plan draft about which consumer files changed. Harder to audit #2881 doc surface from release notes alone. Name review-core.md, review-and-fix.sh breadcrumb, and test-review-core.sh stub explicitly in the bullet.
- **Suggested revision**: Address the concern above.


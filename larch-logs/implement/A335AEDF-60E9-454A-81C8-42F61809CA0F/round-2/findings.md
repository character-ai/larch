### FINDING_1: code-quality: skills/review/scripts/aggregate-findings.md:26 SECURITY.md:81 CHANGELOG.md:12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Docs and changelog quote the attestation pattern without the leading [[:space:]]* prefix that production code uses at aggregate-findings.sh:687. An operator compares dispatcher behavior to SECURITY.md during a padded-attestation incident and concludes the gate should reject lines the running script accepts, wasting triage time. Sync aggregate-findings.md, SECURITY.md, and CHANGELOG.md to the exact ERE in aggregate-findings.sh:687 and document leading-whitespace tolerance on the attestation alternation only.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/review/scripts/aggregate-findings.sh:739-769
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] MERGE_PIPELINE_RC case has no default branch and the script ends immediately after esac. If _agg_pipeline_for_candidate ever sets an unexpected RC, the process exits without emit_result and review-core.sh sees no REASON. Add a *) branch that emits validation-failed (or validation-exhausted) via emit_result and exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review/scripts/test-aggregate-findings.sh:1230-1251
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] pseudo-heading fallback test does not assert --require-result-pattern on the real dispatcher path. Removing --require-result-pattern from dispatch_args could regress #2881 while pseudo-heading and phase-2 fallback tests still pass. Use write_real_dispatch_wrapper plus AGGREGATE_DISPATCH_ARGV_LOG and grep for the dual-gate ERE like the codex_primary and padded-attestation cases.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/aggregate-findings.sh:687 skills/design/scripts/decompose-aggregator.sh:127-142
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated ALL_OUTPUT_FILES_PATH resolution and divergent doc strings for the same dispatcher contract. Future edits may fix one caller or one doc surface and leave the other stale (already happened for attestation whitespace). Consider a shared resolve_dispatch_candidate helper used by both aggregators.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated commits (#2878, tracking-issue-read, plugin version) mixed with #2881. Reviewers may miss or re-review unrelated surface area. Split PR or add a clear PR summary separating #2881 from drive-by fixes.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern. cap_hit artifacts without FINDING headings reach validation-failed instead of dispatcher fallback. Pre-existing; document or address in a follow-up if desired.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Narrow-trigger RC=1 terminates as validation-exhausted without trying Claude even when Codex/Cursor returned pattern-valid attestation or preamble-only output. Codex phase-1 returns padded LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED on a 25-finding ballot; dispatcher accepts; validator emits empty_merge_from_nonempty_input; Step 5 stalls; Claude never runs though it might merge. Document as accepted in aggregate-findings.md/SECURITY.md or add a post-validator redispatch when narrow-trigger fires on non-Claude tool.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review/scripts/aggregate-findings.md:26
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Documented --require-result-pattern omits [[:space:]]* before attestation; runtime and tests use it after bd1f13c8. Operator compares padded attestation failure to docs without leading-space allowance and misdiagnoses validation-exhausted. Update aggregate-findings.md SECURITY.md and CHANGELOG to match aggregate-findings.sh:687.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] case on MERGE_PIPELINE_RC has no default; unexpected RC can exit without emit_result. Future MERGE_PIPELINE_RC=3 leaves review-core with empty REASON and stale findings.md. Add *) branch: REASON=validation-failed emit_result exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan optional tests for codex-absent three-phase chain and indented-heading gate not present. Phase-3-only recovery or indented-heading gate regression may slip CI. Add optional harness cases from the implementation plan.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: skills/review/scripts/test-review-core.sh:348
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Most run_core tests keep LARCH_AGGREGATOR_DISABLED=1 so review-core rarely hits real aggregate-findings dispatch. Limited integration coverage of collapsed aggregator inside review-core; pre-existing. Consider a review-core test without LARCH_AGGREGATOR_DISABLED using stub dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/aggregate-findings.md:26; SECURITY.md:81; CHANGELOG.md:12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Documentation and changelog quote a stricter --require-result-pattern than aggregate-findings.sh:687 and the harness assert. Operators debugging padded attestation or copy-pasting the ERE from SECURITY.md will expect leading whitespace to fail at the dispatcher gate; production accepts [[:space:]]* before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED. Update aggregate-findings.md SECURITY.md and CHANGELOG.md to the exact shipped ERE including [[:space:]]* on the attestation alternation.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan optional indented-heading regression test is missing. A future change could reintroduce [[:space:]]* before ### FINDING_ in the pattern without CI catching mismatch with count_finding_blocks. Add real-dispatcher case: indented ### FINDING_1: rejected at phase 1 valid heading at phase 2.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan optional codex-absent three-phase narration→Claude test is missing. Codex absent plus Cursor narration-only plus Claude valid output is only partially covered by codex_absent_runs_cursor_in_phase2. Add integration test with CODEX_PRESENT=false narration Cursor stub and Claude ballot asserting PHASE3_SLOTS and ALL_OUTPUT_TOOLS=claude.
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

### FINDING_18: architecture: skills/review/scripts/aggregate-findings.sh:712-736
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ALL_OUTPUT_FILES_PATH sidecar path is not constrained to REVIEW_TMPDIR before read; only the resolved candidate path is canonicalized. Within the same-user tmpdir threat model, a tampered aggregator-dispatch.env could point the sidecar at another readable file and leak its first line into path-resolution logic before rejection. Canonicalize and reject all_output_files_path unless it resolves under REVIEW_TMPDIR_CANON, then read cand.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dispatcher pattern in code allows leading whitespace before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED but aggregate-findings.md SECURITY.md and CHANGELOG.md document a stricter pattern without [[:space:]]*. An operator reads SECURITY.md and expects padded attestation to fail at the dispatcher; production accepts it (see padded-attest real-dispatch test) and only the validator decides exhaustion. Align prose in aggregate-findings.md SECURITY.md and CHANGELOG.md with the exact ERE at aggregate-findings.sh:687 or revert the code to match the documented stricter gate.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] case on MERGE_PIPELINE_RC has no default branch. Unexpected MERGE_PIPELINE_RC leaves the script without emit_result; review-core may proceed with missing REASON keys. Add *) default mapping to validation-failed or dispatch-failed with emit_result and exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/review/scripts/test-aggregate-findings.sh:584-598
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] zero_findings_no_attest uses stub dispatch that skips pattern gate. Production all-narration failure yields dispatch-failed; harness asserts validation-failed and can hide regressions in warning text or DISPATCH_OK handling. Add real-dispatcher integration test for all-phase narration-only; relabel stub test as validator-only if kept.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing optional phase-3 and indented-heading pattern-gate tests from the plan. Codex-absent Cursor-narration-only path and indented-heading rejection are unguarded against future dispatcher regressions. Add PATH-stub tests for phase-3 Claude recovery and indented pseudo-heading rejection at the gate.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] architecture: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern by design. Documented accepted behavior: cap-hit without FINDING headings yields validation-failed not validation-exhausted. No change unless product policy changes.
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


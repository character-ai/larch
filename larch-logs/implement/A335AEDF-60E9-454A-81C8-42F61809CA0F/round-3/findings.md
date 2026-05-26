### FINDING_1: code-quality: skills/review/scripts/test-aggregate-findings.sh:329-370
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated codex/cursor stub helpers mirror test-dispatch-with-waterfall.sh but omit claude stub. Stub behavior change in one harness leaves the other passing while aggregate integration tests mis-simulate production launchers. Extract shared external-agent stub fixture sourced by both harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] --require-result-pattern ERE is copy-pasted across script docs CHANGELOG SECURITY and many grep assertions. Future pattern tweak updates script but greps/docs drift causing silent loss of regression coverage. Centralize pattern in one shell variable used by script and tests.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review/scripts/test-aggregate-findings.sh:694-1270
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four real-dispatch integration cases repeat identical PATH stub wrapper and env boilerplate. Each new dispatcher scenario copies 12+ lines increasing merge conflict and setup mistakes. Add run_aggregate_real_dispatch_case helper to DRY setup.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/test-review-core.sh:266-294
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] aggregate-dispatch stub emits only ALL_OUTPUT_FILES not ALL_OUTPUT_FILES_PATH. review-core tests never exercise primary candidate resolution path used in production. Emit ALL_OUTPUT_FILES_PATH sidecar in review-core dispatch stub.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review/scripts/test-aggregate-findings.sh:1250-1275
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Optional three-phase Claude fallback test from plan not implemented. Codex absent plus cursor narration-only plus claude recovery regression could slip through. Add codex absent cursor narration routes to phase3 claude case with claude stub.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: SECURITY.md:133
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Branch mixes unrelated ADOPTED sentinel hardening with #2881 aggregator work. Revert or bisect of one concern affects unrelated security/docs changes. Split #2878 hardening into separate PR or commit.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review/scripts/aggregate-findings.sh:687-752
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Single dispatch stops after phase-1 Codex attestation passes pattern gate but fails narrow-trigger validation; Cursor never runs. Codex returns only LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED on a nonempty ballot; REASON=validation-exhausted stalls Step 5 though Cursor might merge on a second tool attempt under the old outer loop. Do not treat attestation-only as terminal pattern success when input has findings, or map attestation-only validator success to REASON=ok with stripped empty ballot.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review/scripts/aggregate-findings.sh:747-751
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] RC=1 warning text always says empty merge even for preamble_finding_substring. Preamble-contradiction failures log misleading execution-issues text. Branch warning on AGGREGATOR_VALIDATION_FAILED token or use neutral narrow-trigger wording.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Optional indented-heading pattern-gate regression test from plan is missing. Indented ### FINDING_1: could diverge between gate and validator without CI catching it. Add real-dispatcher stub case for indented heading-only output.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] cap_hit bypasses require-result-pattern (pre-existing). Cap-hit without headings reaches validator as validation-failed not dispatcher retry. Track under #2895; out of scope for this branch.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review/scripts/test-aggregate-findings.sh:1250-1271
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing optional Codex-absent Cursor-narration to phase-3 Claude dispatcher regression. When Codex is unavailable Cursor still runs in phase 2; narration-only Cursor output could fail aggregation with no test proving Claude phase-3 recovery. Add codex_absent_cursor_narration_routes_to_phase3_claude mirroring codex_primary_narration test with CODEX_PRESENT=false and narration-only Cursor stub.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent]  No indented-heading pattern-gate regression test despite docs rejecting leading whitespace on FINDING branch. Indented ### FINDING_1: might pass or fail dispatcher differently than validator; split classification could return. Add dispatcher case with indented heading output and assert phase fallback or failure consistent with validator.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review/scripts/test-review-core.sh:266-293
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] review-core stubs omit ALL_OUTPUT_FILES_PATH so integration never exercises sidecar resolution. Regression in ALL_OUTPUT_FILES_PATH handling could pass review-core while failing production aggregate path. Emit ALL_OUTPUT_FILES_PATH from aggregate-dispatch stub used in at least one review-core happy path.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review/scripts/aggregate-findings.sh:556-567
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No positive REASON=ok test for attestation-only duplicate-merge; validator always narrow-triggers on nonempty input. Operators following plan edge-case prose may expect ok on attestation-only output; behavior is validation-exhausted. Align docs with validator or add explicit ok-path test if product requires it.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1213
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb wording updated but not asserted in review-and-fix harness. Accidental revert to old outer-phases message would go unnoticed in CI. Grep new breadcrumb string in aggregator-validation-exhausted propagation test.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/test-aggregate-findings.sh:1250-1271
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] codex_absent case does not assert --require-result-pattern threading. Pattern flag could be dropped for Codex-absent wiring without failing this case. Add AGGREGATE_DISPATCH_ARGV_LOG and pattern greps like phase2 recovery test.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: skills/review/scripts/aggregate-findings.sh:712-715
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] ALL_OUTPUT_FILES_PATH sidecar is opened with only -f/-r checks; its own path is not required to lie under REVIEW_TMPDIR_CANON before read -r cand. A tampered aggregator-dispatch.env could aim the sidecar at an arbitrary readable file; only the parsed candidate path is canonicalized, leaving a minor trust-boundary gap if the session tmpdir is writable by a hostile peer. Canonicalize all_output_files_path under REVIEW_TMPDIR_CANON (mirror the cand case block) before reading; emit REASON=dispatch-failed on mismatch.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Attestation alternation in --require-result-pattern lets phase-1 Codex succeed dispatch with attestation-only output. Codex returns only LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED on a 3-finding ballot; dispatcher never runs Cursor phase 2; validator emits empty_merge_from_nonempty_input; REASON=validation-exhausted stalls Step 5 though Cursor could merge. Remove attestation from the pattern gate (FINDING headings only) or only accept attestation when INPUT_COUNT semantics allow it.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/aggregate-findings.sh:702-708
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Total pattern-gate failure yields REASON=dispatch-failed not validation-exhausted. All phases return narration-only; DISPATCH_OK=false; voters run on unmerged duplicates; pre-collapse multi-outer narrow-trigger exhaustion often stalled under Tool Failures. Document intentional degrade-or-vote behavior or map total pattern failure on nonempty input to validation-exhausted.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/dispatch-with-waterfall.sh:275-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] STATUS=cap_hit bypasses require-result-pattern. Codex cap_hit with empty or non-structured output; REASON=validation-failed; ballot unchanged; voting proceeds without merge signal. Treat cap_hit without FINDING heading as pattern miss or add explicit execution-issues severity.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing regression for attestation-only phase-1 blocking and all-narration dispatch-failed. Harness proves narration and pseudo-heading fallback but not attestation short-circuit or total structural dispatch failure end state. Add integration tests for attestation-only phase 1 and all-phases narration DISPATCH_OK=false.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Live --require-result-pattern adds [[:space:]]* before LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED; plan required byte-equivalent ERE without leading whitespace on attestation. Codex phase-1 padded attestation passes dispatcher gate and ends validation-exhausted instead of falling through to Cursor/Claude per plan. Restore plan ERE or update plan/acceptance to document attestation-only whitespace tolerance.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/review/scripts/test-aggregate-findings.sh:1173-1189
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] No dedicated test_narrow_trigger_validator_failure_maps_to_validation_exhausted or review-core.sh:514 comment. Coverage exists but plan-named regression anchor is missing. Add focused case or rename block; optional comment to review-core.sh:514.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Optional plan tests for three-phase narration failure and indented-heading rejection are absent. Gaps in regression coverage for optional edge paths only. Add optional cases if desired.
- **Suggested revision**: Address the concern above.


### FINDING_1: code-quality: skills/review/scripts/aggregate-findings.sh:494-551
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate construction of input_slot_set in _attempt_attestation_repair and main(). Future edits to slot parsing could diverge between repair and validation. Extract a shared helper or single code path for the input slot set.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/review/scripts/aggregate-findings.sh:300-514
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] has_nonconforming_finding_heading_markers blocks synthesis when pseudo-### FINDING_ headings exist without valid blocks. Model outputs malformed FINDING-like headings plus narrative-only merge; synthesis is skipped and validation still fails despite plan framing all zero-block/no-token cases as recoverable. Document the escape hatch or narrow the detector to cases that would never validate anyway.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/review/scripts/aggregate-findings.sh:528-530; skills/review/scripts/aggregate-findings.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan text used input_slots=<N> style breadcrumb; shipped code uses unique_input_reviewers and input_findings. Downstream greps or audit snippets keyed to the plan string miss the signal. Align naming with consumers or add a transitional alias field.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/aggregate-findings.sh:632-651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Repair path always mv-replaces cand even when output unchanged. Extra inode churn on every successful aggregation. Optional cmp-skip before mv.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/review/scripts/aggregate-findings.sh:646-650
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Any stderr from repair Python is treated as synthesis breadcrumb file content. Unexpected Python warnings could be mistaken for attestation synthesis telemetry. Isolate breadcrumb emission to a dedicated channel or filter.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: agents/orchestrator-aggregator.md:40-56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prompt hardening adds length and repeated fence/token prohibitions. Model may skim critical tail constraints. Consolidate duplicate prohibitions if the section grows further.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/review/scripts/aggregate-findings.sh:220-630
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Embedded validate script already monolithic before this change. N/A for this feature-only review. N/A unless the project chooses a broader split of aggregate-validate.py.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: SECURITY.md:57 and skills/review/scripts/aggregate-findings.sh:632-651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] aggregator-output.txt can be rewritten before validation on the synthesis path, diverging from the embedded plan claim that external consumers always see the raw model bytes An audit or automation diffs dispatch capture to aggregator-output.txt and misattributes the synthesized attestation line to the vendor, or misses that recovery ran because it never reads aggregator-repair.stderr Treat SECURITY.md and aggregate-findings.md as authoritative; update any remaining plan or audit templates that still promise byte-identical aggregator-output.txt and document reliance on aggregator-repair.stderr for empty-merge recovery
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/review/scripts/aggregate-findings.sh:300-517
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New has_nonconforming_finding_heading_markers gate skips attestation synthesis with no regression test. Vendor output with malformed ### FINDING_ headings but zero parsed blocks and no token still fails validation with no synthesis; future edits to the regex could widen or narrow rescue without CI signal. Add a harness stub case expecting validation-failed and no synthesis breadcrumb when nonconforming headings are present.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/review/scripts/test-aggregate-findings.sh:424-442
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Synthesis success case does not assert execution-issues.md stays free of merged-output validation warnings. Plan acceptance #2 explicitly ties success to absence of that execution-issues entry; REASON=ok is indirect only. After synthesis run grep or negate-match execution-issues.md under the same review tmpdir for the validation-failure phrase.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: <TMPDIR>/round-2/diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Precomputed diff file was empty (0 bytes); reviewer used git diff vs origin/main. Does not affect code quality of the branch. Use a populated sidecar or document merge-base when invoking the reviewer.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/aggregate-findings.sh:497-518,632-696
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Deterministic empty-merge attestation synthesis lets narrative-only vendor output pass validation and rewrite findings.md to zero structured findings. Previously the same shape commonly failed validation and left findings.md unchanged so voting could proceed on the original structured ballot; after synthesis a mistaken or hostile narrative-only merge can still clear the ballot with REASON=ok unless operators notice tmpdir-only breadcrumbs. Add a durable human-visible signal when synthesis runs or gate synthesis if ballot preservation on ambiguity is required; document the fail-open for voting consumers.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/review/scripts/aggregate-findings.sh:640-641
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Repair-step failure log refers generically to aggregate-validate.py. Minor triage friction when correlating logs to the actual tmpdir script path. Reword the failure log to match the real artifact or describe it as the embedded validator module.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] security: skills/review/scripts/aggregate-findings.sh:157-161
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Aggregator prompt includes untrusted reviewer markdown in the external-agent prompt surface. Long-standing trust boundary for prompt injection into vendor tools; unchanged by attestation synthesis. Track under general external-agent hardening rather than this feature delta.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review/scripts/aggregate-findings.sh:497-676
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Synthesis plus exact-line strip can persist a malformed near-attestation line when strip() is not exactly the token. Model returns zero parsed FINDING blocks and a line visually like the token with a non-stripped suffix (e.g. format characters); script appends a valid token, validation passes, strip removes only exact-match lines, corrupted line remains in rewritten findings.md; previously validation failed and findings.md stayed unchanged. Reject or strip lines that contain the token without an exact trimmed match before accepting empty-merge success, or narrow synthesis preconditions.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/aggregate-findings.sh:300-312
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Nonconforming FINDING-like line guard blocks synthesis without a dedicated operator-facing breadcrumb. Reviewer prose includes a literal line matching ### FINDING_... that does not parse as a block; empty-merge path fails with generic missing-attestation noise. Emit a single-line reason on aggregator-repair.stderr when synthesis is suppressed due to pseudo-heading detection.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/review/scripts/aggregate-findings.sh:528-531
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Breadcrumb name unique_input_reviewers does not match path-like slot strings in input_slot_set. Misleading monitoring counts for dashboards or humans reading breadcrumbs. Rename counter field or align documentation wording with normalized slot tokens.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: skills/review/scripts/aggregate-findings.sh:274-280
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] finding_id_from_block regex differs from strict block split regexes. Potential rare heading drift inconsistencies; unchanged by this branch. Consider unifying heading parsers in a later refactor.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/aggregate-findings.sh:527-531
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Breadcrumb keys differ from plan input_slots=<N> Downstream checks or docs keyed to plan string miss the new unique_input_reviewers/input_findings format Align breadcrumb to plan or amend plan and consumers together
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review/scripts/aggregate-findings.sh:300-517
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Nonconforming FINDING heading gate skips synthesis not described in plan Model emits malformed ### FINDING_… lines plus narrative; repair may not run; validation-failed path persists despite plan always-on synthesis narrative Document and test the guard or remove it per plan contract
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/review/scripts/test-aggregate-findings.sh:424-442
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Missing literal empty_merge_synthesis_succeeds case name from plan Plan-to-test traceability and audit matrices that reference the planned name do not map 1:1 Rename or add a clearly named case matching the plan
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: implementation_plan Breaking changes
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan still claims aggregator-output.txt shows raw first model write Stakeholders relying on the written plan misunderstand artifact semantics Update the locked plan paragraph to match post-repair staging
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] code-quality: ~/.cache/.../diff.txt empty; git merge-base HEAD main..HEAD empty
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff and requested git range were unusable for this workspace snapshot Reviewer had to substitute origin/main...HEAD None required for code; fix launcher cache or branch baseline next run
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] code-quality: SECURITY.md vs plan file list
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Extra file touched beyond the four listed files None; aligns with SECURITY policy None
- **Suggested revision**: Address the concern above.


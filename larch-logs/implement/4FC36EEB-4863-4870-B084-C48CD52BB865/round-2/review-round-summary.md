# Review Round 2

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 7
- Neutral findings: 1

## Accepted Findings

### FINDING_10: risk-integration: skills/review/scripts/test-aggregate-findings.sh:424-442
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Synthesis success case does not assert execution-issues.md stays free of merged-output validation warnings. Plan acceptance #2 explicitly ties success to absence of that execution-issues entry; REASON=ok is indirect only. After synthesis run grep or negate-match execution-issues.md under the same review tmpdir for the validation-failure phrase.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/review/scripts/aggregate-findings.sh:497-676
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Synthesis plus exact-line strip can persist a malformed near-attestation line when strip() is not exactly the token. Model returns zero parsed FINDING blocks and a line visually like the token with a non-stripped suffix (e.g. format characters); script appends a valid token, validation passes, strip removes only exact-match lines, corrupted line remains in rewritten findings.md; previously validation failed and findings.md stayed unchanged. Reject or strip lines that contain the token without an exact trimmed match before accepting empty-merge success, or narrow synthesis preconditions.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/review/scripts/aggregate-findings.sh:300-312
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Nonconforming FINDING-like line guard blocks synthesis without a dedicated operator-facing breadcrumb. Reviewer prose includes a literal line matching ### FINDING_... that does not parse as a block; empty-merge path fails with generic missing-attestation noise. Emit a single-line reason on aggregator-repair.stderr when synthesis is suppressed due to pseudo-heading detection.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/review/scripts/aggregate-findings.sh:300-514
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] has_nonconforming_finding_heading_markers blocks synthesis when pseudo-### FINDING_ headings exist without valid blocks. Model outputs malformed FINDING-like headings plus narrative-only merge; synthesis is skipped and validation still fails despite plan framing all zero-block/no-token cases as recoverable. Document the escape hatch or narrow the detector to cases that would never validate anyway.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/review/scripts/aggregate-findings.sh:300-517
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Nonconforming FINDING heading gate skips synthesis not described in plan Model emits malformed ### FINDING_… lines plus narrative; repair may not run; validation-failed path persists despite plan always-on synthesis narrative Document and test the guard or remove it per plan contract
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: implementation_plan Breaking changes
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan still claims aggregator-output.txt shows raw first model write Stakeholders relying on the written plan misunderstand artifact semantics Update the locked plan paragraph to match post-repair staging
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: skills/review/scripts/aggregate-findings.sh:528-530; skills/review/scripts/aggregate-findings.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan text used input_slots=<N> style breadcrumb; shipped code uses unique_input_reviewers and input_findings. Downstream greps or audit snippets keyed to the plan string miss the signal. Align naming with consumers or add a transitional alias field.
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: skills/review/scripts/aggregate-findings.sh:646-650
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Any stderr from repair Python is treated as synthesis breadcrumb file content. Unexpected Python warnings could be mistaken for attestation synthesis telemetry. Isolate breadcrumb emission to a dedicated channel or filter.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: SECURITY.md:57 and skills/review/scripts/aggregate-findings.sh:632-651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] aggregator-output.txt can be rewritten before validation on the synthesis path, diverging from the embedded plan claim that external consumers always see the raw model bytes An audit or automation diffs dispatch capture to aggregator-output.txt and misattributes the synthesized attestation line to the vendor, or misses that recovery ran because it never reads aggregator-repair.stderr Treat SECURITY.md and aggregate-findings.md as authoritative; update any remaining plan or audit templates that still promise byte-identical aggregator-output.txt and document reliance on aggregator-repair.stderr for empty-merge recovery
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/review/scripts/aggregate-findings.sh:300-517
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New has_nonconforming_finding_heading_markers gate skips attestation synthesis with no regression test. Vendor output with malformed ### FINDING_ headings but zero parsed blocks and no token still fails validation with no synthesis; future edits to the regex could widen or narrow rescue without CI signal. Add a harness stub case expecting validation-failed and no synthesis breadcrumb when nonconforming headings are present.
- **Suggested revision**: Address the concern above.



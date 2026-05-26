### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan optional tests for codex-absent three-phase chain and indented-heading gate not present. Phase-3-only recovery or indented-heading gate regression may slip CI. Add optional harness cases from the implementation plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan optional indented-heading regression test is missing. A future change could reintroduce [[:space:]]* before ### FINDING_ in the pattern without CI catching mismatch with count_finding_blocks. Add real-dispatcher case: indented ### FINDING_1: rejected at phase 1 valid heading at phase 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan optional codex-absent three-phase narration→Claude test is missing. Codex absent plus Cursor narration-only plus Claude valid output is only partially covered by codex_absent_runs_cursor_in_phase2. Add integration test with CODEX_PRESENT=false narration Cursor stub and Claude ballot asserting PHASE3_SLOTS and ALL_OUTPUT_TOOLS=claude.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: architecture: skills/review/scripts/aggregate-findings.sh:712-736
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ALL_OUTPUT_FILES_PATH sidecar path is not constrained to REVIEW_TMPDIR before read; only the resolved candidate path is canonicalized. Within the same-user tmpdir threat model, a tampered aggregator-dispatch.env could point the sidecar at another readable file and leak its first line into path-resolution logic before rejection. Canonicalize and reject all_output_files_path unless it resolves under REVIEW_TMPDIR_CANON, then read cand.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: architecture: skills/review/scripts/test-aggregate-findings.sh:584-598
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] zero_findings_no_attest uses stub dispatch that skips pattern gate. Production all-narration failure yields dispatch-failed; harness asserts validation-failed and can hide regressions in warning text or DISPATCH_OK handling. Add real-dispatcher integration test for all-phase narration-only; relabel stub test as validator-only if kept.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing optional phase-3 and indented-heading pattern-gate tests from the plan. Codex-absent Cursor-narration-only path and indented-heading rejection are unguarded against future dispatcher regressions. Add PATH-stub tests for phase-3 Claude recovery and indented pseudo-heading rejection at the gate.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/review/scripts/aggregate-findings.sh:687 skills/design/scripts/decompose-aggregator.sh:127-142
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated ALL_OUTPUT_FILES_PATH resolution and divergent doc strings for the same dispatcher contract. Future edits may fix one caller or one doc surface and leave the other stale (already happened for attestation whitespace). Consider a shared resolve_dispatch_candidate helper used by both aggregators.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Narrow-trigger RC=1 terminates as validation-exhausted without trying Claude even when Codex/Cursor returned pattern-valid attestation or preamble-only output. Codex phase-1 returns padded LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED on a 25-finding ballot; dispatcher accepts; validator emits empty_merge_from_nonempty_input; Step 5 stalls; Claude never runs though it might merge. Document as accepted in aggregate-findings.md/SECURITY.md or add a post-validator redispatch when narrow-trigger fires on non-Claude tool.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


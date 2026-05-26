### FINDING_10: [OUT_OF_SCOPE] stderr newline splitting remains boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `sanitize_diagnostic_line` strips intra-line control bytes but does not prevent upstream stderr newlines from creating multiple `larch_err` lines; this is documented as a residual scope boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] SKIP_REASON emit lacks control-byte sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SKIP_REASON` is emitted through `emit_kv` without a control-byte pass, relying on current fixed sanitizer vocabulary and quiet-mode routing; this is a defense-in-depth concern if token vocabulary expands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] step-7a does not consume generator SKIP_REASON
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: On skipped generator status, step-7a sets a generic `CODE_FLOW_SKIP_REASON` and does not consume `SKIP_REASON` from generator stdout, so improved token extraction does not yet affect PR or summary text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] SECURITY.md not updated
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Item B changes handling of untrusted `gh` stderr, but `SECURITY.md` was not updated; reviewer marks this outside the plan’s acceptance contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Divergent warning REASON_TOKEN parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/sanitize-mermaid-fragment.sh` still extracts warning `REASON_TOKEN` values with parsing that would truncate hypothetical tokens containing embedded `=`, diverging from `generate-code-flow-diagram.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] sanitize_list lacks LC_ALL=C
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `sanitize_list` does not use `LC_ALL=C`, unlike `sanitize_diagnostic_line`, so malformed UTF-8 in KV list inputs could trigger BSD `tr` illegal-byte-sequence behavior on rare paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] step-7a SKIP_REASON stub is stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The step-7a generator stub still emits legacy `SKIP_REASON=<token> fence=mermaid line=7` output, so future step-7a parsing could be tested against stale stub behavior rather than production generator output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Branch includes unrelated issue work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch diff includes work outside the `#2854` plan, broadening the review surface even though the `#2854` commit itself is described as isolated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_9: [OUT_OF_SCOPE] Raw gh job names remain unsanitized
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Failed job names from `gh run view` can still flow into TSV and emit paths without the new diagnostic sanitizer or strict list sanitization, leaving downstream TSV or line-oriented consumers exposed to crafted names with control bytes, newlines, or delimiter-like characters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


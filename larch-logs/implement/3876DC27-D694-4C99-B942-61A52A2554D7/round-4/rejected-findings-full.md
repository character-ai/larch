### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `larch_emit_untrusted_file_block` does not validate XML tag names
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `larch_emit_untrusted_file_block` does not validate XML tag names. A future caller passing a user-influenced tag containing `>` or spaces could break out of the literal-redacted block framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict tags to a safe identifier regex or escape tag names inside the helper.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: Scope-reduction marker detector changed `startswith` to `re.match`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Marker consolidation in `check-scope-reduction-marker.sh` changed startswith-based detection to `re.match` despite the plan requiring byte-identical detector logic below the input-read head. A future marker-shape edge case could diverge between pre-merge behavior and consolidated behavior without a deliberate contract decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore `startswith` in the unified detector or document and test the intentional semantic change.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `emit_untrusted_dynamic_body` duplicates `larch_untrusted_redact_stream`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-review-panel.sh` `emit_untrusted_dynamic_body` duplicates `larch_untrusted_redact_stream` logic inline. Dynamic archetype prompts may miss a future redaction/escaping fix applied only to `lib-untrusted-block` consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source `lib-untrusted-block.sh` and call `larch_untrusted_redact_stream` for dynamic body emission.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


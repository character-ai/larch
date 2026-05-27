### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: risk-integration: scripts/test-upsert-diagrams-comment.sh:258-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Empty/absent --code-flow-file preserve (FINDING_3 symmetric half) is not regression-tested. Step 7a skip/fail paths rely on preserve-not-clear for Code Flow; a helper regression could clobber prior Code Flow sections undetected. Add a case with existing Code Flow and architecture-only upsert asserting CODE_FLOW_SOURCE=preserved.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: security: skills/implement/scripts/step-7a.sh:386
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] step-7a logs diagram upsert failures with append_best_effort_failure without --redact while design 5c.5 uses --redact. Raw gh stderr from a failed upsert can land in execution-issues.md and be flushed to public larch-logs. Pass --redact for the larch:diagrams upsert append-tool-failure site and align with design Step 5c.5.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: security: scripts/upsert-diagrams-comment.sh:137-144,221-222
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Preserved Architecture sections from the issue comment are not re-sanitized through sanitize-mermaid-fragment.sh on code-flow-only upserts. An actor with issue-comment access could pre-seed Architecture under the stable marker; /implement preserves it until /design overwrites. Document the trust boundary; optionally re-sanitize preserved sections or ignore foreign Architecture without design provenance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/upsert-diagrams-comment.sh:74-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Awk fence logic is mermaid-only Non-mermaid fenced blocks with H2-like lines inside diagram comments could be split incorrectly on merge Track generic fence depth or document mermaid-only comment bodies
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/shared/mermaid-safe-content.md:21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale placeholder wording for Step 7a publish path Docs imply placeholder upserts that no longer occur after this change Update enforcement prose to describe omit-and-preserve behavior
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


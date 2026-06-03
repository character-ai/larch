### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Harness lacks redaction-pipeline failure fallback tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test stubs redact scripts failing and asserting documented fallback operator strings on stderr with empty stdout for copy-plan/gh-issue-view paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Harness covers symlink but not other non-regular `bootstrap-routing.env`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Only symlink refusal is tested; a directory (or other non-regular path) named `bootstrap-routing.env` could be mishandled. Add a harness case expecting refusal/exit 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: File-first `bootstrap-routing.env` trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: When present, file-first `bootstrap-routing.env` is authoritative for routing keys; a local writer to session tmpdir could swap `REPO` or bail keys between wrapper write and orchestrator read. Document trust boundary; chmod 600 on write; cross-check critical keys against `_inv_out` stdout envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Wrapper retains `_ib_*` local names after `_inv_*` migration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` arg-assembly helpers still use `_ib_*` names while SKILL call sites moved to `_inv_*`, increasing trace cost in Step 0 with no functional bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0


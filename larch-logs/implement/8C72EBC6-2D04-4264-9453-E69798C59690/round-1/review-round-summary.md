# Review Round 1

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 8
- Neutral findings: 1

## Accepted Findings

### FINDING_13: risk-integration: scripts/test-tracking-issue-write.sh:108-167 scripts/tracking-issue-write.sh:216-229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Truncation-marker fail-closed path for gh stderr is documented but not exercised by the harness. A future change removes or narrows the case arm matching [content truncated while redact() still returns 0; CI stays green and raw or partially redacted gh/jq material could return to ERROR=. Add a stub redact-secrets.sh that prints the real truncation marker plus a fake token and assert generic ERROR= and no token leakage.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/tracking-issue-write.md:41-42
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-code table still implies redaction helper failures always exit 3, but gh stderr fail-closed redaction now exits 2 via emit_gh_failure. Operators or automation using exit 3 as the sole signal that the redaction subsystem failed will miss stderr-side redact_gh_error failures, which now look identical to ordinary gh failures. Document that stderr-side redact_gh_error failures intentionally use the exit 2 gh failure envelope with a generic ERROR=, distinct from exit 3 body/title redaction.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/test-tracking-issue-write.sh:7088-7147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness lacks a truncation-marker success-path case for redact_gh_error. A regression could break the truncation substring guard or reorder truncation vs flattening without failing CI. Add a stub redactor or stdin fixture that emits the documented truncation marker with exit 0 and assert generic ERROR= and no secret leakage.
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: scripts/tracking-issue-write.sh:216-254; scripts/tracking-issue-write.md:35-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Gh stderr redaction pipeline failure now exits 2 via emit_gh_failure instead of exit 3 via emit_redaction_failure. Automation or operators distinguishing gh/API failures (exit 2) from redaction helper failures (exit 3) mis-classifies redactor outages on gh error paths. Document the new split in tracking-issue-write.md or preserve exit 3 for pipeline failure on the gh stderr path while keeping ERROR= generic.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/tracking-issue-write.sh:216-254
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Gh stderr redaction failure no longer exits 3 via emit_redaction_failure; emit_gh_failure always exits 2. Wrapper or runbook that keys only on exit 3 to detect redaction-helper breakage will mis-classify a rename path where gh fails and redact_gh_error falls back to generic ERROR=. Document exit 2 vs 3 split or restore exit 3 on redact_gh_error generic branch.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/tracking-issue-write.md:35-42 scripts/tracking-issue-write.sh:49-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Exit-code docs/header still imply all redaction helper failures are code 3 with redaction: ERROR=. Readers assume stderr redaction outage maps to exit 3; actual exit is 2. Add carve-out lines aligning docs with behavior.
- **Suggested revision**: Address the concern above.



### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Aggregator harness uses 2-row panel NDJSON instead of full eight-slot panel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Concatenation / ordering bugs across a full panel surface may not be exercised in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add eight minimal panel output files and assert merge prompt contains eight panel sections


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No assertion for feature-only discussion substitution on success path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Discussion block wiring in feature-only success mode is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed feature-only run and grep rendered prompt for discussion artifact text


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No test for `FALLBACK_COUNT`-only degradation path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Threshold regression for degraded vs ok could flip without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub FALLBACK_COUNT=5 with STATIC_DISPATCH_OK=true and assert degraded panel flags


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `DECOMPOSE_REDACT_SH` can override close-comment redactor
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Hostile or mistaken env could disable redaction while still posting via `gh issue comment --body-file`; trust boundary for tests vs production should be explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit override to harness runs or ignore env outside tests; document trust boundary.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Annotate idempotency: `ISSUES_CREATED` vs parsed URL count / malformed stdout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sentinel and filed record can desync from real GitHub filing if stdout is malformed; interacts with partial-batch semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add stricter stdout validation before sentinel write; document partial ISSUES_FAILED handling.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `/larch:block-issue` vs intra-batch deps / top-level requirements drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Reference / requirements still imply `/larch:block-issue` while the flow may rely on intra-batch deps only, so extra dependency edges outside the batch TSV might never get filed unless documented or an explicit step exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document subsume-by-intra-batch or add explicit block-issue step


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `aggregate-findings` reuse vs waterfall-only aggregator
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan / acceptance language pointed at `aggregate-findings` reuse but implementation is waterfall-only; mismatch risks silent loss of an intended merge path and weak CI signal for concatenation/order bugs at full panel width.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Maintain as KISS or add optional probe per original plan
  - From cursor-specialist-testing-output.txt: Reconcile docs/plan with code or implement the optional aggregate-findings path plus tests


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `close-original` comment body is grep-thin vs #2644 narrative
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Closing comment is minimal for grepping/audit compared to the richer narrative expected for partition closes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Compose structured close body from parsed partition metadata


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Omitted `--issue-number` yields placeholder parent reference in partition bodies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Prepare falls back to a placeholder original issue reference when `--issue-number` is omitted, weakening traceability and confusing partition issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require --issue-number for prepare or read ISSUE_NUMBER from a session env file.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0


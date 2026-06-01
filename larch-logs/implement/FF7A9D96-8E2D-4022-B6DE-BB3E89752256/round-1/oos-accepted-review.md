### FINDING_14: [OUT_OF_SCOPE] Session id can be used as an unchecked path segment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `session-id` is used in path construction without rejecting traversal or unexpected characters, so a party able to rewrite it could influence ndjson discovery paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_15: [OUT_OF_SCOPE] Design tmpdir / ndjson discovery trust tmpdir contents too broadly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--design-tmpdir` and find-based ndjson discovery trust session tmpdir contents; symlinks or cross-tmpdir use could steer the gate toward misleading or arbitrary readable inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_18: [OUT_OF_SCOPE] ship-pr has a parallel weaker OOS gate path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` still embeds a separate OOS disposition gate path that does not share checkpoint plumbing or strict/precondition behavior, risking divergence from Step 8+ checkpoint semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-state-handshake-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Multiple ndjson files are not treated as ambiguous with non-empty session id
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `RUN_ID` is non-empty, multiple ndjson files do not trigger an ambiguity exit, so stale or wrong ndjson may be selected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_22: [OUT_OF_SCOPE] Checkpoint exit 2 passthrough is an intentional contract refinement
- **Reviewer(s)**: dyn-state-handshake-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that propagating checkpoint exit 2 for validation/setup aligns with the plan and is not a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-handshake-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_23: [OUT_OF_SCOPE] Helper boundaries are otherwise respected
- **Reviewer(s)**: dyn-state-handshake-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that the checkpoint helper does not mutate `OOS_PENDING`, `run-statistics`, or PR resume state, and its main exit mapping matches the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-handshake-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_25: [OUT_OF_SCOPE] Pre-gate failures now improve audit coverage
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that ambiguous/missing ndjson pre-gate failures now flow through checkpoint validation logging, improving audit coverage over the old inline path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_26: [OUT_OF_SCOPE] Gate rc 1/2 logging uses intended checkpoint sites and tool name
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that gate rc 1/2 logging uses the expected site tokens, checkpoint tool name, saved exit codes, and stderr sinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_27: [OUT_OF_SCOPE] Best-effort append remains by design
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that best-effort append semantics are unchanged from the prior inline block and that missing durable rows remain possible if append fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_28: [OUT_OF_SCOPE] NEVER #17 checkpoint drift also noted as documentation-only by audit reviewer
- **Reviewer(s)**: dyn-audit-trail-output.txt
- **Severity**: nit
- **Concern**: The audit reviewer separately tags the NEVER #17 direct-gate wording as out-of-scope documentation drift rather than a helper audit-logging regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-trail-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected



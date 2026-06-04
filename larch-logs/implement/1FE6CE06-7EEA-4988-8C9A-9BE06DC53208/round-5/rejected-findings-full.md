### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: publish-path docs and validation need to match implementation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security reviewer called out `SECURITY.md` / `design-log-publish.md` ordering plus publish-path input validation as an invariant to keep accurate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: design-publish exits success after failed log publish
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` can exit 0 after plan write even when the log publish failed, so automation that checks only the driver exit code may treat a failed flush as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Parse PUBLISH_OK or exit non-zero when SESSION_ID is set and PUBLISH_OK is not true


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: watch and merge path lacks transient retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After registration succeeds, transient `gh` failures during watch or merge can fail closed and leave an open PR even though retrying might succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use with_transient_retry or a single retry on the watch path before fail-closed


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: plan-fidelity risk from unplanned plan-review-loop changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Collector stderr handling and multi-round test `LARCH_QUIET_PID` changes are not listed in the #3413 plan file set, so strict plan-only review may treat them as scope creep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document the coupling in the PR body or move plan-review-loop changes to a separate issue if strict plan scope is required.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: registration gate may still accept stale green checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The registration predicate checks `headRefOid == PUSH_HEAD_SHA` but may not prove required check runs are for that pushed SHA, leaving a possible stale-green race after force-push PR reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If gh JSON exposes check commit/head metadata require pending or SHA-aligned runs before registration; else add post-head-match grace or document residual race.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: registration stop conditions can confuse operators
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `REG_DEADLINE` and `REG_MAX_PROBES` are co-equal bounds, so slow probes can hit the wall-clock deadline before probe budget exhaustion and produce confusing diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document co-equal deadline in design-log-publish.md or use probe count as sole bound.
  - From cursor-specialist-edge-cases-output.txt: Document wall-clock authority or tie stop primarily to probe budget


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: post-registration check watch can block indefinitely
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Registration polling is bounded, but after checks register, `gh pr checks --watch` has no local timeout, so a stuck required check can block `/design` indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document as known limit or add bounded watch with fail-closed merge refusal.
  - From cursor-specialist-edge-cases-output.txt: Document trade-off or add optional watch wall-clock cap with distinct stderr


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: two-phase CI gate invariant needs preservation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Security reviewer surfaced the bounded registration polling, non-empty checks array, contract-stream cleanliness, head match, watch, and admin merge ordering as an important invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: fail-closed merge paths must remain distinct
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Registration timeout, watch failure, and admin merge behavior should stay distinct, with no unconditional admin merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: re-enabled flush must preserve redaction pipeline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The restored design-log flush depends on the redacted publish pipeline and `[DESIGNED]` rename remaining gated on `PUBLISH_OK=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0


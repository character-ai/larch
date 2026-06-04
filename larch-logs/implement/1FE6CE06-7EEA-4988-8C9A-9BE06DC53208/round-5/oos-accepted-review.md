### FINDING_11: [OUT_OF_SCOPE] direct design-log-publish repo argument is less strictly validated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Direct `scripts/design-log-publish.sh --repo OWNER/REPO` forwarding lacks the stricter `validate_repo` used upstream, so malformed direct invocation could target the wrong repository. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] admin merge bypass remains part of trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--admin` still bypasses human review after required checks pass; this is intentional and documented, relying on branch protection, CI, and credential hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_13: [OUT_OF_SCOPE] re-enabled flush increases committed artifact exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: More redacted design artifacts will reach the default branch; existing scrub/allowlist mitigations remain the stated control, and scrub failures should be treated as credential-rotation events.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_20: [OUT_OF_SCOPE] jq-required test intentionally does not exercise merge gate
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: nit
- **Concern**: The jq-required case uses a no-op `gh` stub and does not test registration/watch behavior; source marked this acceptable because the case targets jq availability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_21: [OUT_OF_SCOPE] publish orchestration tests stub design-log-publish boundary
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: latent
- **Concern**: `test-design-publish.sh` stubs `design-log-publish.sh`, so merge-gate fidelity depends on `test-design-log-publish.sh`; source marked this pre-existing and intentional layering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] step registry advances past publish failure
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: latent
- **Concern**: The orchestrator writes `.completed/step-5c` when `PLAN_WRITE_OK=true` even if `PUBLISH_OK=false`, so pause/resume can advance to cleanup rather than retrying publish. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_4: [OUT_OF_SCOPE] missing SESSION_ID still renders approved summary
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: When `SESSION_ID` is missing, publish is skipped but the post-publish summary can still render as approved, which may confuse operators. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pre-existing; consider failed-publish or cancelled variant when publish skipped.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted



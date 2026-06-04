# Review Round 3

- Mode: `diff`
- 12 accepted, 8 rejected (8 exonerated)

## Accepted Findings

### FINDING_10: Step 5c failure/resume behavior lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 5c gating is only prompt/structure checked; no offline harness verifies failed publish leaves resume positioned at Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Clarify publish failure handling can miss normalized `PUBLISH_OK=false`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Clarify publish handling is under-tested and appears to log failures only on non-zero rc, so an rc-zero `PUBLISH_OK=false` operational failure may skip execution-issues logging and publish-failure warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Malformed repo negative tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Malformed `--repo` coverage is thin for log-publish and missing for the postplan pause path, so invalid repo regressions may slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Clarify publish metadata is not persisted into final summary render
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-lifecycle-output.txt
- **Severity**: important
- **Concern**: Clarify publish parses PR/recovery metadata in one subshell, but Final summary rendering runs in another without persisted `DESIGN_LOG_*`, so failed-publish summaries can omit recovery details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-lifecycle-output.txt: Address the concern above.


### FINDING_21: Gate C plan-block write omits resolved `--repo`
- **Reviewer(s)**: dyn-repo-boundary-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` threads resolved `REPO` into publish/summary paths but omits it for `plan-block-write.sh`, risking writes to the wrong repository when the target differs from the hub default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-boundary-output.txt: Address the concern above.


### FINDING_22: Postplan invalid repo abort leaves pause sentinel armed
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: `design-postplan-emit.sh` exits on invalid resolved repo before invoking pause-save, leaving `.pause-requested` armed and skipping structured pause failure output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


### FINDING_25: Clarify empty-session publish skip uses a different outcome
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: Gate C maps empty `SESSION_ID` to `publish-skipped`, but clarify maps the same skipped-publish condition to `cancelled-clarify`, splitting the shared summary contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_26: Publish-tail docs describe a stale two-phase render contract
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: `design-publish.md` still describes pre-publish then post-publish rendering, while the driver and tests use a single post-publish render path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_3: Inconsistent `validate_repo` rules across repo-boundary scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-repo-boundary-output.txt
- **Severity**: latent
- **Concern**: Repo validation differs across publish, pause, postplan, init, and env-persistence paths; malformed slugs such as `--owner/repo`, backslash-containing values, or `../repo` can be accepted by weaker paths while stricter paths reject them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-boundary-output.txt: Address the concern above.


### FINDING_4: Contradictory publish envelopes discard recovery metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: When `design-log-publish.sh` exits non-zero while stdout claims `PUBLISH_OK=true`, `design-publish.sh` forces failure but clears parsed PR/recovery metadata, so operators may lose recovery branch or flush PR hints in failed-publish summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_5: `publish-skipped` is missing from SKILL summary outcome prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The documented Final summary `SUMMARY_OUTCOME` enum omits `publish-skipped` even though renderers accept it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Clarify repo-resolution prose references nonexistent argv binding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Clarify-loop instructions cite Step 0-pre explicit repo argv binding, but `/design` has no `--repo`; the documented order should match Step 0b resolution and persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.



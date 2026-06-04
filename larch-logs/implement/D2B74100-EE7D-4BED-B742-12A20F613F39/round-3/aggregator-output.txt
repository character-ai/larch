### FINDING_1: Duplicate publish-recovery metadata validators can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Publish-recovery metadata validation is duplicated between `design-publish.sh` and `render-final-summary.sh`, creating drift risk between summary rendering and warning behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Source-env parsing helpers remain duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `source_env_get` is not shared with other awk-only source-env readers, leaving multiple parsers for the same contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_6: Harness assertion id collides with Step 5c numbering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Assertion id `(27)` in `test-design-structure.sh` collides semantically with Step 5c `(27)` pins, making CI failures ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Pre-existing validator duplication remains across design toolchain
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: Several repo and sanitizer validators predate this branch and remain duplicated or subtly inconsistent across design scripts, creating long-term maintenance drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_8: Clarify repo-resolution prose references nonexistent argv binding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Clarify-loop instructions cite Step 0-pre explicit repo argv binding, but `/design` has no `--repo`; the documented order should match Step 0b resolution and persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Publish-skipped result env omits explicit `PUBLISH_OK`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Empty-`SESSION_ID` publish-skipped runs omit `PUBLISH_OK` from `.design-publish-result.env`, so env-only consumers may confuse skip with failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_13: [OUT_OF_SCOPE] Bash prelude still sources generated env
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The broader design prelude still sources generated `current-design-env-$PPID.sh` / `source-env.sh`; this trust model predates the branch even though pause-save moved to awk-only reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Positive hardening observations
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-boundary-output.txt, dyn-pause-recovery-output.txt, dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Reviewers noted positive out-of-scope hardening/coverage observations, including metadata sanitization, awk-only reads, repo threading, recoverable pause behavior, and run-log guard coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-boundary-output.txt: Address the concern above.
  - From dyn-pause-recovery-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_15: Clarify publish metadata is not persisted into final summary render
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-lifecycle-output.txt
- **Severity**: important
- **Concern**: Clarify publish parses PR/recovery metadata in one subshell, but Final summary rendering runs in another without persisted `DESIGN_LOG_*`, so failed-publish summaries can omit recovery details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-lifecycle-output.txt: Address the concern above.

### FINDING_16: Pause state is written before publish succeeds
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `pause-state.txt` can be written before publish succeeds, leaving local state that implies resumability even when no marker or recovery metadata was published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Step 5c can be marked complete on empty `SESSION_ID`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `step-5c` is written for `publish-skipped` when `SESSION_ID` is empty, so resume may not retry the publish tail after transient session-id loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Run-log synthesis guard may miss `failed-plan-write`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Run-log synthesis suppresses fake paths for `failed-publish` and `publish-skipped`, but may still synthesize paths for `failed-plan-write` with `RUN_LOGS_PATH=N/A`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Publish-skipped uses success-class footer and cleanup path
- **Reviewer(s)**: dyn-publish-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Empty `SESSION_ID` produces an honest `publish-skipped` summary but still uses success footer/cleanup behavior, weakening terminal signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-lifecycle-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Pre-existing plan/named-block repo binding gaps
- **Reviewer(s)**: dyn-publish-lifecycle-output.txt, dyn-repo-boundary-output.txt
- **Severity**: latent
- **Concern**: Some named/plan block paths predate this branch and either omit explicit repo forwarding or do not validate `--repo` before `gh` calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-lifecycle-output.txt: Address the concern above.
  - From dyn-repo-boundary-output.txt: Address the concern above.

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

### FINDING_23: Pause-save contradictory envelope clears recovery branch
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: In `design-pause-save.sh`, non-zero publish rc plus stdout `PUBLISH_OK=true` forces failure but blanks `RECOVERY_BRANCH`, preventing the usual recovery-branch-only resumable marker path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Pause publish failure logging omits stdout metadata
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: Pause publish failure logging attaches stderr but not stdout, so recovery metadata from stdout may be absent from `execution-issues.md`.
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

### FINDING_27: [OUT_OF_SCOPE] Pause contradictory-envelope behavior should align with publish fix
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: The pause path applies the same recovery-clearing contradictory-envelope rule as publish; it should be aligned with whatever recovery-preservation behavior is chosen.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Implement fallback does not mirror `publish-skipped`
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Implement’s degraded fallback documents/emits outcome bullets only for `failed-*`, not `publish-skipped`, though `/implement` does not currently use that outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

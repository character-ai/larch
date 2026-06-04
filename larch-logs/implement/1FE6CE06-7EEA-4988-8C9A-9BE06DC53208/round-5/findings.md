### FINDING_1: failed-publish recovery summary bullets can drift or go untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Failed-publish PR/recovery bullets are assembled on multiple render paths and are not covered by an integration-style test with `DESIGN_LOG_*` values, so fallback or future edits could omit stale recovery guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract append_failed_publish_notes helper used by both paths
  - From cursor-specialist-correctness-output.txt: Add case setting DESIGN_LOG_PR_NUMBER URL RECOVERY_BRANCH and assert recovery lines in final-summary.md.
  - From cursor-specialist-testing-output.txt: Add matrix or dedicated case setting DESIGN_LOG_PR_NUMBER/URL/RECOVERY_BRANCH and grep final-summary.md for Log flush PR and recovery bullets.

### FINDING_2: registration gate may still accept stale green checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The registration predicate checks `headRefOid == PUSH_HEAD_SHA` but may not prove required check runs are for that pushed SHA, leaving a possible stale-green race after force-push PR reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If gh JSON exposes check commit/head metadata require pending or SHA-aligned runs before registration; else add post-head-match grace or document residual race.

### FINDING_3: registration stop conditions can confuse operators
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `REG_DEADLINE` and `REG_MAX_PROBES` are co-equal bounds, so slow probes can hit the wall-clock deadline before probe budget exhaustion and produce confusing diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document co-equal deadline in design-log-publish.md or use probe count as sole bound.
  - From cursor-specialist-edge-cases-output.txt: Document wall-clock authority or tie stop primarily to probe budget

### FINDING_4: [OUT_OF_SCOPE] missing SESSION_ID still renders approved summary
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: When `SESSION_ID` is missing, publish is skipped but the post-publish summary can still render as approved, which may confuse operators. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pre-existing; consider failed-publish or cancelled variant when publish skipped.

### FINDING_5: final empty-porcelain publish semantics lack verification and documentation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The final no-delta publish path can succeed idempotently when logs already exist on main or fail closed when missing, but that behavior is not fully tested or documented and may surprise automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-design-log-publish.sh cases for main-already-has-run-id (success, no gh create/merge) and missing-on-main (PUBLISH_OK=false).
  - From cursor-specialist-edge-cases-output.txt: Document idempotency or compare tree or require merge in this invocation
  - From cursor-specialist-plan-fidelity-output.txt: Add a short "empty porcelain (final)" subsection to scripts/design-log-publish.md describing the ls-tree idempotency branch.

### FINDING_6: post-registration check watch can block indefinitely
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Registration polling is bounded, but after checks register, `gh pr checks --watch` has no local timeout, so a stuck required check can block `/design` indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document as known limit or add bounded watch with fail-closed merge refusal.
  - From cursor-specialist-edge-cases-output.txt: Document trade-off or add optional watch wall-clock cap with distinct stderr

### FINDING_7: two-phase CI gate invariant needs preservation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Security reviewer surfaced the bounded registration polling, non-empty checks array, contract-stream cleanliness, head match, watch, and admin merge ordering as an important invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: fail-closed merge paths must remain distinct
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Registration timeout, watch failure, and admin merge behavior should stay distinct, with no unconditional admin merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: re-enabled flush must preserve redaction pipeline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The restored design-log flush depends on the redacted publish pipeline and `[DESIGNED]` rename remaining gated on `PUBLISH_OK=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: publish-path docs and validation need to match implementation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security reviewer called out `SECURITY.md` / `design-log-publish.md` ordering plus publish-path input validation as an invariant to keep accurate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] direct design-log-publish repo argument is less strictly validated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Direct `scripts/design-log-publish.sh --repo OWNER/REPO` forwarding lacks the stricter `validate_repo` used upstream, so malformed direct invocation could target the wrong repository. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] admin merge bypass remains part of trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--admin` still bypasses human review after required checks pass; this is intentional and documented, relying on branch protection, CI, and credential hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] re-enabled flush increases committed artifact exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: More redacted design artifacts will reach the default branch; existing scrub/allowlist mitigations remain the stated control, and scrub failures should be treated as credential-rotation events.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: design-publish exits success after failed log publish
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` can exit 0 after plan write even when the log publish failed, so automation that checks only the driver exit code may treat a failed flush as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Parse PUBLISH_OK or exit non-zero when SESSION_ID is set and PUBLISH_OK is not true

### FINDING_15: watch and merge path lacks transient retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After registration succeeds, transient `gh` failures during watch or merge can fail closed and leave an open PR even though retrying might succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use with_transient_retry or a single retry on the watch path before fail-closed

### FINDING_16: plan-fidelity risk from unplanned plan-review-loop changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Collector stderr handling and multi-round test `LARCH_QUIET_PID` changes are not listed in the #3413 plan file set, so strict plan-only review may treat them as scope creep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document the coupling in the PR body or move plan-review-loop changes to a separate issue if strict plan scope is required.

### FINDING_17: multi-round integration gh stub can drift from canonical harness
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-multi-round-integration.sh` embeds a simplified `gh` stub that only models happy-path registration/watch behavior, so integration can stay green while canonical merge-gate behavior regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Factor shared stub helpers (or source `make_gh_stub` from one file) and add at least one integration assertion that exercises registration (e.g. `GH_STUB_CHECKS_JSON_EMPTY_FIRST` + `GH_STUB_LOG` probe counts) or document that merge-gate coverage is exclusively in `test-design-log-publish.sh`.

### FINDING_18: stale-head harness coverage is unrealistic
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: latent
- **Concern**: Stale-head tests use all-zero or synchronously updated head OIDs, which does not reproduce the realistic force-push lag where checks are non-empty but `headRefOid` still points to the prior valid SHA.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: In stale-head cases, set `GH_STUB_PR_HEAD_OID` (or the mismatch knob) to the pre-push commit from the harness clone (e.g. `HEAD~1` or the seed pause commit) while `resolve_pr_head_oid` returns the new tip after alignment, so registration must reject a syntactically valid stale OID.
  - From dyn-gh-harness-output.txt: Add a case that keeps non-empty `--json` output while `GH_STUB_PR_HEAD_OID` (or a first-N knob) returns the previous push SHA, then flips to `PUSH_HEAD_SHA` after K probes—mirroring pause reuse without relying on all-zero OIDs.

### FINDING_19: gh stub watch branch does not require --required
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: latent
- **Concern**: The `--watch` stub accepts `pr checks --watch --fail-fast` without requiring `--required`, so dropping `--required` on the production watch call could still pass harness cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Add `has_arg --required "$@"` to the watch branch (and optionally to the `--json` branch) so unhandled or under-specified `pr checks` shapes fail with exit 99.

### FINDING_20: [OUT_OF_SCOPE] jq-required test intentionally does not exercise merge gate
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: nit
- **Concern**: The jq-required case uses a no-op `gh` stub and does not test registration/watch behavior; source marked this acceptable because the case targets jq availability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] publish orchestration tests stub design-log-publish boundary
- **Reviewer(s)**: dyn-gh-harness-output.txt
- **Severity**: latent
- **Concern**: `test-design-publish.sh` stubs `design-log-publish.sh`, so merge-gate fidelity depends on `test-design-log-publish.sh`; source marked this pre-existing and intentional layering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-harness-output.txt: Address the concern above.

### FINDING_22: flush PR can contain approved final-summary after publish failure
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: The publish tail stages `final-summary.md` before the actual flush outcome is known, so an open failed-publish PR can contain an approved-run summary while issue/chat output shows failed-publish recovery information.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Defer staging `final-summary.md` until publish outcome is known (e.g. run pre-publish only to a sidecar path, or have `design-log-publish.sh` re-stage/overwrite `final-summary.md` from the post-publish render before `git commit`), or drop pre-publish bundling of the terminal summary when flush is live.

### FINDING_23: reentry marker can block quick retry after publish failure
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: `design_reentry_marker_write` runs after plan write, but rename is gated on `PUBLISH_OK=true`; after failed flush, a quick retry can hit the same-session reentry guard instead of resuming recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Move the reentry marker write to after successful publish (and rename), or clear/short-circuit the marker when publish fails so operators can retry publish or `/design` without waiting for TTL expiry.

### FINDING_24: Step 5d/Step 6 cleanup prose can destroy failed-publish recovery metadata
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` implies tmpdir cleanup is mandatory whenever `PLAN_WRITE_OK=true`, while failed flushes require preserving `$DESIGN_TMPDIR`; an orchestrator following the prose literally could remove recovery artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Tighten Step 5d to say “continue to Step 6” without implying cleanup, and gate the Step 6 Bash fence on the same `PUBLISH_OK` predicate (or add an explicit “do not run the cleanup fence when publish failed” bullet next to item 7).

### FINDING_25: [OUT_OF_SCOPE] step registry advances past publish failure
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: latent
- **Concern**: The orchestrator writes `.completed/step-5c` when `PLAN_WRITE_OK=true` even if `PUBLISH_OK=false`, so pause/resume can advance to cleanup rather than retrying publish. Source marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.

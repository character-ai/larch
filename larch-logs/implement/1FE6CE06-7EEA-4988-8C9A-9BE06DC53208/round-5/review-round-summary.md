# Review Round 5

- Mode: `diff`
- 8 accepted, 10 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: failed-publish recovery summary bullets can drift or go untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Failed-publish PR/recovery bullets are assembled on multiple render paths and are not covered by an integration-style test with `DESIGN_LOG_*` values, so fallback or future edits could omit stale recovery guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract append_failed_publish_notes helper used by both paths
  - From cursor-specialist-correctness-output.txt: Add case setting DESIGN_LOG_PR_NUMBER URL RECOVERY_BRANCH and assert recovery lines in final-summary.md.
  - From cursor-specialist-testing-output.txt: Add matrix or dedicated case setting DESIGN_LOG_PR_NUMBER/URL/RECOVERY_BRANCH and grep final-summary.md for Log flush PR and recovery bullets.


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


### FINDING_5: final empty-porcelain publish semantics lack verification and documentation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The final no-delta publish path can succeed idempotently when logs already exist on main or fail closed when missing, but that behavior is not fully tested or documented and may surprise automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-design-log-publish.sh cases for main-already-has-run-id (success, no gh create/merge) and missing-on-main (PUBLISH_OK=false).
  - From cursor-specialist-edge-cases-output.txt: Document idempotency or compare tree or require merge in this invocation
  - From cursor-specialist-plan-fidelity-output.txt: Add a short "empty porcelain (final)" subsection to scripts/design-log-publish.md describing the ls-tree idempotency branch.



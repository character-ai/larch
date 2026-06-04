### FINDING_1: [OUT_OF_SCOPE] Pause-save clears recovery metadata on contradictory publish envelope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` forces `PUBLISH_OK=false` on non-zero publish exit with `PUBLISH_OK=true` in stdout, but also clears `RECOVERY_BRANCH`. That diverges from `design-publish.sh` and can drop a valid recovery branch after a post-push failure, preventing a resumable pause marker or recovery summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] render-final-summary accepts unvalidated repo
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-boundary-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` uses caller-provided `--repo` for issue URLs and summary upsert paths without validating the `OWNER/REPO` grammar, risking misleading links or wrong GitHub targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_13: [OUT_OF_SCOPE] tracking-issue-write lacks repo validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/tracking-issue-write.sh` still accepts `--repo` without entry validation, so malformed repo strings may reach rename/comment GitHub paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] Design-log admin merge remains high privilege
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Admin merge for design log PRs remains a high-privilege operation with pre-existing blast radius if credentials are over-scoped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_16: [OUT_OF_SCOPE] design-postplan-emit invocations do not consistently forward repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: important
- **Concern**: Some `design-postplan-emit.sh` call sites and reference docs omit `${REPO:+--repo "$REPO"}` even when the surrounding prelude uses the resolved shell `REPO`, risking pause or publish actions against a default repo when `source-env.sh` is missing or stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_2: [OUT_OF_SCOPE] Postplan internal pause misreports invalid repo as paused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` handles malformed resolved repo during an internal pause locally instead of delegating cleanly to `design-pause-save.sh`, and may persist `POSTPLAN_EMIT_STATUS=paused` even though no pause marker was written. Operators or orchestrator logic can treat the run as resumable when it actually failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] publish-skipped sentinel prevents later Step 5c retry
- **Reviewer(s)**: dyn-publish-state-output.txt
- **Severity**: nit
- **Concern**: Writing `.completed/step-5c` for empty `SESSION_ID` is intentional, but if the empty session id was accidental and later fixed, resume will not return to Step 5c publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-state-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_25: [OUT_OF_SCOPE] failed-plan-write summaries may point to unpublished logs
- **Reviewer(s)**: dyn-summary-renderer-output.txt
- **Severity**: latent
- **Concern**: `failed-plan-write` can set `RUN_LOGS_PATH` when a session id exists, even if the log tree was never published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_26: [OUT_OF_SCOPE] git-dependent recovery branch validation can drop recovery metadata
- **Reviewer(s)**: dyn-summary-renderer-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovery branch sanitizers call `git check-ref-format`; if `git` is unavailable or unsuitable in the runtime environment, valid recovery branch metadata may be silently cleared from warnings, exports, or final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_28: [OUT_OF_SCOPE] Miscellaneous pre-existing shell-boundary gaps remain
- **Reviewer(s)**: dyn-shell-boundary-output.txt
- **Severity**: latent
- **Concern**: Remaining pre-existing concerns include `named-block-write.sh` trusting `gh repo view` output when `--repo` is omitted, `LARCH_DESIGN_LOG_PUBLISH` overriding the publish helper path, and `design-publish.sh` session-id validation being weaker than full slug grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-boundary-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_31: [OUT_OF_SCOPE] resolve-repo validation refactor is outside named scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `resolve-repo.sh` split a pre-existing combined validation expression into separate checks. The behavior appears equivalent, but the refactor was outside the named findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_6: [OUT_OF_SCOPE] SKILL.md mirrors publish logic and may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Clarify and Step 5c prose in `skills/design/SKILL.md` duplicates script publish behavior. Without structural checks or helper extraction, prose and driver behavior may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] Duplicate source-env awk parsers may diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` and `design-postplan-emit.sh` each contain awk export parsers for `source-env.sh`; changes to quoting rules could be implemented inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated



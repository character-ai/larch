### FINDING_1: [OUT_OF_SCOPE] Pause-save clears recovery metadata on contradictory publish envelope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` forces `PUBLISH_OK=false` on non-zero publish exit with `PUBLISH_OK=true` in stdout, but also clears `RECOVERY_BRANCH`. That diverges from `design-publish.sh` and can drop a valid recovery branch after a post-push failure, preventing a resumable pause marker or recovery summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Postplan internal pause misreports invalid repo as paused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` handles malformed resolved repo during an internal pause locally instead of delegating cleanly to `design-pause-save.sh`, and may persist `POSTPLAN_EMIT_STATUS=paused` even though no pause marker was written. Operators or orchestrator logic can treat the run as resumable when it actually failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-repo-binding-output.txt, dyn-publish-state-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Duplicated repo-validation logic risks drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `validate_repo` and publish-metadata sanitization are duplicated across multiple scripts. Future changes to accepted `OWNER/REPO` syntax or hardening rules could be applied inconsistently, allowing malformed repo strings through one path but not another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: Duplicate/ambiguous structure-test assertion labels
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Several `test-design-structure.sh` assertions reuse labels such as `(27)` or `(FINDING_20)` for unrelated checks, making CI failures ambiguous and harder to triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Collateral repo-validation surfaces were not documented in plan scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Additional repo-validation changes in files such as `named-block-write`, `resolve-repo`, `tracking-issue-summary`, `upsert-diagrams`, `write-design-current-env`, and `run-logs.md` were not named in the plan, which can look like accidental scope creep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] SKILL.md mirrors publish logic and may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Clarify and Step 5c prose in `skills/design/SKILL.md` duplicates script publish behavior. Without structural checks or helper extraction, prose and driver behavior may diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Duplicate source-env awk parsers may diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` and `design-postplan-emit.sh` each contain awk export parsers for `source-env.sh`; changes to quoting rules could be implemented inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Step 5c publish-failure sentinel behavior lacks executable coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Step 5c rule that `.completed/step-5c` must be withheld when publish fails is covered only by structural greps, not an offline harness that simulates `PLAN_WRITE_OK=true`, `SESSION_ID` set, and `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Clarify publish-failure branching lacks executable coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Clarify-loop `SUMMARY_OUTCOME` branching is grep-only. A regression could revert failed clarify publish handling to unconditional `cancelled-clarify` without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: resolve-repo malformed-output rejection lacks targeted tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New fail-closed rejection in `scripts/resolve-repo.sh` lacks `test-resolve-repo.sh` cases for malformed resolved values such as flag-shaped repos or double-dot components.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: design-publish fallback repo is not revalidated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/design-publish.sh` does not re-run `validate_repo` after the `gh repo view` fallback, so unexpected `nameWithOwner` output could reach later `gh --repo` or publish calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] render-final-summary accepts unvalidated repo
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-boundary-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` uses caller-provided `--repo` for issue URLs and summary upsert paths without validating the `OWNER/REPO` grammar, risking misleading links or wrong GitHub targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-boundary-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] tracking-issue-write lacks repo validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/tracking-issue-write.sh` still accepts `--repo` without entry validation, so malformed repo strings may reach rename/comment GitHub paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Design-log admin merge remains high privilege
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Admin merge for design log PRs remains a high-privilege operation with pre-existing blast radius if credentials are over-scoped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Clarify publish failure prose omits full append-tool-failure details
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` clarify publish-failure instructions do not include the full `append-tool-failure.sh` invocation with site, tool, exit code, and output-file details, weakening `execution-issues.md` diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] design-postplan-emit invocations do not consistently forward repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: important
- **Concern**: Some `design-postplan-emit.sh` call sites and reference docs omit `${REPO:+--repo "$REPO"}` even when the surrounding prelude uses the resolved shell `REPO`, risking pause or publish actions against a default repo when `source-env.sh` is missing or stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_17: Clarify helper scripts pass unvalidated repo to gh
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `clarify-state.sh`, `clarify-comment-post.sh`, and `clarify-label.sh` thread caller `--repo` through to `gh` paths without the same grammar validation added to publish and pause paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_18: design-pause-load validates marker repo only after first gh call
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` accepts `--repo` and uses it for `gh issue view` before validating it; marker repo validation happens only later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_19: Clarify publish recovery metadata may be lost across Bash calls
- **Reviewer(s)**: dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: Clarify publish instructions parse `DESIGN_LOG_*` values in one Bash block, but the final summary fence re-exports only variables available in the current subshell. Failed-publish summaries can omit PR or recovery metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-state-output.txt: Address the concern above.

### FINDING_20: Pause prelude can repeatedly reattempt terminal pause failures
- **Reviewer(s)**: dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: The canonical pause prelude `exec`s `design-pause-save.sh` when `.pause-requested` exists. If pause-save emits `PAUSE_OK=false` without removing the sentinel, later steps can repeatedly hit the same failing pause path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-state-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] publish-skipped sentinel prevents later Step 5c retry
- **Reviewer(s)**: dyn-publish-state-output.txt
- **Severity**: nit
- **Concern**: Writing `.completed/step-5c` for empty `SESSION_ID` is intentional, but if the empty session id was accidental and later fixed, resume will not return to Step 5c publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-state-output.txt: Address the concern above.

### FINDING_22: publish-skipped runs use the same success footer as completed publish
- **Reviewer(s)**: dyn-summary-renderer-output.txt
- **Severity**: latent
- **Concern**: Step 5d prints the normal success footer for `publish-skipped`, even though the summary says run-log publish was skipped. Operators may miss that logs were not flushed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt: Address the concern above.

### FINDING_23: Final-summary fallback places outcome notes differently than primary renderer
- **Reviewer(s)**: dyn-summary-renderer-output.txt
- **Severity**: latent
- **Concern**: `compose_self_fallback` emits `publish-skipped` and `failed-publish` notes before the standard summary sentinel, while the primary render path appends them after it. Renderer failure changes summary structure, not only the degraded banner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt: Address the concern above.

### FINDING_24: publish-skipped note can falsely claim no SESSION_ID
- **Reviewer(s)**: dyn-summary-renderer-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.sh` always says publish was skipped due to no `SESSION_ID`, even when callers provide a real `--run-id` with outcome `publish-skipped`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] failed-plan-write summaries may point to unpublished logs
- **Reviewer(s)**: dyn-summary-renderer-output.txt
- **Severity**: latent
- **Concern**: `failed-plan-write` can set `RUN_LOGS_PATH` when a session id exists, even if the log tree was never published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] git-dependent recovery branch validation can drop recovery metadata
- **Reviewer(s)**: dyn-summary-renderer-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovery branch sanitizers call `git check-ref-format`; if `git` is unavailable or unsuitable in the runtime environment, valid recovery branch metadata may be silently cleared from warnings, exports, or final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-renderer-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Pause-save does not validate SESSION_ID/RUN_ID from source-env before publishing state
- **Reviewer(s)**: dyn-shell-boundary-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` reads `SESSION_ID` and `RUN_ID` from `source-env.sh` without validating newline/CR or slug constraints before writing them into pause state and passing `RUN_ID` to publish tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-boundary-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Miscellaneous pre-existing shell-boundary gaps remain
- **Reviewer(s)**: dyn-shell-boundary-output.txt
- **Severity**: latent
- **Concern**: Remaining pre-existing concerns include `named-block-write.sh` trusting `gh repo view` output when `--repo` is omitted, `LARCH_DESIGN_LOG_PUBLISH` overriding the publish helper path, and `design-publish.sh` session-id validation being weaker than full slug grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-boundary-output.txt: Address the concern above.

### FINDING_29: source_env_get is not printf-%q-safe for $'...' values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `source_env_get` strips simple single and double quotes but not `$'...'` quoting that `printf '%q'` may produce for shell-special values, so future expanded value domains could be parsed incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_30: design-log-publish malformed-repo tests omit required values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-log-publish.sh` does not include explicit plan-required malformed repo cases such as `bad..repo` and `a/b/c`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] resolve-repo validation refactor is outside named scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `resolve-repo.sh` split a pre-existing combined validation expression into separate checks. The behavior appears equivalent, but the refactor was outside the named findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_32: rc-ok-false path logs the same publish failure twice
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: In `design-pause-save.sh`, the contradictory-envelope path calls `log_failure`, then immediately enters the existing `PUBLISH_OK != true` block that logs the same failure again, duplicating Tool Failures entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_33: Collateral repo-validation hardening lacks targeted tests and exit-code documentation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `named-block-write.sh`, `tracking-issue-summary.sh`, `upsert-diagrams-comment.sh`, and `write-design-current-env.sh` gained repo-validation changes outside the implementation plan, but corresponding rejection-path tests and exit-code documentation were not updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

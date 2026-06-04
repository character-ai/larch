# Review Round 4

- Mode: `diff`
- 16 accepted, 4 rejected (2 exonerated)

## Accepted Findings

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


### FINDING_15: Clarify publish failure prose omits full append-tool-failure details
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` clarify publish-failure instructions do not include the full `append-tool-failure.sh` invocation with site, tool, exit code, and output-file details, weakening `execution-issues.md` diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_27: Pause-save does not validate SESSION_ID/RUN_ID from source-env before publishing state
- **Reviewer(s)**: dyn-shell-boundary-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` reads `SESSION_ID` and `RUN_ID` from `source-env.sh` without validating newline/CR or slug constraints before writing them into pause state and passing `RUN_ID` to publish tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-boundary-output.txt: Address the concern above.


### FINDING_30: design-log-publish malformed-repo tests omit required values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-log-publish.sh` does not include explicit plan-required malformed repo cases such as `bad..repo` and `a/b/c`.
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

### FINDING_4: Duplicate/ambiguous structure-test assertion labels
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Several `test-design-structure.sh` assertions reuse labels such as `(27)` or `(FINDING_20)` for unrelated checks, making CI failures ambiguous and harder to triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


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



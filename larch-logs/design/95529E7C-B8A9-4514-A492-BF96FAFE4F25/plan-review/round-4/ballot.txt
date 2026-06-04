### FINDING_1: Clarify structural assertion anchors on wrong sub-step
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 0b clarify structural assertion is planned around a non-existent or wrong “sub-step 3.5” anchor, which could miss the intended clarify publish/rename contract or match the wrong Gate B section instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the assertion to ordering between the line-463 publish bullet (non-zero _publish_rc forces PUBLISH_OK=false) and the line-465 rename gate (SESSION_ID non-empty and PUBLISH_OK=true); drop "sub-step 3.5" from the grep anchor and align plan/test-design-structure.md wording with clarify sub-step 5

### FINDING_2: Pause marker gating contradicts recovery path
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan says pause marker writing remains gated on `PUBLISH_OK=true`, but the existing required recovery path writes a resumable marker when publish exits non-zero with `PUBLISH_OK=false` and a valid `RECOVERY_BRANCH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Rewrite that plan bullet to say the existing PUBLISH_OK=false plus valid RECOVERY_BRANCH path must continue through redaction and marker write; only normalize non-zero plus PUBLISH_OK=true before entering that existing branch
  - From Codex-Requirements: Revise the plan sentence to say marker write remains allowed after either PUBLISH_OK=true or a validated RECOVERY_BRANCH, or delete that sentence because the prior bullet and tests already define the contract

### FINDING_3: Clarify publish failure path loses recovery metadata and may advertise run logs
- **Reviewer(s)**: Codex-dyn-publish-contract
- **Severity**: important
- **Concern**: The proposed clarify publish parity change forces `PUBLISH_OK=false` on non-zero publish exit, but does not preserve recovery metadata or suppress the run-log success path, so final summaries can advertise a run-log path while omitting the recovery branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-contract: Extend the Step 0b clarify publish parsing to capture PR_NUMBER, PR_URL, and RECOVERY_BRANCH, export DESIGN_LOG_* on failure, and render a failed-publish/suppressed-run-logs summary when an attempted clarify publish ends with PUBLISH_OK!=true.

### FINDING_4: Publish-skipped fallback renderer path lacks explicit coverage
- **Reviewer(s)**: Cursor-dyn-summary-operator, Codex-dyn-summary-operator
- **Severity**: important
- **Concern**: The plan adds publish-skipped summary behavior but lacks an explicit degraded fallback test for when `render-run-summary.sh` fails, leaving room for fallback output to leak failed-publish recovery prose or synthetic `larch-logs/design/unknown/` run logs while primary tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-summary-operator: Add a `publish-skipped` renderer-fail test: empty `SESSION_ID`, stub renderer failure, assert the skipped-publish note, no recovery bullets, **Run logs** `N/A`, and no `larch-logs/design/unknown/` in `final-summary.md`; optionally add `publish-skipped` to the post-publish outcome matrix loop and update the pass label from thirteen-outcome.
  - From Codex-dyn-summary-operator: Add one renderer-fail publish-skipped case beside the existing fallback block: run with SESSION_ID empty and --outcome publish-skipped, then assert the skipped-publish note, no Publish recovery / Log recovery / Log flush PR text, Run logs N/A, no larch-logs/design/unknown/, and stdout/file identity. Update skills/design/scripts/test-render-final-summary.md to document both primary and degraded fallback coverage.

### FINDING_5: Pause-check call sites do not pass repo to new pause-save validation
- **Reviewer(s)**: Codex-dyn-repo-boundary
- **Severity**: important
- **Concern**: The plan adds `design-pause-save --repo` validation, but canonical pause-check invocations still call the helper without forwarding `REPO`, so non-default repo runs may resolve the hub default before GitHub reads, publish, or marker writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-repo-boundary: Update the canonical prelude and duplicated SKILL.md pause-check blocks to pass ${REPO:+--repo "$REPO"}, or route them through one tested snippet; add a structural test that pause-check invocations forward REPO.

### FINDING_6: SECURITY.md omits pause-save repo validation boundary
- **Reviewer(s)**: Codex-dyn-repo-boundary
- **Severity**: latent
- **Concern**: The planned SECURITY.md update covers malformed `--repo` fail-closed behavior for design-log publishing, but not the new pause/resume marker write boundary in `design-pause-save`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-repo-boundary: Add one sentence to the existing /design pause/resume marker binding paragraph documenting the design-pause-save --repo OWNER/REPO validation and early invalid-repo failure before gh issue view, publish, or marker writes.

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (planned); skills/design/SKILL.md:460-465
- **Concern**: Step 0b clarify structural assertion anchors on non-existent "sub-step 3.5" rename gate. Scenario: Step 0b clarify uses sub-steps 3 (publish) and 5 (tracking-issue-write rename at line 465); "3.5" in SKILL.md is Gate B (line 1140+), not clarify. A literal grep for sub-step 3.5 before tracking-issue-write can miss the clarify contract, match the wrong step, or fail while the SKILL regression remains unenforced
- **Proposed resolution**: Pin the assertion to ordering between the line-463 publish bullet (non-zero _publish_rc forces PUBLISH_OK=false) and the line-465 rename gate (SESSION_ID non-empty and PUBLISH_OK=true); drop "sub-step 3.5" from the grep anchor and align plan/test-design-structure.md wording with clarify sub-step 5

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-pause-save.sh:180-211
- **Concern**: Plan text says pause marker write remains gated on PUBLISH_OK=true, but the existing recovery contract writes the marker after PUBLISH_OK=false when RECOVERY_BRANCH is valid. Scenario: If implemented literally, exit 1 plus PUBLISH_OK=false plus RECOVERY_BRANCH would stop producing a resumable pause marker, breaking the recovery path the plan says to preserve
- **Proposed resolution**: Rewrite that plan bullet to say the existing PUBLISH_OK=false plus valid RECOVERY_BRANCH path must continue through redaction and marker write; only normalize non-zero plus PUBLISH_OK=true before entering that existing branch

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:180-223
- **Concern**: Plan contradicts the required pause recovery path by saying marker write remains gated on PUBLISH_OK=true. Scenario: An implementer could follow that sentence and move marker writing behind PUBLISH_OK=true, breaking the accepted rc=1 plus PUBLISH_OK=false plus RECOVERY_BRANCH path that should still write a resumable pause marker
- **Proposed resolution**: Revise the plan sentence to say marker write remains allowed after either PUBLISH_OK=true or a validated RECOVERY_BRANCH, or delete that sentence because the prior bullet and tests already define the contract

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-publish-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:460-466; skills/design/scripts/render-final-summary.sh:295-298; scripts/design-log-publish.sh:926-929
- **Concern**: Clarify publish parity still does not preserve recovery metadata or suppress the run-log success path. Scenario: The proposed Step 0b change forces PUBLISH_OK=false on non-zero publish exit, but the clarify prose still only parses PUBLISH_OK. If design-log-publish exits 1 after push with PUBLISH_OK=false and RECOVERY_BRANCH, the clarify path skips rename but then renders cancelled-clarify with RUN_ID, so the final summary can advertise larch-logs/design/<run-id>/ while omitting the recovery branch.
- **Proposed resolution**: Extend the Step 0b clarify publish parsing to capture PR_NUMBER, PR_URL, and RECOVERY_BRANCH, export DESIGN_LOG_* on failure, and render a failed-publish/suppressed-run-logs summary when an attempted clarify publish ends with PUBLISH_OK!=true.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-summary-operator
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-render-final-summary.sh:69-70
- **Concern**: skills/design/scripts/test-render-final-summary.sh:535-571. Scenario: The plan adds a primary `--outcome publish-skipped` case and a `compose_self_fallback` branch in `render-final-summary.sh`, but it does not add a renderer-fail fallback harness case (stub `render-run-summary.sh` to exit non-zero) analogous to the existing `failed-publish` recovery test (~527-533) and cancelled fallback tests (~236-268). If `compose_self_fallback` omits the publish-skipped note or accidentally reuses `append_failed_publish_notes`, operators still see failed-publish recovery prose or a synthetic `larch-logs/design/unknown/` Run logs line on the degraded path.
- **Proposed resolution**: Add a `publish-skipped` renderer-fail test: empty `SESSION_ID`, stub renderer failure, assert the skipped-publish note, no recovery bullets, **Run logs** `N/A`, and no `larch-logs/design/unknown/` in `final-summary.md`; optionally add `publish-skipped` to the post-publish outcome matrix loop and update the pass label from thirteen-outcome.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-summary-operator
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-render-final-summary.sh:184-233; <TMPDIR>/plan.txt:69-70
- **Concern**: The plan adds the publish-skipped fallback code branch but only calls for generic render-final-summary coverage, not an explicit degraded fallback subcase.. Scenario: compose_self_fallback is a separate operator-visible path when render-run-summary.sh exits nonzero; a publish-skipped fallback could still leak failed-publish notes or larch-logs/design/unknown/ while the primary renderer test stays green.
- **Proposed resolution**: Add one renderer-fail publish-skipped case beside the existing fallback block: run with SESSION_ID empty and --outcome publish-skipped, then assert the skipped-publish note, no Publish recovery / Log recovery / Log flush PR text, Run logs N/A, no larch-logs/design/unknown/, and stdout/file identity. Update skills/design/scripts/test-render-final-summary.md to document both primary and degraded fallback coverage.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-repo-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:65-72,568-589,1561-1571; <TMPDIR>/plan.txt:33-35
- **Concern**: Plan adds design-pause-save --repo validation but leaves canonical pause-check call sites without --repo. Scenario: A /design run bound to a non-default repo can hit .pause-requested; the prelude execs design-pause-save with only --issue, so the helper resolves the hub default before gh issue view, publish, and marker writes. The new validation only checks that default/resolved repo and does not cover this direct invocation surface.
- **Proposed resolution**: Update the canonical prelude and duplicated SKILL.md pause-check blocks to pass ${REPO:+--repo "$REPO"}, or route them through one tested snippet; add a structural test that pause-check invocations forward REPO.

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-repo-boundary
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:86-91,221; <TMPDIR>/plan.txt:111-112
- **Concern**: SECURITY.md update is scoped only to design-log-publish, but the plan also changes the pause/resume marker write boundary. Scenario: After the proposed pause-save guard lands, SECURITY.md would document design-log malformed --repo fail-closed behavior but not the pause-save direct GitHub issue read/write boundary that now rejects malformed non-empty --repo before gh/stateful marker work.
- **Proposed resolution**: Add one sentence to the existing /design pause/resume marker binding paragraph documenting the design-pause-save --repo OWNER/REPO validation and early invalid-repo failure before gh issue view, publish, or marker writes.

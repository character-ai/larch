### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:221
- **Concern**: Plan adds fail-closed --repo validation to design-log-publish.sh but omits the required SECURITY.md update. Scenario: Security docs for the design-log publish boundary stay stale and do not record that malformed --repo values now exit 1 before gh calls
- **Proposed resolution**: Add a short note to the design-log publish paragraph that --repo is validated as OWNER/REPO and malformed values fail closed with exit 1 before network operations

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1119-1121
- **Concern**: Proposed FINDING_25 harness id `(25)` already labels two unrelated assertions. Scenario: Adding the publish-gate grep as `(25)` collides with existing `(25)` fail messages for `design_reentry_marker_write` ordering; a regression in the new gate can be misread as a marker-order failure or the new check can be dropped while reusing an ambiguous id
- **Proposed resolution**: Use an unused id such as `(27)` (after `(26)` session-cache anchors at 1173-1177), or extend the existing `(15b)` step-5c sentinel grep at 1134-1135 instead of introducing `(25)`

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: .claude/rules/script-md-siblings.md:8-17
- **Concern**: Plan updates five test .sh harnesses but omits their required sibling .md contract updates. Scenario: The repo rule requires each changed script or harness to update its sibling .md in the same PR, so the plan can land behavior changes with stale harness docs and violate the edit-in-sync contract
- **Proposed resolution**: Add UPDATED entries for scripts/test-design-structure.md, skills/design/scripts/test-design-publish.md, scripts/test-design-log-publish.md, skills/design/scripts/test-render-final-summary.md, and scripts/test-render-run-summary.md documenting the new regression cases

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-wire-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:463-465
- **Concern**: Step 0b clarify still gates on parsed PUBLISH_OK=true even when design-log-publish exits non-zero. Scenario: The plan hardens Step 5c via design-publish.sh, but clarify calls design-log-publish.sh directly; if it emits PUBLISH_OK=true and exits non-zero, substep 3.5 can run the PUBLISH_OK-gated rename despite a failed publish
- **Proposed resolution**: Mirror the fail-closed rule in the clarify publish prose before any rename action: after parsing stdout, any non-zero _publish_rc sets PUBLISH_OK=false and records the publish warning

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-caller-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1119-1121
- **Concern**: FINDING_25 proposes a new `(25)` assertion but that ID is already used for design_reentry_marker_write ordering checks. Scenario: Implementer adds a second `(25)` fail message; CI failures become ambiguous and the harness numbering convention drifts
- **Proposed resolution**: Use `(27)` for the new Step 5c publish-gate grep assertion instead of `(25)`

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-caller-compat
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:53-59
- **Concern**: The plan says empty --repo is treated as no repo, but the current argv parser rejects an explicit empty --repo value before the proposed validate_repo call can run.. Scenario: Docs or tests may claim `--repo ""` falls back to the hub default, while direct users actually get a structural argv failure with no PUBLISH_OK stream; in-repo callers already omit empty repos via `${REPO:+--repo "$REPO"}`.
- **Proposed resolution**: Keep the minimum change: document and test omitted --repo as the hub-default path, and treat explicit empty --repo as invalid/required-value exit 1 rather than changing the parser to accept it.

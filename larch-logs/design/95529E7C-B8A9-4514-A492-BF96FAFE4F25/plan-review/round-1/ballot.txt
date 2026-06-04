### FINDING_1: SECURITY.md missing design-log publish --repo validation note
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan adds fail-closed `--repo` validation to `design-log-publish.sh` but does not update `SECURITY.md`. Security documentation for the design-log publish boundary would stay stale and would not record that malformed `--repo` values now exit 1 before `gh` calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a short note to the design-log publish paragraph that --repo is validated as OWNER/REPO and malformed values fail closed with exit 1 before network operations

### FINDING_2: Harness assertion id `(25)` collision in test-design-structure.sh
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-caller-compat
- **Severity**: important
- **Concern**: The proposed new publish-gate grep would reuse harness id `(25)`, which already labels unrelated `design_reentry_marker_write` ordering assertions. A regression in the new gate could be misread as a marker-order failure, or the new check could be dropped while reusing an ambiguous id; CI failures become ambiguous and the harness numbering convention drifts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use an unused id such as `(27)` (after `(26)` session-cache anchors at 1173-1177), or extend the existing `(15b)` step-5c sentinel grep at 1134-1135 instead of introducing `(25)`
  - From Cursor-dyn-caller-compat: Use `(27)` for the new Step 5c publish-gate grep assertion instead of `(25)`

### FINDING_3: Changed test harnesses missing required sibling .md updates
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan updates five test `.sh` harnesses but omits their required sibling `.md` contract updates. Per repo rule, each changed script or harness must update its sibling `.md` in the same PR; the plan could land behavior changes with stale harness docs and violate the edit-in-sync contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED entries for scripts/test-design-structure.md, skills/design/scripts/test-design-publish.md, scripts/test-design-log-publish.md, skills/design/scripts/test-render-final-summary.md, and scripts/test-render-run-summary.md documenting the new regression cases

### FINDING_4: Step 0b clarify still gates rename on PUBLISH_OK after non-zero publish exit
- **Reviewer(s)**: Codex-dyn-wire-contract
- **Severity**: important
- **Concern**: Step 0b clarify still gates on parsed `PUBLISH_OK=true` even when `design-log-publish` exits non-zero. The plan hardens Step 5c via `design-publish.sh`, but clarify calls `design-log-publish.sh` directly; if it emits `PUBLISH_OK=true` and exits non-zero, substep 3.5 can run the `PUBLISH_OK`-gated rename despite a failed publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-wire-contract: Mirror the fail-closed rule in the clarify publish prose before any rename action: after parsing stdout, any non-zero _publish_rc sets PUBLISH_OK=false and records the publish warning

### FINDING_5: Explicit empty `--repo` behavior diverges from documented hub-default fallback
- **Reviewer(s)**: Codex-dyn-caller-compat
- **Severity**: latent
- **Concern**: The plan says empty `--repo` is treated as no repo, but the current argv parser rejects an explicit empty `--repo` value before the proposed `validate_repo` call can run. Docs or tests may claim `--repo ""` falls back to the hub default, while direct users actually get a structural argv failure with no `PUBLISH_OK` stream; in-repo callers already omit empty repos via `${REPO:+--repo "$REPO"}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-caller-compat: Keep the minimum change: document and test omitted --repo as the hub-default path, and treat explicit empty --repo as invalid/required-value exit 1 rather than changing the parser to accept it.

### FINDING_1: Cancel render handoff must preserve explicit repo forwarding
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Innovation, Codex-Requirements, Codex-dyn-driver-contract, Codex-dyn-quiet-channel, Codex-dyn-state-identity
- **Severity**: important
- **Concern**: Moving planned cancel render calls into `design-route.sh` risks dropping `${REPO:+--repo "$REPO"}`. For `/design` runs bound to a non-default repo, `render-final-summary.sh` may lose repo-specific issue URLs, upsert the final summary against the hub/default repo, or fail against the wrong issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the existing ${REPO:+--repo "$REPO"} on both driver-owned cancel render-final-summary.sh calls and add/update the structure pin so command-scoped render covers repo forwarding as well as ISSUE_NUMBER/SESSION_ID.
  - From Codex-Edge, Codex-Pragmatic: Add ${REPO:+--repo "$REPO"} to both design-route.sh cancel render invocations and pin/document it
  - From Codex-Innovation: Add ${REPO:+--repo "$REPO"} to both design-route.sh cancel render invocations, and pin/document that render repo forwarding is preserved.
  - From Codex-Requirements: Add ${REPO:+--repo "$REPO"} to both design-route.sh render-final-summary.sh quiet branches and pin it in design-route.md and scripts/test-design-structure.sh
  - From Codex-dyn-driver-contract: Preserve ${REPO:+--repo "$REPO"} on both design-route.sh cancel render calls and add a structure-test pin for that argv on the render-final-summary.sh lines.
  - From Codex-dyn-quiet-channel, Codex-dyn-state-identity: Add ${REPO:+--repo "$REPO"} to both cancel render invocations in design-route.sh and pin it in the route/docs structure checks.

### FINDING_2: Resume manual flag must pass required boolean value
- **Reviewer(s)**: Codex-Edge, Codex-Requirements, Codex-dyn-quiet-channel
- **Severity**: important
- **Concern**: Resume forwarding is described as a bare `--manual-requested`, but `write-design-current-env.sh` requires a true/false value. On manual resume, the bare flag can consume the next flag as its value, lose repo forwarding, fail argument parsing, or abort env refresh before resume routing completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Specify and pin _wdce_resume_args+=(--manual-requested true) when manual_gate_b is true
  - From Codex-Requirements: Specify and test _wdce_resume_args+=(--manual-requested true) when manual_gate_b is true, not a bare --manual-requested flag
  - From Codex-dyn-quiet-channel: Specify --manual-requested true in the resume argv construction and related docs/tests, matching the current SKILL.md call shape.

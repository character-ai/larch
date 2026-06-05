### [Plan Review] FINDING_4

### FINDING_4: Design MAV start timestamp artifact may violate strict plan-review artifact allowlist
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: If design MAV stores a new round-start artifact in the plan-review round directory without updating the strict artifact allowlist, `design-log-publish.sh` can reject the unexpected file and fail final log publishing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not create a new round-dir artifact; store ROUND_START_S in the already-allowlisted round-summary.env, or explicitly add the new basename to lib-design-round-artifacts.sh plus its docs and tests


### [Plan Review] FINDING_7

### FINDING_7: Design MAV round-start persistence path is not canonicalized
- **Reviewer(s)**: Cursor-dyn-telemetry-contract
- **Severity**: latent
- **Concern**: Design MAV start persistence lacks a shared filename/read contract between the loop and SKILL prompt-side helper, so writer and reader can diverge or fall back to an incorrect timestamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-telemetry-contract: Writer and reader can pick different paths, fall back to date +%s, and emit near-zero or wrong duration_seconds for MAV rounds. Reuse the implement round-start-s filename under plan-review/round-N/ (or add --start-s-file to the helper), write it in plan-review-loop on main-agent-vote-required, and have SKILL.md pass that path explicitly.


### FINDING_1: Stale Step 8+ re-entry docs missing foreground handoff clear
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan updates `skills/implement/SKILL.md` (and related main Step 8 surfaces) but leaves load-on-demand Step 8+ relaunch reference docs stale: `skills/implement/references/stall-recovery.md`, `skills/implement/references/ship-pr-ci-fix.md`, `skills/implement/references/conflict-resolution.md`, and `skills/implement/references/ship-pr-exit-matrix.md`. Those files are the prompts loaded on `step8-shippr`, `ci-fix`, conflict-resolution re-entry, and `reship`. Without a separate foreground pre-launch `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" 2>/dev/null || true` before each `step-8-ship.sh` re-invoke, stale sidecars can misroute premature `<task-notification>` handling before wrapper-entry cleanup runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these docs to `### UPDATED` and mirror the same foreground pre-launch clear in each re-entry block, not just in `SKILL.md`.
  - From Codex-Requirements: Add the four re-entry docs to `### UPDATED:` and insert the same separate foreground sidecar-clear step immediately before each `step-8-ship.sh` re-invoke bullet.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)


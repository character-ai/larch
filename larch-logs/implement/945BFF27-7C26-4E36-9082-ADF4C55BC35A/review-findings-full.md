### REJ_C1: Cursor-testing (round 1) [code-review/rejected]

**Finding**: larch-logs/implement/ trees committed on feature branch add unrelated session artifacts.
**Reason not implemented**: larch-log commits are intentional per repo design. The `/implement` workflow commits larch-logs to the branch as part of the normal PR flow; this is not a bug.

### REJ_C2: Cursor-plan-fidelity (round 1) [code-review/rejected]

**Finding**: FAILURE_LOG doc note added to scripts that always exit 0 is misleading.
**Reason not implemented**: The note "On non-zero exit, FAILURE_LOG=<path> may appear on stdout" follows the existing repo-wide convention established by prior phases (visible in check-reviewers.md, render-lane-status.md, collect-agent-results.md, etc.). Changing this convention is out of scope for Phase 5.

### REJ_C3: Multiple reviewers (round 1) [code-review/rejected]

**Finding**: ship-pr.sh and plugin.json bundled with Phase 5 changes.
**Reason not implemented**: These changes came from a prior implement run (031AE2E0) on this branch before the current session started. They include a legitimate ship-pr fix. Out of scope to split these.


# Review Round 2

- Mode: `diff`
- 3 accepted, 8 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Launch-failure sentinel written before append succeeds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On first collect after a failed brainstorm launch, `run-log append-failure` may fail silently (`|| true`), but the `.runlog-appended` sentinel is still created. Resume collect skips re-append and the failure never appears in `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only create `.runlog-appended` sentinel when append succeeds, or remove sentinel on append failure.


### FINDING_10: Stale dirty-tree-detected.env after clean re-collect
- **Reviewer(s)**: dyn-brainstorm-flow-output.txt
- **Severity**: important
- **Concern**: `design_brainstorm_dirty_checkpoint` writes `dirty-tree-detected.env` with `RECOVERY_REQUIRED=true` when dirty/unknown is detected, but never clears or rewrites that file when a later `--mode collect` run sees a clean checkpoint and clean `${path}.dirty-tree` sidecars. A stale env file can still carry `RECOVERY_REQUIRED=true` and block synthesis or Step 1d.7 even though the wrapper no longer emits a `WARN=` line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-brainstorm-flow-output.txt: When sidecar scan and `dirty-tree checkpoint` both resolve to clean, rewrite `dirty-tree-detected.env` with `RECOVERY_REQUIRED=false` (or remove the file), matching the post-restore contract in `brainstorm.md`.


### FINDING_4: Launch-failure log lookup ignores vendor-fallback stderr sink
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Launch-failure ingestion maps failure logs from the slot output basename, but `brainstorm.md` allows either vendor to run for either slot while keeping the slot's canonical output path. If Codex runs the framing fallback and writes `cursor-brainstorm-output.txt` with `codex-brainstorm-launch.failure.log`, `--mode collect -- cursor-brainstorm-output.txt` checks only `cursor-brainstorm-launch.failure.log`, so the Codex launch failure is never appended to `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Derive the failure sink from each output's `.meta` `STDERR_SINK=` when present, or check both canonical brainstorm launch logs per supplied output with per-log sentinels.



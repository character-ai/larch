### [Plan Review] FINDING_5

### FINDING_5: State rewrite helpers can erase canonical bash/orchestrator state keys
- **Reviewer(s)**: Codex-dyn-state-contracts
- **Severity**: important
- **Concern**: Planned `_write_ship_state` / `_write_terminal_state` calls preserve selected counters but may replace the canonical `ship-pr-state.sh` with a shortened Python field set, dropping stall, bail, failed-run, no-logs, pending-rebase, and other keys that bash/orchestrator paths still seed or validate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-contracts: Keep `_write_ship_state` as a narrow key-rewrite that preserves unknown existing keys, or expand it to the canonical key set and have `_write_terminal_state` write bash-compatible stall metadata and exit code


### [Plan Review] FINDING_6

### FINDING_6: Terminal and cap stall paths can still reset restored counters to zero
- **Reviewer(s)**: Cursor-dyn-resume-routing
- **Severity**: important
- **Concern**: Extending `_write_terminal_state` is insufficient unless every terminal/cap early-return site threads the restored and post-monitor counter values; otherwise exit-3/6 or cap handback can persist zeroed counters and cause the next run to resume at zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-resume-routing: In _write_terminal_state pass through optional counter kwargs; on every terminal/cap return (monitor non-OK, merge-loop cap after monitor, pre-rebase stall) compute post-monitor values (apply did_fixing/transient_rerun_attempted before write) and thread resume-restored baselines on open-pr



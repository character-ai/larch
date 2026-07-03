# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_5: Implement launchers do not clear stale clamp state
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: important
- **Concern**: Implement Step 3/5 bg-wait launchers do not reset old probe-denial counters or stale terminal sentinels. A fresh wait can inherit clamp state and deny the first real recovery probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Mirror the design/Step 8 launch hygiene in all implement Step 3/5 marker writers: on bg-wait start, `rm -f` the matching `bg-poll-guard-probe-denials.<sentinel>.count` and unlink the prior `.completed/step-3-terminal` / `.completed/step-5-terminal` sentinel before writing `.bg-wait-active`.



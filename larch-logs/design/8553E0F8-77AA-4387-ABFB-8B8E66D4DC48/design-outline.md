## Proposed Design Outline

### Goals
- Eliminate the `/design` Step 3 background-wait deadlock (premature `<task-notification>` + hook denial → up to ~14 min stall, 28 denied probes).
- Let the orchestrator confirm a spurious notification mid-wait by reading the write-once task-output file, which the hook currently denies.
- Reduce/prevent the premature notification itself during the long silent review window (defense in depth).

### Non-goals
- No upstream Claude Code fix (Fix D); capture it as an OOS follow-up.
- Do not weaken the hook's denial of genuine Bash sentinel-polling probes during a live wait.
- No change to plan-review loop logic, the round cap, or the `normalize-status` terminal KV contract.

### Approach sketch (Fix A + B + C, defense in depth)
- Fix A: in `scripts/hook-bg-poll-guard.sh` Read path (~line 1150), drop the `path_is_task_output && bash_probe_target_dir_plausible` OR-clause so write-once `tasks/*.output` reads are never denied; remove the orphaned `path_is_task_output` helper.
- Fix C: in `skills/design/scripts/design-step3-review.sh`, emit a periodic stdout keepalive during the blocking `wait "$_loop_pid"` window, torn down before `normalize-status` so terminal KV stays clean.
- Fix B: document in `AGENTS.md` + `skills/shared/design-background-wait.md` that task-output reads are allowed and how empty / heartbeat-only output maps to silent-yield vs the terminal sentinel.
- Update harnesses in the same change.

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh` (+ `.md` sibling), `scripts/test-hook-bg-poll-guard.sh`
- `skills/design/scripts/design-step3-review.sh` (+ `.md` sibling), `skills/design/scripts/test-design-step3-review.sh`
- `skills/shared/design-background-wait.md`, `AGENTS.md`

### Open questions
- Heartbeat interval + stdout format that keeps activity without tripping the empty-output rule or the KV parser (resolve in drafting/review).
- Exact Claude Code notification trigger is unknown (upstream); Fix A/B are the guaranteed recovery, Fix C is best-effort prevention.

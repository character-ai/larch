## Proposed Design Outline

### Goals
- Remove every larch dependency on Bash `run_in_background` and `<task-notification>` waits.
- Ship stdlib-only `python3 python/cli.py bgjob {start,wait,status,reap}`: setsid daemons, identity-checked registry, atomic result envs, budget self-expiry, dead-man switch, reap.
- Replace background waits with chunked foreground `bgjob wait` loops (270s chunks, `timeout: 330000`) per one shared contract doc.

### Non-goals
- No waiter-subagent wait mode, now or later (explicit user refusal). Direct-loop is the only wait topology.
- No removal of the legacy defense stack (bg-poll hooks, bg-wait machinery, `design-background-wait.md`); issue 2 owns deletion.
- No behavior change to step routing: existing terminal sentinels keep being written during transition.

### Approach sketch
- New package `python/larch/bgjob/` behind `python3 python/cli.py bgjob ...`; daemon is double-forked + `setsid`, never a child of the Bash tool; registry entries carry PID + start-time identity (never bare PID).
- New `skills/shared/bgjob-wait.md` orchestrator contract; every migrated call site points at it.
- Migrate all inventory spawn sites (5 /design, 6 /implement, /review audit, /research lanes) to `bgjob start` + looped `bgjob wait`; wrappers emit exactly one `BGJOB_STATUS=STARTED` stdout line.
- New PreToolUse hook denies `run_in_background: true` while a larch run is active; repurpose `lint bg-wait-coverage` into its inverse allowlist lint.
- Document optional `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` for dedicated runner sessions in `docs/configuration-and-permissions.md`.

### Surfaces in scope
- `python/larch/bgjob/` (new), `python/cli.py`, `python/tests/bgjob/` (new)
- `skills/shared/bgjob-wait.md` (new); migrated fences and references in `skills/design/`, `skills/implement/`, `skills/research/`; `python/larch/review/` standalone audit
- `python/larch/design/design_step5c.py`, `design_step6.py`/`design_core.py`, `python/larch/implement/step_7a.py`, `dispatch_commit_route.py`
- `hooks/hooks.json` + new hook script, `python/larch/lint/lint_bg_wait_coverage.py`, `scripts/cleanup-sessionstart.sh`, `docs/workflow-lifecycle.md`, `docs/configuration-and-permissions.md`, `skills/design/references/sentinel-host-table.md`

### Open questions
- None.

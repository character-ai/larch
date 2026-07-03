# step-8-ship.sh

Step 8+ Python ship-driver wrapper. It rehydrates durable ship argv from `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, derives `EXPECTED_TMPDIR_BASENAME_PREFIX` through fail-closed `python/cli.py implement clone-tag` capture, delegates the Python 3.11 guard to `step-8-python-guard.sh`, runs the advisory `8-pre-ship` phantom probe, and invokes `python/cli.py ship pr` with the canonical argv.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from Step 8+ in immediate-background mode. Pre-driver orchestration may run guard, initial seeding, and `oos file` first; post-driver continuations invoke only this wrapper.

## Stdout and sidecar contract

Wrapper stdout remains the single schema JSON object emitted by the guard or `python/cli.py ship pr`. The wrapper truncates `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture` at entry, captures guard and driver stdout through a synchronous `tee` pipeline, and extracts the JSON sidecar only after the producing pipeline has closed.

At entry, the wrapper clears stale `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` before arming the marker. On every exit, the trap writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc`. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` only when the current capture contains a schema JSON object, such as guard `STALLED` JSON or ship-driver JSON. If the current capture has no schema JSON, setup failures such as missing durable inputs or `clone-tag` failure produce rc-only sidecars and the trap unlinks any stale `.step-8-ship-handoff.json` from a previous attempt.

The wrapper writes `$IMPLEMENT_TMPDIR/.bg-wait-active` with `STEP=implement-step8-ship`, `TIMEOUT_S=21600`, and `CLONE_PATH` copied from `$IMPLEMENT_TMPDIR/.larch-keepalive` when available before the guard and driver calls. Entry clears `no-progress-turns.count`, `no-progress-circuit-breaker-armed`, and `bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count` so reused tmpdirs do not inherit stale no-progress or rc-probe clamp state. `persist_handoff` writes rc/json first and removes `.bg-wait-active` last on all exits. Handoff sidecar writes are fail-open so marker cleanup still runs. The hook release sentinel is the root-level `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc`, not a `.completed/` file.

`python/cli.py ship route-exit` consumes the `.rc` and `.json` sidecars. It does not consume live task-notification stdout.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Self-rehydrates `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, `MERGE`, `DRAFT`, `FORKED_TARGET`, `REPO_UNAVAILABLE`, `MANIFEST_PATH`, `TOOL_LABEL`, `NO_ADMIN_FALLBACK`, and `NO_LOGS_COMMIT` from `ship-pr-state.sh` before invoking the active driver.
- `EXPECTED_TMPDIR_BASENAME_PREFIX` comes from `python/cli.py implement clone-tag`; the ship wrapper and initial state seeder must share the same prefix.
- Guard rc 4 and `ship pr` JSON are capture-backed so `ship route-exit` can classify `NEXT_ACTION=stall` or another post-driver token.
- `SKILL.md` also requires a separate orchestrator foreground stale-handoff removal immediately before every Step 8+ `run_in_background` relaunch; wrapper entry cleanup is defense in depth.
- Setup failures without schema JSON are intentionally rc-only. The SKILL halts with Tool Failures before `route-exit` when the `.json` sidecar is absent.
- The Python version guard lives in `step-8-python-guard.sh`.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `step-8-seed-initial.md`, and `skills/implement/scripts/test-step-8-ship.sh` when this contract or argv changes.

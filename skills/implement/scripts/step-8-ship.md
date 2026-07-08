# step-8-ship.sh

Step 8+ Python ship-driver bgjob launcher. Foreground mode starts or rejoins bgjob step `implement-step8-ship`; child mode rehydrates durable ship argv from `$IMPLEMENT_TMPDIR/ship-pr-state.sh`, derives `EXPECTED_TMPDIR_BASENAME_PREFIX` through fail-closed `python/cli.py implement clone-tag` capture, delegates the Python 3.11 guard to `step-8-python-guard.sh`, runs the advisory `8-pre-ship` phantom probe, and invokes `python/cli.py ship pr` with the canonical argv.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from Step 8+ as a foreground bgjob launcher. Pre-driver orchestration may run guard, initial seeding, and `oos file` first; post-driver continuations invoke only this wrapper.

## Stdout and sidecar contract

Foreground wrapper stdout is exactly `BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=<n>` on a fresh start, or a bgjob wait envelope on live/completed rejoin. Child stdout remains the single schema JSON object emitted by the guard or `python/cli.py ship pr`. The child truncates `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture` at entry, captures guard and driver stdout through a synchronous `tee` pipeline, and extracts the JSON sidecar only after the producing pipeline has closed.

At entry, the wrapper clears stale `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` before arming the marker. On every exit, the trap writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc`. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` only when the current capture contains a schema JSON object, such as guard `STALLED` JSON or ship-driver JSON. If the current capture has no schema JSON, setup failures such as missing durable inputs or `clone-tag` failure produce rc-only sidecars and the trap unlinks any stale `.step-8-ship-handoff.json` from a previous attempt.

Fresh foreground launch clears stale handoff sidecars, removes stale canonical bgjob result envs, and recreates `$IMPLEMENT_TMPDIR/bgjob/implement-step8-ship.merge.env` before `bgjob start`. Child entry clears `no-progress-turns.count`, `no-progress-circuit-breaker-armed`, and `bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count` so reused tmpdirs do not inherit stale no-progress or rc-probe clamp state. `persist_handoff` writes rc/json, writes merge-result KVs (`STEP8_HANDOFF_RC`, `STEP8_HANDOFF_JSON_PRESENT`, and sidecar paths), and leaves legacy `.bg-wait-active` absent. Merge-result publication is fail-closed: if the merge-result env write fails, the child aborts instead of pretending the handoff succeeded.

`python/cli.py ship route-exit` consumes the `.rc` and `.json` sidecars after bgjob `DONE`. It does not consume launcher stdout. `persist_handoff` records the real driver rc in `.step-8-ship-handoff.rc`; the child exits 0 after successful handoff persistence so generic bgjob success is not confused with the driver route. Step 8 is persist-and-resume by design and uses bgjob live-registry rejoin instead of a second driver start.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Self-rehydrates `BRANCH_NAME`, `ISSUE_NUMBER`, `RUN_ID`, `REPO`, `MERGE`, `DRAFT`, `FORKED_TARGET`, `REPO_UNAVAILABLE`, `MANIFEST_PATH`, `TOOL_LABEL`, `NO_ADMIN_FALLBACK`, and `NO_LOGS_COMMIT` from `ship-pr-state.sh` before invoking the active driver.
- `EXPECTED_TMPDIR_BASENAME_PREFIX` comes from `python/cli.py implement clone-tag`; the ship wrapper and initial state seeder must share the same prefix.
- Guard rc 4 and `ship pr` JSON are capture-backed so `ship route-exit` can classify `NEXT_ACTION=stall` or another post-driver token.
- Foreground launch refuses a second start when a live identity-valid `implement-step8-ship` registry row exists and rejoins with `bgjob wait`.
- Fresh launch clears stale handoff sidecars itself; prompt-side stale-clear fences are retired.
- Setup failures without schema JSON are intentionally rc-only. The SKILL halts with Tool Failures before `route-exit` when the `.json` sidecar is absent.
- The Python version guard lives in `step-8-python-guard.sh`.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `step-8-seed-initial.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and `skills/implement/scripts/test-step-8-ship.sh` when this contract or argv changes.

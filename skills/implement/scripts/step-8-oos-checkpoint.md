# step-8-oos-checkpoint.sh

Thin Step 8+ OOS checkpoint relay. Runtime authority lives in `python/cli.py implement step-8-oos-checkpoint`.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` step so the prompt-side Bash fence remains a plugin-root source guard plus one script call.

## KV grammar

The wrapper forwards Python stdout unchanged and exits with the Python process rc only. The disposition-checkpoint rc is diagnostic in `OOS_CHECKPOINT_RC`; it is not the wrapper exit code.

Python emits these keys when routing succeeds:

- `OOS_CHECKPOINT_RC=0` and `NEXT_ACTION=reship` only when disposition rc 0 and all bookkeeping succeeds.
- `OOS_CHECKPOINT_RC=<n>` and `NEXT_ACTION=stall` when disposition is non-zero.
- `OOS_CHECKPOINT_RC=<nonzero>` and `NEXT_ACTION=stall` when disposition rc 0 but run-statistics, manifest stamp, or `OOS_PENDING=false` patching fails. It never pairs `OOS_CHECKPOINT_RC=0` with `NEXT_ACTION=stall`.

## Python-owned work

The Python verb runs `oos disposition-checkpoint` without forwarding child stdout, preserves child-written `oos-disposition-checkpoint.stderr.log` when captured stderr is empty, appends Tool Failures rows when needed, writes `run-statistics.md`, stamps `steps_ran.step9a1=true` on full success, best-effort stamps `step9a1=false` on bookkeeping failure, and clears `OOS_PENDING=false` via `ship._patch_ship_state_keys`.

OOS-checkpoint `NEXT_ACTION=stall` is not the post-driver Step 16 stall path. It halts Step 8+ until the checkpoint gap or bookkeeping failure is resolved.

`("implement", "step-8-oos-checkpoint")` is enrolled in `_MACHINE_STDOUT_KEYS` so inherited quiet mode cannot suppress `NEXT_ACTION`.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.

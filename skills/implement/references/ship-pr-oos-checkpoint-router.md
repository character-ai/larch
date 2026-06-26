# Ship PR OOS checkpoint router

**Consumer**: /implement Step 8+ after NEXT_ACTION=oos-pipeline and after the OOS pipeline body runs.
**Contract**: Owns the Step 8+ OOS checkpoint wrapper routing semantics and success bookkeeping contract.
**When to load**: **MANDATORY — READ ENTIRE FILE** only on the NEXT_ACTION=oos-pipeline branch before invoking step-8-oos-checkpoint.sh.

`python/cli.py implement step-8-oos-checkpoint` runs `oos disposition-checkpoint`, owns success bookkeeping, and emits exactly one `NEXT_ACTION=` when routing succeeds. Its process rc is 0 whenever `NEXT_ACTION` is emitted. It returns non-zero only when no `NEXT_ACTION` is emitted. It never emits `OOS_CHECKPOINT_RC=0` with `NEXT_ACTION=stall`.

On disposition rc 0 and successful bookkeeping, it writes run-scoped `run-statistics.md`, stamps `steps_ran.step9a1=true`, clears `OOS_PENDING=false` through `ship._patch_ship_state_keys`, emits `OOS_CHECKPOINT_RC=0`, and emits `NEXT_ACTION=reship`. Filed count comes from `larch-logs/implement/<RUN_ID>/oos-issues.ndjson` URL evidence when present, with fallback counts only when ndjson is absent.

On disposition rc 0 with stats, manifest-stamp, or state-patch failure, it best-effort stamps `steps_ran.step9a1=false`, leaves `OOS_PENDING` unchanged, emits non-zero `OOS_CHECKPOINT_RC`, and emits `NEXT_ACTION=stall`. On disposition rc 1, rc 2, 126, 127, or other non-zero rc, it emits `NEXT_ACTION=stall`, writes no stats, and clears no state.

The checkpoint wrapper preserves non-empty child-written `oos-disposition-checkpoint.stderr.log` when captured stderr is empty. Child stdout is not forwarded on success.

OOS-checkpoint `stall` is distinct from post-driver `stall`: halt Step 8+ until the gap or bookkeeping failure is resolved. Do not continue to Step 16.

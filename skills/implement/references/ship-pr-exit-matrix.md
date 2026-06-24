# Ship PR NEXT_ACTION routing

**Consumer**: `/implement` Step 8+ orchestrator.
**Contract**: Python-owned post-driver and OOS-checkpoint routing that emits one `NEXT_ACTION=` token.
**When to load**: Reference for Step 8+ `NEXT_ACTION` branches. It is no longer read on every non-zero driver exit.

## Durable handoff sidecars

`step-8-ship.sh` truncates `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture` at wrapper entry. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc` on every exit. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` only when the current capture contains guard or `ship pr` schema JSON. Rc-only setup failures unlink stale `.json`; the SKILL halts Tool Failures before `ship route-exit` and never invents driver JSON.

Capture extraction runs only after the guard or driver pipeline has closed, so the final JSON line has drained to disk before sidecar extraction.

## `ship route-exit` contract

`python/cli.py ship route-exit` reads the `.rc` and `.json` sidecars, validates required fields, writes `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env`, and emits exactly one `NEXT_ACTION=<token>` on stdout. Its process rc is 0 whenever `NEXT_ACTION` is emitted. It returns non-zero only when no `NEXT_ACTION` is safe to emit, such as malformed JSON, missing sidecar, missing required field, or handoff write failure.

Required JSON fields:

| Driver rc | Required fields | Routing |
| --- | --- | --- |
| 0 | `outcome` | `OK` maps to `complete`; any other outcome maps to `reship`. |
| 1 | `outcome=INTERNAL_ERROR` | `tool-failure`. |
| 3 | `outcome`, non-empty `needs_user_reason` | Reason table below. |
| 4 | `outcome` | `stall`. |
| 6 | `outcome` | retries 1-3 `reship`; retry 4 `stall`. |

Exit 3 reason routing:

- `oos-filing` maps to `oos-pipeline`.
- `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, and exact `local-unfixable` map to `ci-fix`.
- `ci-fix-exhausted`, `fix-attempts-exhausted`, `unsupported-rebase-continuation`, `checkout-mismatch`, and unknown operator-only reasons map to `operator-bail`.
- `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true` in scoped state makes the prose skip autonomous `ci-fix` and use operator-bail.

The handoff env uses safe single-line values: `FAILED_RUN_ID`, `NEEDS_USER_REASON`, `DETAIL`, optional `DETAIL_FILE`, and ledger keys. Boolean ledger values are lowercase `true` or `false`. When `ledger_ready=true`, prose records escalation before any `ci-fix` or `operator-bail` edits.

## Transient retry authority

`ship route-exit` owns post-driver exit-6 retry counting. It treats absent `ship-pr-net-retries-python.count` as 0, increments the count, persists the post-increment value before sleeping or emitting, and sleeps 30 seconds for retries 1-3. The sidecar records `RESHIP_DELAY_SECONDS=30` for audit only; the orchestrator does not sleep again. Retry 4 best-effort seeds `stall-recovery seed-terminal-state --stall-step transient-retry-cap --phase ci-initial` and emits `NEXT_ACTION=stall`.

`python/ship.py` keeps standalone direct or cron behavior: the in-driver fourth `TRANSIENT` still converts to `STALLED` when `--expected-session-id` is empty. Orchestrated wrapper calls pass a non-empty expected session id, so the fourth transient reaches `ship route-exit` as exit 6.

## Branch semantics

- **`complete`**: continue to Step 16.
- **`reship`**: re-invoke `step-8-ship.sh`. Preserve `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` while `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push` until conflict-resolution Phase 4 completes.
- **`oos-pipeline`**: run the `/issue` pipeline, then the OOS checkpoint router.
- **`ci-fix`**: run autonomous repair unless fork or repo-unavailable state forces operator-bail. It includes exact `local-unfixable`.
- **`operator-bail`**: use `AskUserQuestion` and Step 12d. It includes exhausted paths and fork or repo-unavailable skips.
- **Post-driver `stall`**: default route is Step 16, then Step 18. `ship_pr_pre_push` conflict-resolution runs first when its state handoff is active.
- **`tool-failure`**: hard Tool Failures stop. Do not rename as stalled and do not use Step 18 recovery.

Pre-driver `NEXT_ACTION=stall` remains separate: it skips ship and goes directly to Step 18.

## OOS checkpoint router

`python/cli.py implement step-8-oos-checkpoint` runs `oos disposition-checkpoint`, owns success bookkeeping, and emits exactly one `NEXT_ACTION=` when routing succeeds. Its process rc is 0 whenever `NEXT_ACTION` is emitted. It returns non-zero only when no `NEXT_ACTION` is emitted. It never emits `OOS_CHECKPOINT_RC=0` with `NEXT_ACTION=stall`.

On disposition rc 0 and successful bookkeeping, it writes run-scoped `run-statistics.md`, stamps `steps_ran.step9a1=true`, clears `OOS_PENDING=false` through `ship._patch_ship_state_keys`, emits `OOS_CHECKPOINT_RC=0`, and emits `NEXT_ACTION=reship`. Filed count comes from `larch-logs/implement/<RUN_ID>/oos-issues.ndjson` URL evidence when present, with fallback counts only when ndjson is absent.

On disposition rc 0 with stats, manifest-stamp, or state-patch failure, it best-effort stamps `steps_ran.step9a1=false`, leaves `OOS_PENDING` unchanged, emits non-zero `OOS_CHECKPOINT_RC`, and emits `NEXT_ACTION=stall`. On disposition rc 1, rc 2, 126, 127, or other non-zero rc, it emits `NEXT_ACTION=stall`, writes no stats, and clears no state.

The checkpoint wrapper preserves non-empty child-written `oos-disposition-checkpoint.stderr.log` when captured stderr is empty. Child stdout is not forwarded on success.

OOS-checkpoint `stall` is distinct from post-driver `stall`: halt Step 8+ until the gap or bookkeeping failure is resolved. Do not continue to Step 16.

## autonomous main-agent CI-fix sub-procedure

This reference retains the Python driver non-zero routing contract for exit-3 CI handoffs. The `ci-fix` action covers `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, and exact `local-unfixable`. `ci-fix-exhausted` remains operator-bail.

  1. Read `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` and read `REPO` from scoped `ship-pr-state.sh`.
  2. If `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true`, skip autonomous edits and route to operator-bail.
  3. Use sentinel `$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.attempted` and counter `$IMPLEMENT_TMPDIR/main-agent-ci-fix.count`. Attempts 1-3 may run; the next arrival falls through.
  4. Write the sentinel and increment the counter before repo edits. On write failure, append Tool Failures and fall through.
  5. Capture fresh CI logs with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" gh run-logs --run-id "$FAILED_RUN_ID" --repo "$REPO" | python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" redact secrets > "$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.gh-run-logs.redacted.txt"`.
  6. Make the minimal repo edit from the redacted CI log and optional detail file.
  7. Run relevant checks with `python/cli.py checks run-relevant --site step8-main-agent-fix --tmpdir "$IMPLEMENT_TMPDIR"`.
  8. Stage edited files explicitly with `git add -- <paths>`.
  9. Commit via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit -m "Fix CI failure (main-agent)"`.
  10. Refresh run logs with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log refresh --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"`.
  11. Rerun architectural-guidelines Phase A before the next ship re-invoke when staged or durable guideline artifacts exist.
  12. Push with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch`, then re-invoke `step-8-ship.sh`.

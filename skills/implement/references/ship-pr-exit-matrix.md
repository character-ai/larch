# Ship PR NEXT_ACTION routing

**Consumer**: `/implement` Step 8+ orchestrator.
**Contract**: Python-owned post-driver and OOS-checkpoint routing that emits one `NEXT_ACTION=` token.
**When to load**: **MANDATORY — READ ENTIRE FILE** at Step 8+ entry, before any Step 8+ orchestrator fence, including `ship route-exit` and `ship pre-driver`.

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
- **`reship`**: re-invoke `step-8-ship.sh`. Preserve `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` while `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push` until conflict-resolution Phase 4 completes. Do not sleep on `RESHIP_DELAY_SECONDS`; the router already applied exit-6 delay.
- **`oos-pipeline`**: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/execution-issues-tracking.md` completely, run the `/issue` pipeline, then run the OOS checkpoint router.
- **`ci-fix`**: read `.ship-route-exit-handoff.env` via `larch.io.read_kvs`. If `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true` in scoped `ship-pr-state.sh`, skip autonomous edits and route to operator-bail. Otherwise, when `ledger_ready=true`, call `stall-recovery record-escalation` before edits. Run autonomous repair using `FAILED_RUN_ID`, `DETAIL_FILE` when present, and ledger fields from the sidecar. This includes exact `local-unfixable`.
- **`operator-bail`**: read `NEEDS_USER_REASON`, `DETAIL`, and `DETAIL_FILE` from `.ship-route-exit-handoff.env`. When `ledger_ready=true`, record escalation first. Use `AskUserQuestion` and Step 12d. It includes exhausted paths and fork or repo-unavailable skips.
- **Post-driver `stall`**: if `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, run conflict-resolution Phase 1-4 first. Otherwise the default route is Step 16, then Step 18.
- **`tool-failure`**: hard Tool Failures stop. Do not rename as stalled and do not use Step 18 recovery.

Pre-driver `NEXT_ACTION=stall` remains separate: it skips ship and goes directly to Step 18. OOS-checkpoint `NEXT_ACTION=stall` is also separate: halt Step 8+ until the gap or bookkeeping failure is resolved.

## Initial state seeder contract

`python/cli.py ship seed-initial-state` owns the canonical initial `ship-pr-state.sh` key set, including `OOS_PENDING=false`; `python/test_ship.py` pins the exact ordered keys. `step-8-seed-initial.sh` is the only shell argv-assembly wrapper for that seeder. Dynamic inputs come from durable `$IMPLEMENT_TMPDIR/bootstrap-routing.env` and `$IMPLEMENT_TMPDIR/ship-seed-input.env`, plus session readers documented in `step-8-seed-initial.md`.

`MANIFEST_PATH` MUST be empty unless `/implement` Step 2 returned `STATUS=complete` with a readable JSON manifest. The `/design` Step 5 manifest (`design-export/manifest.env`, a shell KV file) is NEVER a valid value for `MANIFEST_PATH`. The bash ship path is retired, so `LARCH_SHIP_PR_IMPL=bash` prose is moot.

## Long-running driver re-entry

Post-driver Step 8+ continuations happen when `PR_NUMBER` is non-empty, `PHASE` is beyond the initial `checks` cold-start, OOS checkpoint re-entry happens after the driver started, a transient retry occurs, conflict resolution resumes, or Exit 3 re-invokes after a PR exists. In these cases, invoke only `step-8-ship.sh`; do not rerun the pre-driver verb. The wrapper still runs its internal guard and advisory phantom probe before the driver.

For unexpected turn-end recovery, every Step 8+ re-entry goes through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` only for the active driver call. The Python driver reads continuation from persisted `ship-pr-state.sh` and the phase14 flag after conflict-resolution Phase 4. When the pre-driver predicate still matches, re-evaluate it first and run `python/cli.py ship pre-driver` before `step-8-ship.sh`. Do not call `python/cli.py ship pr` directly from a separate foreground shell. Do not pass `--resume-phase`; resume is state-file driven.

## OOS cap contract

The OOS cap contract lives in `${CLAUDE_PLUGIN_ROOT}/python/cli.py oos issue-cap` and `${CLAUDE_PLUGIN_ROOT}/python/file_oos.py`; apply it before any `/issue --input-file` batch emission so per-run issue count limits and excerpt behavior stay unchanged. Harness coverage lives in `${CLAUDE_PLUGIN_ROOT}/python/test_file_oos.py` via `make test-oos-issue-cap`.

The Step 8+ checkpoint contract is `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-oos-checkpoint.md`. Offline harness `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/test-oos-disposition-gate.sh` covers the disposition gate, and `skills/implement/scripts/test-step-8-oos-checkpoint.sh` covers the wrapper relay. Sibling docs: `skills/implement/scripts/oos-disposition-checkpoint.md`, `skills/implement/scripts/oos-disposition-gate.md`, `skills/implement/scripts/test-oos-disposition-gate.md`, and `skills/implement/scripts/test-step-8-oos-checkpoint.md`.

## Bail-time `steps_ran` invariant

If the run ends before Step 9a.1 or before `oos file` succeeds, the committed manifest MUST NOT leave `steps_ran` as an ambiguous empty object for downstream audit tooling. Step 9a.1 completion requires post-checkpoint `run-statistics.md`; explicit `manifest.json` `steps_ran.step9a1=true` is valid only together with that file. `step9a1=true` without `run-statistics.md` is a stale or corrupt marker and must fail audit/verify scans. `oos-issues.ndjson` without `run-statistics.md` is provisional disposition evidence and must not suppress `steps_ran.step9a1=false`.

`python/cli.py final-report write` records explicit `steps_ran.step9a1=false` (and `step8` / `step7a` when their on-disk artifacts are absent) for terminal non-merge outcomes (`bailed`, `stalled`, `design-only`, fork dry-run, PR-created-without-merge, etc.); a non-zero exit from that `run-log manifest` call fails finalization. `python/cli.py run-log verify-completeness` treats missing/null `steps_ran` like `jq '.steps_ran // {}'` for the empty-object bail path, matching `python/cli.py audit-runs scan-run`.

## Execution-issues checkpoint and metadata refresh

`CI_PASSED=true` does not append execution-issues after green CI. The primary flush happens in Step 7a (pre-ship) so the NDJSON record is part of the same PR tree that CI validates; appending after CI would either validate a different tree or create a post-CI audit-log delta. Later steps may still add new entries to `$IMPLEMENT_TMPDIR/execution-issues.md`; Step 7a writes a checkpoint marker even when the pre-ship flush is a skip, and the shared external-implementer / pre-push paths (`python/cli.py run-log flush`, `python/cli.py run-log refresh`) flush any later non-empty tail before the next log commit once that checkpoint exists. Step 18's teardown safety net remains the fallback if the normal path is missed.

Invoke `${CLAUDE_PLUGIN_ROOT}/python/cli.py execution-issues flush` per its contract (see `skills/implement/scripts/flush-execution-issues.md`; regression harness: `skills/implement/scripts/test-flush-execution-issues.sh` with sibling `skills/implement/scripts/test-flush-execution-issues.md`). Refresh the tracking metadata projection after execution-issues changes when a tracking issue exists. If `ISSUE_NUMBER` is empty or `0`, skip the refresh helper entirely; do not call GitHub for issue `#0`.

## Active driver ownership notes

The active Step 8+ driver writes `finalize-state.sh` for terminal outcomes, records `CI_PASSED=true` internally when Step 10 sees `ACTION=merge` and advances from `ci-initial` to `ci-merge` in the same Python invocation, and treats Step 12 `ACTION=merge` as permission to call `python/cli.py merge pr`. CI-fix rebase + force-push lives inside the active Step 8+ driver (`run_rebase_rebump`).

On Python Exit 4 with `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, the orchestrator must load and run `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/conflict-resolution.md` with `caller_kind=ship_pr_pre_push` before re-invoking `step-8-ship.sh`; that file remains live for pre-push conflict resolution only. If CI failure metadata lacks a failed run id, use `${CLAUDE_PLUGIN_ROOT}/python/cli.py pr checks` as the fallback diagnostic path before deciding whether to stall. Within `PHASE=ci-merge`, after merge succeeds the Python ship driver delegates local cleanup to `python/cli.py implement-finalize postmerge`; after that returns, continue to Step 15.

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

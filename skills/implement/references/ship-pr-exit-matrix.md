# Ship PR NEXT_ACTION routing

**Consumer**: `/implement` Step 8+ orchestrator.
**Contract**: Python-owned post-driver and OOS-checkpoint routing that emits one `NEXT_ACTION=` token.
**When to load**: **MANDATORY — READ ENTIRE FILE** at Step 8+ entry, before any Step 8+ orchestrator fence, including `ship route-exit` and `ship pre-driver`.

## Durable handoff sidecars

Before every Step 8+ background relaunch, the orchestrator runs the foreground stale-handoff clear from SKILL.md Step 8+; wrapper entry also removes stale rc/json sidecars as defense in depth. `step-8-ship.sh` truncates `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture` at wrapper entry. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc` on every exit. It writes `$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json` only when the current capture contains guard or `ship pr` schema JSON. Rc-only setup failures unlink stale `.json`; the SKILL halts Tool Failures before `ship route-exit` and never invents driver JSON.

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

## Branch semantics

- **`complete`**: continue to Step 16.
- **`reship`**: run the foreground stale-handoff clear from SKILL.md Step 8+ in the same turn, then re-invoke `step-8-ship.sh` with the single-line launcher fence and `run_in_background: true`. Preserve `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` while `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push` until conflict-resolution Phase 4 completes. Do not sleep on `RESHIP_DELAY_SECONDS`; the router already applied exit-6 delay.
- **`oos-pipeline`**: security sidecar disposition only. Read `$IMPLEMENT_TMPDIR/security-oos-observations.md`, follow `SECURITY.md` `## Security Findings in OOS Workflows` private disclosure with no public `/issue`, and clear the sidecar only after private disposition completes. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-oos-checkpoint-router.md` completely before invoking `step-8-oos-checkpoint.sh`.
- **`ci-fix`**: If `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true` in scoped `ship-pr-state.sh`, skip autonomous edits and route to operator-bail. Otherwise, **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/ship-pr-ci-fix.md` completely when not skipped to operator-bail and before autonomous repair / `step-8-ship.sh` re-entry. Any autonomous repair path that ends in ship re-entry must run the foreground stale-handoff clear immediately before the background launch. This includes exact `local-unfixable` routing via the Exit 3 table.
- **`operator-bail`**: read `NEEDS_USER_REASON`, `DETAIL`, and `DETAIL_FILE` from `.ship-route-exit-handoff.env`. When `ledger_ready=true`, record escalation first. Use `AskUserQuestion` and Step 12d. It includes exhausted paths and fork or repo-unavailable skips. If CI failure metadata lacks `failed_run_id`, use `${CLAUDE_PLUGIN_ROOT}/python/cli.py pr checks` as the fallback diagnostic path before deciding whether to stall.
- **Post-driver `stall`**: if `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, run conflict-resolution Phase 1-4 first. Otherwise the default route is Step 16, then Step 18.
- **`tool-failure`**: hard Tool Failures stop. Do not rename as stalled and do not use Step 18 recovery.

Pre-driver `NEXT_ACTION=stall` remains separate: it skips ship and goes directly to Step 18. OOS-checkpoint `NEXT_ACTION=stall` is also separate: halt Step 8+ until the gap or bookkeeping failure is resolved.

## Initial state seeder contract

`python/cli.py ship seed-initial-state` owns the canonical initial `ship-pr-state.sh` key set, including `OOS_PENDING=false`; `python/test_ship.py` pins the exact ordered keys. `step-8-seed-initial.sh` is the only shell argv-assembly wrapper for that seeder. Dynamic inputs come from durable `$IMPLEMENT_TMPDIR/bootstrap-routing.env` and `$IMPLEMENT_TMPDIR/ship-seed-input.env`, plus session readers documented in `step-8-seed-initial.md`.

`MANIFEST_PATH` MUST be empty unless `/implement` Step 2 returned `STATUS=complete` with a readable JSON manifest. The `/design` Step 5 manifest (`design-export/manifest.env`, a shell KV file) is NEVER a valid value for `MANIFEST_PATH`. The bash ship path is retired, so `LARCH_SHIP_PR_IMPL=bash` prose is moot.

## Long-running driver re-entry

Post-driver Step 8+ continuations happen when `PR_NUMBER` is non-empty, `PHASE` is beyond the initial `checks` cold-start, OOS checkpoint re-entry happens after the driver started, a transient retry occurs, conflict resolution resumes, or Exit 3 re-invokes after a PR exists. In these cases, run the foreground stale-handoff clear in the parent shell before `run_in_background`, then invoke only `step-8-ship.sh`; do not rerun the pre-driver verb. The wrapper still runs its internal guard and advisory phantom probe before the driver.

For unexpected turn-end recovery, every Step 8+ re-entry runs the foreground stale-handoff clear, then goes through `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` only for the active driver call. The Python driver reads continuation from persisted `ship-pr-state.sh` and the phase14 flag after conflict-resolution Phase 4. When the pre-driver predicate still matches, re-evaluate it first and run `python/cli.py ship pre-driver` before `step-8-ship.sh`. Do not call `python/cli.py ship pr` directly from a separate foreground shell. Do not pass `--resume-phase`; resume is state-file driven.

## Terminal manifest contract

Terminal runs must leave explicit `steps_ran` values through `python/cli.py final-report write`. The full invariant lives in `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/write-final-report.md`.

## Execution-issues checkpoint and metadata refresh

`CI_PASSED=true` does not append execution-issues after green CI. The primary flush happens in Step 7a (pre-ship) so the NDJSON record is part of the same PR tree that CI validates; appending after CI would either validate a different tree or create a post-CI audit-log delta. Later steps may still add new entries to `$IMPLEMENT_TMPDIR/execution-issues.md`; Step 7a writes a checkpoint marker even when the pre-ship flush is a skip, and the shared external-implementer / pre-push paths (`python/cli.py run-log flush`, `python/cli.py run-log refresh`) flush any later non-empty tail before the next log commit once that checkpoint exists. Step 18's teardown safety net remains the fallback if the normal path is missed.

Invoke `${CLAUDE_PLUGIN_ROOT}/python/cli.py execution-issues flush` per its contract (see `skills/implement/scripts/flush-execution-issues.md`; regression harness: `skills/implement/scripts/test-flush-execution-issues.sh` with sibling `skills/implement/scripts/test-flush-execution-issues.md`). Refresh the tracking metadata projection after execution-issues changes when a tracking issue exists. If `ISSUE_NUMBER` is empty or `0`, skip the refresh helper entirely; do not call GitHub for issue `#0`.

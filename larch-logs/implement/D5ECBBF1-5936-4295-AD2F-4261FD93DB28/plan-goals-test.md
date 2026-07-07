## Goal
Implement issue #6530: [IMPLEMENTING] bgjob migration foundation: wait contract, real-process harness, writer-parity lint rescope (#6524 chunk 1/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 1/11.

Scope: bgjob migration foundation — flesh out the normative `skills/shared/bgjob-wait.md` wait contract, add the real-process `scripts/test-bgjob.sh` harness with its Makefile shard, rescope the bg-wait writer-parity lint so later chunks can remove `.bg-wait-active` writers, and add hook-guard compatibility assertions.

Dependencies: none — this chunk is independent and must merge before the call-site migration chunks (they rely on the rescoped writer-parity lint and the extended wait contract).

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them.

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel and Step 8 handoff sidecar.
3. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate each per-step merge-result env before `bgjob start`** so stale KVs from a prior attempt cannot satisfy required-key gates after a fresh child exits `BGJOB_RC=0` without writing new values. Prefer truncating the merge input file immediately before start; optionally stamp a per-run generation token in the merge env.
5. Treat `$TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
6. Gate normal continuation on both `BGJOB_RC=0` (with the Step 8 carve-out) and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
7. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, any other non-zero rc where the step has no valid completion sidecar, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
8. **Step 8 carve-out:** do not apply the generic `BGJOB_RC=0` gate to `ship route-exit`. The bgjob child must always write current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` (when schema JSON exists) before exit.
9. **Parallel lanes:** assign a unique `--step` slug per concurrent external lane so registry rows and result envs cannot clobber each other.
10. **Live-registry rejoin:** before every `bgjob start` for long-lived loops (`design-step3-review`, `implement-step5-review`, `implement-step8-ship`), if an identity-valid registry row exists for that step, refuse a second start and require chunked `bgjob wait` instead; clear only stale or dead rows before a fresh start.
11. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/shared/bgjob-wait.md
- Add examples for wrapper launch, repeated `wait`, `DONE` parsing, and `--merge-result-env`.
- Pin the "no prose, no tools, no sleep between WAITs" rule.
- Name result envs as the completion source of truth.
- Document merge-input freshness: truncate or recreate the merge env before each `bgjob start`.
- Document the Step 8 handoff-sidecar carve-out: route-exit follows sidecar rc/json, not `BGJOB_RC=0` alone.
- Document per-lane unique `--step` slugs for parallel external lanes.

### NEW: scripts/test-bgjob.sh
- Add real-process coverage for:
  - one-line start stdout
  - owner death writes `BGJOB_RC=orphaned`
  - budget expiry writes `BGJOB_RC=timeout`
  - external daemon kill yields `DEAD`
  - identity-checked reap does not signal a recycled PID owner
  - bad step names are rejected
- Skip loudly when sandbox limitations block `ps` identity probes.

### UPDATED: `Makefile`
- Repoint or split `test-bgjob` so real-process `scripts/test-bgjob.sh` is in a `test-harnesses-N` shard.
- Keep Python bgjob unit tests in `py-test`, not duplicated as the only bgjob harness.
- Run `make test-harness-shards-coverage` after shard edits.

### UPDATED: python/larch/lint/lint_bg_wait_writer_parity.py
- Rescope writer parity so it no longer requires `.bg-wait-active` writers.
- Keep compatibility lint passing until #6516 removes legacy hooks.
- Chunk note: the lint must stay green both before and after sibling chunks remove `.bg-wait-active` from the current `WRITERS` files (`design-step3-review.sh`, `design-step3b-tail.sh`, `run-step-checks.sh`, `step-5-review.sh`, `step-6-entry.sh`, `step-8-ship.sh`, `design_core.py`, `bg_wait.py`) — order-independent tolerance, not deletion of the lint.

### UPDATED: python/tests/lint/test_lint_bg_wait_writer_parity.py
- Update expectations for the narrowed compatibility lint.

### UPDATED: scripts/test-hook-bg-poll-guard.sh
- Keep legacy marker coverage.
- Add assertions that bgjob wait loops do not trigger legacy polling denies.

### UPDATED: scripts/test-hook-no-progress-guard.sh
- Keep legacy no-progress coverage.
- Assert bgjob `WAIT` loops do not count as stale background-wait turns.

### MAY_UPDATE: python/tests/bgjob/test_daemon.py
- Add any missing daemon unit coverage found while wiring real-process shell tests.

### MAY_UPDATE: python/tests/bgjob/test_wait.py
- Add parsing and `DEAD` edge coverage if the migration needs a wait helper adjustment.

### MAY_UPDATE: python/tests/bgjob/test_bgjob_cli.py
- Add CLI flag coverage for any new helper option needed by migrated wrappers.

### MAY_UPDATE: scripts/hook-deny-run-in-background.sh
- Update only if registry row shape changes.
- Keep it denying `run_in_background` while a larch bgjob is active in the clone.

### MAY_UPDATE: scripts/test-hook-deny-run-in-background.sh
- Update fixture rows only if registry shape changes.

## Edge cases

- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- `bgjob wait` shell exit 0 on `WAIT` or `DEAD` must not advance a step; the contract doc must say so explicitly.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; the contract doc pins truncate-before-start.
- Retained legacy hooks must remain functional for #6516; hook-guard tests keep legacy coverage while adding bgjob-wait compatibility assertions.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing (pin the one-line start stdout in `scripts/test-bgjob.sh`).
- Writer-parity lint rescope deletes coverage instead of narrowing it, hiding a regression in a not-yet-migrated writer.
- `scripts/test-bgjob.sh` lands outside a `test-harnesses-N` shard and never runs in CI.
- Hook tests are over-pruned and accidentally delete #6516 compatibility coverage.

## Testing strategy

1. `bash scripts/test-bgjob.sh`
2. `python3 -m pytest python/tests/lint/test_lint_bg_wait_writer_parity.py python/tests/bgjob -q`
3. `bash scripts/test-hook-bg-poll-guard.sh`
4. `bash scripts/test-hook-no-progress-guard.sh`
5. `python3 python/cli.py lint bg-wait-writer-parity`
6. `make test-harness-shards-coverage`
7. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Keep Bash wrappers and harnesses thin and macOS Bash 3.2-compatible.
- Use config constants for bgjob status and rc keys.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.
- Do not migrate any skill prose or wrapper in this chunk; sibling chunks own the call sites.

## Acceptance

1. `scripts/test-bgjob.sh` passes in its `test-harnesses` shard against real processes: owner death yields `BGJOB_RC=orphaned` within grace, budget expiry yields `BGJOB_RC=timeout`, an externally killed daemon yields `DEAD` within one poll interval, and identity-checked reap leaves a recycled PID's new owner unharmed.
2. `skills/shared/bgjob-wait.md` documents wrapper launch, repeated `wait`, `DONE` parsing, `--merge-result-env`, merge-input truncation before start, the Step 8 handoff-sidecar carve-out, and per-lane unique `--step` slugs.
3. `python3 python/cli.py lint bg-wait-writer-parity` passes on the unmodified current tree and continues to pass when a `WRITERS` file no longer contains `.bg-wait-active` (pinned in `python/tests/lint/test_lint_bg_wait_writer_parity.py`).
4. `scripts/test-hook-bg-poll-guard.sh` and `scripts/test-hook-no-progress-guard.sh` pass with the new bgjob-wait compatibility assertions and unchanged legacy coverage.
5. `make py-lint`, `make py-test`, and affected `test-harnesses` shards pass, including the pytest unique-basename constraint for new test files.

diff_added: 340
diff_deleted: 60
mechanical_churn: true
diff_lines: 400

## Test plan
(no test plan section in plan-file)

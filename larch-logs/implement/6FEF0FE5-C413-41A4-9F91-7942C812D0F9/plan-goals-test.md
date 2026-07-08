## Goal
Implement issue #6537: [IMPLEMENTING] Migrate /implement Step 8 ship pipeline to bgjob with handoff-sidecar carve-out (#6524 chunk 8/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 8/11.

Scope: migrate the /implement Step 8 ship pipeline — wrapper, skill fences, exit-matrix / CI-fix / conflict-resolution relaunch prose, and the Step 8 dispatch routing — to bgjob with the handoff-sidecar carve-out (`ship route-exit` follows `.step-8-ship-handoff.rc`/`.json`, not `BGJOB_RC=0`).

Dependencies: blocked by #6536 (chunk 7/11: /implement Step 5 loop). Merge it first (chunks 1, 2, and 6 are transitive prerequisites through it).

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (`stall-recovery.md`, `dispatch_step18.py`, and `bg_wait.py` migrate in the stall/state chunk).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel and Step 8 handoff sidecar.
3. Make the migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate the per-step merge-result env before `bgjob start`.**
5. Treat `$IMPLEMENT_TMPDIR/bgjob/implement-step8-ship.result.env` as the completion source of truth after `bgjob wait` returns `DONE`, subject to the carve-out below.
6. **Step 8 carve-out:** do not apply the generic `BGJOB_RC=0` gate to `ship route-exit`. The bgjob child must always write current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` (when schema JSON exists) before exit. Prefer making the child exit 0 after `persist_handoff` and keeping the real driver rc only in the sidecar. If the child preserves a non-zero process rc, allow `DONE` continuation to `ship route-exit` when both handoff sidecars are present and current, while still blocking `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, `DEAD`, and missing or stale handoff sidecars.
7. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing/stale handoff sidecars as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
8. **Live-registry rejoin:** before every `bgjob start` for `implement-step8-ship`, if an identity-valid registry row exists for that step, refuse a second start and require chunked `bgjob wait` instead; clear only stale or dead rows before a fresh start.
9. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md
- Chunk-scoped: Step 8 fences (Steps 3/5/6/7a landed in earlier chunks). After this chunk, `skills/implement/SKILL.md` contains no `run_in_background` requests; remove its allowlist row (below).
- Replace Step 8 immediate-background fences with bgjob start and wait loops per `bgjob-wait.md`.
- **Step 8:** after final `DONE`, proceed to `ship route-exit` when current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` (when required) exist; do not require `BGJOB_RC=0`. Still block `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, `DEAD`, and missing handoff sidecars.
- On live identity-valid `implement-step8-ship` registry row, rejoin via `bgjob wait`; refuse a second `bgjob start`.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md
- Replace every Step 8 relaunch leg with bgjob start plus wait.
- Keep route-exit inputs unchanged after `DONE` with valid current handoff sidecars.
- Document Step 8 bgjob carve-out: numeric driver rc in `.step-8-ship-handoff.rc` is authoritative for `ship route-exit`; do not treat non-zero `BGJOB_RC` as generic bgjob failure when sidecars are present and current.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md
- Convert CI-fix relaunch prose to bgjob.
- Preserve handoff-sidecar gate before `ship route-exit`.

### UPDATED: skills/implement/references/conflict-resolution.md
- Convert conflict-resolution Phase 4 ship relaunch to bgjob.
- Preserve conflict-routing semantics and Step 8 rejoin rule.

### UPDATED: skills/implement/scripts/step-8-ship.sh
- Run the ship driver as a bgjob daemon.
- Preserve `.step-8-ship-handoff.rc`, `.step-8-ship-handoff.json`, and `persist_handoff` ordering.
- Prefer child exit 0 after `persist_handoff`; keep real driver rc in the sidecar.
- Merge any route-exit KVs into the bgjob result env without changing `ship route-exit` consumption.
- On re-entry when a live identity-valid `implement-step8-ship` registry row exists, refuse a second `bgjob start` and require chunked `bgjob wait`.

### UPDATED: skills/implement/scripts/step-8-ship.md
- Replace `.bg-wait-active` and background relaunch guidance with bgjob contract.
- Keep handoff sidecar contract byte-compatible.
- Gate route-exit handoff on current handoff sidecars after final `DONE`; do not require `BGJOB_RC=0`.

### UPDATED: python/larch/implement/implement_dispatch.py
- Update branches that launch or parse Step 3, Step 5, Step 6, and Step 8 wrappers.
- Parse `BGJOB_STATUS` and bgjob result env KVs, including `BGJOB_RC`, before existing branch handling.
- Step 8: route to `ship route-exit` from handoff sidecars, not `BGJOB_RC=0` alone.
- Chunk note: the Step 3/5/6 wrapper migrations landed in earlier chunks; align any remaining aggregator branches here so all step launch/parse paths are bgjob-aware.

### UPDATED: python/tests/implement/test_implement_dispatch.py
- Chunk-scoped: Step 8 pins (Step 3 and Step 5 resume pins landed in earlier chunks).
- Pin Step 8 route-exit from handoff sidecars without `BGJOB_RC=0` requirement.

### UPDATED: skills/implement/scripts/test-step-8-ship.sh
- Assert bgjob launch contract and unchanged handoff rc/json ordering.
- Assert route-exit is reached with valid handoff sidecars even when `BGJOB_RC` is non-zero (pin rc `3` or `6` cases).
- Assert route-exit is not reached without current handoff sidecars or on `BGJOB_RC=timeout` / `BGJOB_RC=orphaned` / `DEAD`.
- Pin live-registry rejoin: second `bgjob start` refused when identity-valid `implement-step8-ship` row exists.

### UPDATED: scripts/test-implement-structure.sh
- Chunk-scoped: Step 8 rows (Step 3/6/7a and Step 5 rows landed in earlier chunks).
- Replace Step 8 task-notification assertions with bgjob assertions.
- Assert Step 8 route-exit follows handoff sidecars without requiring `BGJOB_RC=0`.

### UPDATED: scripts/test-implement-fence-shape.sh
- Update `EXPECTED_OLD` and `EXPECTED_NEW` for this chunk's changed `skills/implement/SKILL.md` fences.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/implement/SKILL.md`, `skills/implement/references/conflict-resolution.md`, `skills/implement/references/ship-pr-ci-fix.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and `skills/implement/scripts/step-8-ship.md` rows (their prose is migrated by this chunk).
- Keep the `skills/implement/references/stall-recovery.md`, research, and `skills/shared/orchestrator-never.md` rows; sibling chunks own them.

### MAY_UPDATE: scripts/test-implement-anti-polling-rule.sh
- Update only Step 8 rows this chunk's edits break; the harness's bgjob rewrite landed with the checks chunk.

## Edge cases

- Step 8 re-entry must rejoin a live `implement-step8-ship` registry row via `bgjob wait` and must not launch a second ship driver.
- Step 8 must write handoff rc/json before any route-exit handling sees the result.
- Step 8 `DONE` with numeric driver rc in `.step-8-ship-handoff.rc` (for example `3` or `6`) must still reach `ship route-exit` when sidecars are current; `BGJOB_RC=0` is not required for Step 8.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned`, `DEAD`, or missing/stale handoff sidecars must route to failure or stall — never to `ship route-exit`.
- Existing sentinels may exist from prior attempts. Result env, handoff sidecar freshness, and identity-checked registry state must decide current completion.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Step 8 route-exit is blocked by a blanket `BGJOB_RC=0` gate despite valid numeric handoff rc.
- A second live Step 8 ship daemon starts and races on the same handoff files.
- Step 8 handoff sidecar ordering changes and breaks `ship route-exit`.
- Wrapper stdout gains banners and breaks harness parsing.
- Allowlist rows removed while some migrated file still requests `run_in_background`, causing `lint bg-wait-coverage` failure.

## Testing strategy

1. `bash scripts/test-implement-structure.sh`
2. `bash scripts/test-implement-fence-shape.sh`
3. `bash skills/implement/scripts/test-step-8-ship.sh`
4. `python3 -m pytest python/tests/implement/test_implement_dispatch.py -q`
5. `python3 python/cli.py lint bg-wait-coverage`
6. `python3 python/cli.py lint bg-wait-writer-parity`
7. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs in wrappers immediately before every `bgjob start`.
- Step 8: prefer child exit 0 after `persist_handoff`; keep driver rc in `.step-8-ship-handoff.rc` for `ship route-exit`.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion (`bg_wait.py` is narrowed in the stall/state chunk).

## Acceptance

1. `git grep -l "run_in_background" skills/implement/` returns only `skills/implement/references/stall-recovery.md` (owned by the stall/state chunk); the five rows named above are removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
2. Migrated `step-8-ship.sh` harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line, harness-asserted.
3. `ship route-exit` is reached after final `DONE` with current `.step-8-ship-handoff.rc`/`.json` even when `BGJOB_RC` is non-zero (rc `3`/`6` pinned), and never on `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, `DEAD`, or missing sidecars (pinned in `test-step-8-ship.sh` and `test_implement_dispatch.py`).
4. Step 8 re-entry rejoins a live identity-valid `implement-step8-ship` registry row via `bgjob wait`; a second `bgjob start` is refused.
5. `.step-8-ship-handoff.rc` / `.step-8-ship-handoff.json` writing and `persist_handoff` ordering are byte-compatible; `ship route-exit` consumption is unchanged; legacy hooks stay functional and inert.
6. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 250
diff_deleted: 170
mechanical_churn: true
diff_lines: 420

## Test plan
(no test plan section in plan-file)

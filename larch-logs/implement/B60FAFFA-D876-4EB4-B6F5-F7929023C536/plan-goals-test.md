## Goal
Implement issue #6538: [IMPLEMENTING] Migrate stall recovery and state classifiers to bgjob registry liveness (#6524 chunk 9/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 9/11.

Scope: migrate stall recovery and state classification from `.bg-wait-active` marker inspection to identity-checked bgjob registry liveness — `stall-recovery.md` retry prose, `dispatch_step18.py` recovery relaunch, the `_tokens.py`/`_classify.py`/`_state_mgmt.py` classifiers — and narrow `python/larch/implement/bg_wait.py` to its remaining compatibility surface.

Dependencies: blocked by #6537 (chunk 8/11: /implement Step 8 ship). Merge it first (chunks 1, 2, 6, and 7 are transitive prerequisites through it). This chunk requires the migrated steps (`implement-step3-checks`, `implement-step5-self-review`, `implement-step8-ship`) to already run under bgjob so registry rows exist to classify.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them.

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Detect abandoned steps by identity-checked dead owner or daemon PGID from bgjob registry rows. Never use bare PID liveness or bare registry file presence.
3. Stale dead registry rows must be reaped or ignored, never treated as in-flight.
4. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch.
5. **Live-registry rejoin:** stall retry for `implement-step8-ship` must rejoin a live identity-valid registry row via chunked `bgjob wait`; refuse a second start; clear only stale or dead rows before a fresh start.
6. Keep stall state tokens unchanged.
7. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/implement/references/stall-recovery.md
- Convert `step8-shippr` retry instructions to bgjob.
- Keep stall state tokens unchanged.
- Pin live-registry rejoin for `implement-step8-ship`.

### UPDATED: python/larch/implement/dispatch_step18.py
- Convert recovery relaunch paths that still reference legacy marker machinery.
- Preserve Step 18 stall and final-report routing.
- Apply Step 8 live-registry rejoin before recovery relaunch.

### UPDATED: python/larch/implement/bg_wait.py
- Narrow to the compatibility surface needed by retained legacy hooks.
- Do not delete the module in this issue.

### UPDATED: python/larch/state/_tokens.py
- Replace `_abandoned_checks_marker_stall_step` marker logic with bgjob registry inspection.
- Detect abandoned rows by identity-checked dead owner or daemon PGID.
- Never use bare PID liveness or bare registry file presence.

### UPDATED: python/larch/state/_classify.py
- Route abandoned checks detection through the bgjob-aware helper.

### UPDATED: python/larch/state/_state_mgmt.py
- Rename or narrow `_clear_abandoned_checks_marker`.
- Clear stale bgjob registry rows for checks steps on recovery completion.

### UPDATED: python/tests/state/test_stall_recovery.py
- Replace abandoned marker tests with abandoned bgjob registry row tests.
- Cover dead owner, dead daemon, live registry without result env, stale dead registry not blocking, and cleared registry.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/implement/references/stall-recovery.md` row (its prose is migrated by this chunk).
- Keep the research rows and the `skills/shared/orchestrator-never.md` row; sibling chunks own them.

### MAY_UPDATE: scripts/test-implement-structure.sh
- Adjust stall-recovery pins only if this chunk's `stall-recovery.md` edits break existing needles; the Step 3/5/8 row rewrites landed with their chunks.

## Edge cases

- Stall classification must distinguish: dead owner, dead daemon, live registry row without result env (in flight), stale dead row (not blocking), and cleared registry.
- A live identity-valid registry row without a result env means in flight, not abandoned.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Stall retry must not start a second ship driver when an identity-valid `implement-step8-ship` row is live.
- Retained legacy hooks must remain functional for #6516; `bg_wait.py` keeps the compatibility surface they need.

## Failure modes

- Classifier treats dead registry presence as in-flight and blocks recovery forever.
- Classifier uses bare PID liveness and mis-signals a recycled PID's new owner.
- `bg_wait.py` narrowed past the surface retained legacy hooks still import, breaking hooks before #6516.
- Stall state tokens change and break downstream stall-report consumers.

## Testing strategy

1. `python3 -m pytest python/tests/state/test_stall_recovery.py -q`
2. `python3 python/cli.py lint bg-wait-coverage`
3. `python3 python/cli.py lint bg-wait-writer-parity`
4. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for registry liveness and result-env reads.
- Use config constants for bgjob status and rc keys.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks or defense docs; #6516 owns deletion.

## Acceptance

1. Stall recovery classifies abandoned `implement-step3-checks` and `implement-step5-self-review` legs from dead bgjob registry rows, not `.bg-wait-active` (pinned in `test_stall_recovery.py`).
2. Stale dead registry rows do not block recovery; live identity-valid rows are rejoined, and `step8-shippr` retry never starts a second ship driver.
3. The `stall-recovery.md` row is removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
4. `bg_wait.py` retains only the compatibility surface needed by retained legacy hooks and is not deleted; stall state tokens are unchanged.
5. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 160
diff_deleted: 120
mechanical_churn: true
diff_lines: 280

## Test plan
(no test plan section in plan-file)

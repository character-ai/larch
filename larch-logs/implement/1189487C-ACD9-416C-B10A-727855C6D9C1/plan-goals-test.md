## Goal
Implement issue #6535: [IMPLEMENTING] Migrate /implement checks legs (Steps 3, 6, 7a) to bgjob (#6524 chunk 6/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 6/11.

Scope: migrate the /implement checks legs — Step 3 checks, Step 6 entry, Step 7a, and the checks repair-loop re-entry composites — from `run_in_background`/`.bg-wait-active` marker machinery to bgjob start/wait, including the Step 3/commit-route marker branches in `dispatch_commit_route.py`.

Dependencies: blocked by #6530 (chunk 1/11: bgjob-wait contract + writer-parity lint rescope). Merge it first. Independent of the /design chunks.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (Step 5 review loop and Step 8 ship migrate in the next implement chunks; stall/state classifiers migrate later — the interim loss of `.bg-wait-active`-based abandoned-checks classification until that chunk lands matches the parent plan's own commit sequencing).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel (here: `.completed/step-3-terminal`, `.completed/step-6-terminal`, `.completed/step-7a-terminal`).
3. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate each per-step merge-result env before `bgjob start`.**
5. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`.
6. Treat `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
7. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
8. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
9. **Parallel lanes:** assign a unique `--step` slug per concurrent lane so registry rows and result envs cannot clobber each other.
10. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md
- Chunk-scoped: Step 3, Step 6, and Step 7a fences plus the general anti-halt wait text (Step 5 and Step 8 fences migrate in the next implement chunks).
- Replace Step 3, Step 6, and Step 7a immediate-background fences with bgjob start and wait loops per `bgjob-wait.md`.
- Update anti-halt text so `WAIT` means the next action is another identical `bgjob wait`.
- State explicitly: after the final `bgjob wait` `DONE`, required KVs come from the last `DONE` stdout and `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`, not from the start launcher, notification recovery, or intermediate wait turns.

### UPDATED: skills/implement/references/checks-repair-loop.md
- Convert pinned Step 3, Step 5, and Step 6 post-repair re-entry composite launch commands to the shared bgjob start/wait contract.
- After `NEXT_ACTION=continue`, route orchestrator through foreground `bgjob start` plus chunked `bgjob wait`, not bare composite relaunch fences.
- Gate re-entry continuation on `BGJOB_RC=0` and required KVs from result envs.
- Truncate merge-result envs before each re-entry start.
- Chunk note: the Step 5 re-entry composite text converted here must match the launch contract the Step 5 chunk gives its wrapper (thin bgjob launcher; same step-slug family); coordinate wording so the Step 5 chunk does not need to rewrite this file.

### UPDATED: skills/implement/scripts/run-step-checks.sh
- Stop writing `.bg-wait-active`.
- Truncate merge-result envs before each checks leg start.
- Launch Step 3 checks through bgjob with the existing Step 3 sentinel.
- Ensure Step 6 checks legs use the same result env convention.

### UPDATED: skills/implement/scripts/step-6-entry.sh
- Convert to bgjob start.
- Preserve `.completed/step-6-terminal`.

### UPDATED: python/larch/implement/step_7a.py
- Replace `_bg_wait_marker` usage with bgjob result and sentinel handling.
- Preserve `.completed/step-7a-terminal`.

### UPDATED: python/larch/implement/dispatch_commit_route.py
- Chunk-scoped: Step 3 checks and checks-commit-route composite marker branches (the `implement-step5-resume` and step5-self-review marker branches migrate with the Step 5 chunk).
- Replace `_write_bg_wait_marker` contexts with bgjob result handling or remove them when wrappers own bgjob launch — here: the `implement-step3-checks` `_bg_wait_marker` context in the `run-step-checks` path, `_clear_step3_bg_wait_sidecars`, and the `_optional_bg_wait_marker` / `_checks_commit_route_marker` branches for Step 3 and Step 6 checks sites.
- Update Step 3 and commit-route marker branches.
- Parse `BGJOB_RC` from result envs before resume routing.

### UPDATED: python/tests/implement/test_implement_dispatch.py
- Chunk-scoped: Step 3 pins (Step 5 resume and Step 8 pins land with their chunks).
- Replace `.bg-wait-active` expectations for Step 3 with bgjob start/wait contracts.
- Pin `BGJOB_RC` parsing before resume routing.

### UPDATED: python/tests/implement/test_step_7a.py
- Pin bgjob result handling and `.completed/step-7a-terminal`.

### UPDATED: scripts/test-implement-structure.sh
- Chunk-scoped: Step 3, Step 6, Step 7a, and checks-repair-loop rows (Step 5 and Step 8 rows migrate with their chunks).
- Replace this chunk's task-notification assertions with bgjob assertions.
- Keep pins for not-yet-migrated Step 5 and Step 8 surfaces unchanged.

### UPDATED: scripts/test-implement-anti-polling-rule.sh
- Update anti-polling rules for bgjob `WAIT`.
- Keep legacy defense assertions only for compatibility surfaces (including /design rows already migrated by earlier chunks and implement Step 5 / Step 8 rows still pending migration).

### UPDATED: scripts/test-implement-fence-shape.sh
- Update `EXPECTED_OLD` and `EXPECTED_NEW` for this chunk's changed `skills/implement/SKILL.md` fences.

### MAY_UPDATE: python/larch/implement/implement_dispatch.py
- Aggregator import/export adjustments only if this chunk changes entry-point shapes; the full branch migration (including Step 8 routing) lands with the Step 8 chunk.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `BGJOB_STATUS=DEAD` must not parse stale step stdout as success.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- `bgjob wait` shell exit 0 on `WAIT` or `DEAD` must not advance the step.
- Existing sentinels may exist from prior attempts. Result env plus identity-checked registry state must decide current completion.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start`.
- Checks repair-loop must not relaunch bare composites and bypass bgjob wait.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC`.
- A result env omits a required legacy KV, causing false success or false stall.
- Stale merge-input env satisfies KVs after `BGJOB_RC=0` without fresh child output.
- Checks repair-loop still relaunches bare composites and bypasses bgjob wait.
- `test-implement-structure.sh` rows for not-yet-migrated Step 5 / Step 8 surfaces get rewritten prematurely and break sibling chunks.

## Testing strategy

1. `bash scripts/test-implement-structure.sh`
2. `bash scripts/test-implement-anti-polling-rule.sh`
3. `bash scripts/test-implement-fence-shape.sh`
4. `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py -q`
5. `python3 python/cli.py lint bg-wait-coverage`
6. `python3 python/cli.py lint bg-wait-writer-parity`
7. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs in wrappers immediately before every `bgjob start`.
- Use `larch.io` helpers for result env writes and reads where practical.
- Use config constants for bgjob status and rc keys.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion (`bg_wait.py` is narrowed in the stall/state chunk after its callers migrate).

## Acceptance

1. Migrated `run-step-checks.sh` and `step-6-entry.sh` harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line each, harness-asserted.
2. Step 3 / Step 6 / Step 7a `DONE` continuation is gated on `BGJOB_RC=0` plus required step KVs at every migrated orchestrator branch; prompt-shape harnesses assert the gate text.
3. `run-step-checks.sh` no longer writes `.bg-wait-active`; `python3 python/cli.py lint bg-wait-writer-parity` passes.
4. Checks repair-loop re-entry routes through foreground `bgjob start` plus chunked `bgjob wait` with merge-env truncation before each re-entry start.
5. `.completed/step-3-terminal`, `.completed/step-6-terminal`, and `.completed/step-7a-terminal` keep being written; every routing contract stays unchanged; legacy hooks stay functional and inert.
6. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 250
diff_deleted: 180
mechanical_churn: true
diff_lines: 430

## Test plan
(no test plan section in plan-file)

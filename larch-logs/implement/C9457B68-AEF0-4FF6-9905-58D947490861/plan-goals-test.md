## Goal
Implement issue #6536: [IMPLEMENTING] Migrate /implement Step 5 review/self-review/resume loops to bgjob (#6524 chunk 7/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 7/11.

Scope: migrate the /implement Step 5 review, self-review, and resume loops — wrapper scripts, skill prose, and the Step 5 marker branches in `dispatch_commit_route.py` — from bespoke detach/reattach + `run_in_background` to bgjob daemon ownership with live-registry rejoin.

Dependencies: blocked by #6531 (chunk 2/11: review engine merge-result KV emission) and #6535 (chunk 6/11: /implement checks legs, which lands the SKILL.md anti-halt bgjob text and the checks-side dispatch migration). Merge those first.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (Step 8 ship migrates next; stall/state classifiers after that).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel (here: `.completed/step-5-terminal`, `.completed/step-5-resume-terminal`).
3. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate each per-step merge-result env before `bgjob start`.**
5. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`.
6. Treat `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
7. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
8. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
9. **Live-registry rejoin:** before every `bgjob start` for the `implement-step5-review` loop, if an identity-valid registry row exists for that step, refuse a second start and require chunked `bgjob wait` instead; clear only stale or dead rows before a fresh start.
10. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md
- Chunk-scoped: Step 5 fences only (Steps 3/6/7a landed in the previous chunk; Step 8 lands in the next).
- Replace Step 5 immediate-background fences with bgjob start and wait loops per `bgjob-wait.md`.
- Extend the anti-halt `WAIT` text and the "required KVs come from the last `DONE` stdout and `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`" statement to the Step 5 rows.

### UPDATED: skills/implement/references/self-review.md
- Convert Step 5 review, self-review, and resume variants to bgjob ownership.
- Remove `.step5-wrapper-detached` and `.step5-reattach-active` prompt contracts after tests pin replacement behavior.
- Gate continuation on `BGJOB_RC=0`.

### UPDATED: skills/implement/references/step5-review-branches.md
- Convert MAV, coder-handoff, stall, and resume branches to bgjob start plus chunked wait.
- Rebind resume and re-entry parsing to bgjob result envs with `BGJOB_RC=0` gate.
- Document same-step rejoin: a live identity-valid registry row for the Step 5 loop must be rejoined via `bgjob wait`, not relaunched; stale or dead rows are cleared before a fresh `bgjob start`.

### UPDATED: skills/implement/scripts/step-5-review.sh
- Replace bespoke loop detach and reattach with bgjob daemon ownership.
- Ensure owner death and orphan handling are delegated to bgjob.
- Write normalized Step 5 KVs to the merge-result env.
- Preserve `.completed/step-5-terminal`.
- On re-entry when a live identity-valid Step 5 registry row exists, refuse a second `bgjob start` and require chunked `bgjob wait` instead.

### UPDATED: skills/implement/scripts/step-5-review.md
- Rebind the contract to bgjob daemon ownership, owner-death/orphan handling, and merge-result env completion.
- Drop detach/reattach sidecar prose.
- Document re-entry rejoin vs fresh-start rules.

### UPDATED: skills/implement/scripts/step-5-resume.sh
- Convert the resume fence to a thin `bgjob start` launcher for `implement-step5-resume` (or equivalent step name).
- Delegate daemon ownership, orphan handling, and result-env merge to bgjob.
- Preserve timing capture and `.completed/step-5-resume-terminal` semantics.

### UPDATED: python/larch/implement/dispatch_commit_route.py
- Chunk-scoped: Step 5 marker branches (the Step 3 checks and commit-route branches landed in the previous chunk).
- Replace `_write_bg_wait_marker` contexts with bgjob result handling or remove them when wrappers own bgjob launch — here: the `implement-step5-resume` `_bg_wait_marker` context in `checks_step5_resume_main` and the step5-self-review checks-commit-route marker branches.
- Update Step 5 resume and Step 5 self-review marker branches.
- Parse `BGJOB_RC` from result envs before resume routing.

### UPDATED: python/tests/implement/test_implement_dispatch.py
- Chunk-scoped: Step 5 resume pins (Step 3 pins landed in the previous chunk; Step 8 pins land in the next).
- Replace `.bg-wait-active` expectations for Step 5 resume with bgjob start/wait contracts.
- Pin `BGJOB_RC` parsing before resume routing.

### UPDATED: python/tests/review/test_review_and_fix.py
- Chunk-scoped: wrapper-ownership pins (the merge-KV emission coverage landed with the engine chunk).
- Replace Step 5 detached-wrapper expectations with bgjob registry ownership expectations.

### UPDATED: skills/implement/scripts/test-step-5-review.sh
- Pin Step 5 bgjob ownership, owner death, orphaned result, and no detach sidecars.
- Pin re-entry behavior: live registry row requires wait rejoin, not second start; dead row cleared before fresh start.
- Add stale merge-env regression assertion.

### UPDATED: scripts/test-implement-structure.sh
- Chunk-scoped: Step 5 rows (Step 3/6/7a rows landed in the previous chunk; Step 8 rows land in the next).
- Replace Step 5 task-notification assertions with bgjob assertions.
- Assert `BGJOB_RC=0` gates on Step 5 completion routing.
- Add Step 5 resume wrapper and `step5-review-branches.md` bgjob contract pins.

### UPDATED: scripts/test-implement-fence-shape.sh
- Update `EXPECTED_OLD` and `EXPECTED_NEW` for this chunk's changed `skills/implement/SKILL.md` fences.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/implement/references/self-review.md` row (its prose is migrated by this chunk).
- Keep every other row; sibling chunks remove their own rows as they migrate those files.

### MAY_UPDATE: python/larch/implement/implement_dispatch.py
- Aggregator import/export adjustments only if this chunk changes entry-point shapes; the full branch migration lands with the Step 8 chunk.

### MAY_UPDATE: scripts/test-implement-anti-polling-rule.sh
- Update only Step 5 rows this chunk's edits break; the harness's bgjob rewrite landed with the checks chunk.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `BGJOB_STATUS=DEAD` must not parse stale step stdout as success.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- Existing sentinels may exist from prior attempts. Result env plus identity-checked registry state must decide current completion.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start`.
- Step 5 re-entry must rejoin a live registry row via `bgjob wait` and must not launch a second loop daemon.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC`.
- A result env omits a required legacy KV, causing false success or false stall.
- Stale merge-input env satisfies KVs after `BGJOB_RC=0` without fresh child output.
- Step 5 detach sidecars are removed before bgjob owner-death and re-entry tests cover the replacement.
- Step 5 resume path remains on legacy direct launch because `step-5-resume.sh` or `step5-review-branches.md` were not migrated.
- A second live Step 5 loop daemon starts and races on the same result envs.

## Testing strategy

1. `bash scripts/test-implement-structure.sh`
2. `bash scripts/test-implement-fence-shape.sh`
3. `bash skills/implement/scripts/test-step-5-review.sh`
4. `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/review/test_review_and_fix.py -q`
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

1. `git grep -l "run_in_background" skills/implement/references/self-review.md` returns nothing; the `self-review.md` row is removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
2. Migrated `step-5-review.sh` and `step-5-resume.sh` harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line each, harness-asserted.
3. Step 5 `DONE` continuation is gated on `BGJOB_RC=0` plus required step KVs at every migrated orchestrator branch; prompt-shape harnesses assert the gate text.
4. Step 5 re-entry rejoins a live identity-valid registry row via `bgjob wait` and never launches a second loop daemon; owner death and orphaned results are delegated to bgjob (pinned in `test-step-5-review.sh` and `test_review_and_fix.py`).
5. `.completed/step-5-terminal` and `.completed/step-5-resume-terminal` keep being written; every routing contract stays unchanged; legacy hooks stay functional and inert.
6. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 260
diff_deleted: 200
mechanical_churn: true
diff_lines: 460

## Test plan
(no test plan section in plan-file)

## Goal
Implement issue #6532: [IMPLEMENTING] Migrate /design Step 3 plan-review loop to bgjob start/wait (#6524 chunk 3/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 3/11.

Scope: migrate the /design Step 3 plan-review loop — wrapper, skill prose, Gate B / Step 3 resume branches, and the Step 3 result-env normalizer — from `run_in_background` + task-notification recovery to `bgjob start` + chunked foreground `bgjob wait`.

Dependencies: blocked by #6530 (chunk 1/11: bgjob-wait contract + writer-parity lint rescope) and #6531 (chunk 2/11: plan-review engine merge-result KV emission). Merge those first.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them (Step 4 tail / Gate C presentation, Step 5c, Step 6, final-summary, and brainstorm migrate in later design chunks).

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel (here: `.completed/step-3-terminal`).
3. Make the migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate the per-step merge-result env before `bgjob start`** so stale KVs from a prior attempt cannot satisfy required-key gates after a fresh child exits `BGJOB_RC=0` without writing new values.
5. Move step result KVs into a merge env file passed through `bgjob start --merge-result-env`.
6. Treat `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
7. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
8. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
9. **Live-registry rejoin:** before every `bgjob start` for the `design-step3-review` loop, if an identity-valid registry row exists for that step, refuse a second start and require chunked `bgjob wait` instead; clear only stale or dead rows before a fresh start.
10. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/design/SKILL.md
- Chunk-scoped: Step 3 sections only (Step 4 tail, Step 5c, final-summary, and brainstorm migrate in later design chunks).
- Replace Step 3 immediate-background instructions with `bgjob start` and chunked `bgjob wait` per `bgjob-wait.md`.
- Delete migrated premature notification recovery prose from the Step 3 live call sites.
- Keep only compatibility text that #6516 will remove later.
- Gate Step 3 continuation on `BGJOB_RC=0` plus required KVs from the final `DONE` stdout and `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env`.
- Rebind Step 3 post-`DONE` parsing to read `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first via `python/cli.py design read-result-env` (or equivalent), with legacy `.step3-review-result.env` fallback only when the bgjob path is absent.
- Rebind Step 3 resume fences to bgjob `DONE` plus result-env parsing; remove `design-step3-review.sh --starting-round` immediate-background resume prose.

### UPDATED: skills/design/references/plan-review.md
- Replace `run_in_background` launch and resume instructions with bgjob launch and wait semantics.
- Preserve `STEP3_REVIEW_LOOP_STATUS` and resume branches.
- Rebind post-`DONE` result parsing to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with controlled legacy fallback.
- Require `BGJOB_RC=0` before routing on loop envelope KVs.
- Resume mid-loop through chunked `bgjob wait` on a live `design-step3-review` registry row; do not relaunch when identity-valid.

### UPDATED: skills/design/references/approval-gates.md
- Chunk-scoped: Step 3 outcomes and Gate B only (Gate C presentation and `resume@4b` migrate with the Step 4 tail chunk).
- Rebind **Step 3 outcomes** (`NEXT_ACTION` table and resume branches) from `.step3-review-result.env` to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback only when absent.
- Gate Gate B post-apply resume and Step 3 mid-loop returns on `BGJOB_RC=0` plus required loop envelope KVs from the bgjob result env.
- Replace `design-step3-review.sh --starting-round …` immediate-background resume instructions with bgjob `DONE` plus result-env parsing and live-registry rejoin via `bgjob wait`.
- Rebind any Step 3 re-entry prose that still assumes task-notification completion to bgjob `DONE` plus result-env parsing.

### UPDATED: skills/design/scripts/design-step3-review.sh
- Remove `.bg-wait-active`, detach, and reattach ownership logic.
- Keep precondition rehydration and pause-save checks.
- Truncate `$DESIGN_TMPDIR/.step3-review-result.env` (merge input) immediately before start.
- Write step KVs to the merge input; daemon merges into `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env`.
- `exec` bgjob start for `design-step3-review` with `--merge-result-env "$DESIGN_TMPDIR/.step3-review-result.env"` and sentinel `.completed/step-3-terminal`.
- On re-entry when a live identity-valid `design-step3-review` registry row exists, refuse a second `bgjob start`.

### UPDATED: skills/design/scripts/design-step3-review.md
- Update the wrapper contract to bgjob ownership and result env parsing.
- Name `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` as completion truth.
- Preserve sentinel behavior descriptions.
- Document live-registry rejoin vs fresh-start rules.

### UPDATED: python/larch/review/plan_review_normalize.py
- Repoint `_step3_normalize_read_result_env`, `_step3_read_result_env_quiet`, and `--read-result-env` to read `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first, with controlled fallback to `.step3-review-result.env` only when absent.
- Include `BGJOB_RC` in required keys for Step 3 completion routing.
- Update comments and normalization paths that still mention task-notification races.
- Preserve Step 3 result KV compatibility for downstream envelopes.

### UPDATED: python/tests/review/test_plan_review.py
- Chunk-scoped: normalize-path pins (the merge-input KV emission coverage landed with the engine chunk).
- Pin `_step3_normalize_read_result_env` and `--read-result-env` to prefer `bgjob/design-step3-review.result.env`.
- Add `BGJOB_RC` required-key coverage and legacy-path fallback tests.

### UPDATED: skills/design/scripts/test-design-step3-review.sh
- Assert wrapper stdout is exactly the bgjob started line.
- Assert no `.bg-wait-active` writer remains.
- Assert completion parsing prefers `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` and includes `BGJOB_RC` in required keys.
- Add stale merge-env regression: pre-seed merge input with prior-run KVs, start fresh child that writes only `BGJOB_RC=0`, assert routing does not succeed without fresh step KVs.

### UPDATED: scripts/test-design-structure.sh
- Chunk-scoped: Step 3 rows only (Step 4, Step 5c, final-summary, and brainstorm rows migrate with their chunks).
- Replace task-notification/immediate-background pins with `bgjob-wait.md` references for Step 3.
- Drop or rewrite `SHARED_DESIGN_WAIT_MD` notification-recovery `contains` / `not_contains` rows that conflict with this chunk's migrated Step 3 fences.
- Add assertions that the migrated Step 3 fences require `BGJOB_RC=0` gating and bgjob result-env reads.
- Keep sentinel compatibility assertions.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/design/references/plan-review.md` row (its prose is migrated by this chunk).
- Keep every other row; sibling chunks remove their own rows as they migrate those files.

### MAY_UPDATE: scripts/test-implement-anti-polling-rule.sh
- This harness also pins /design SKILL.md background-wait hot paths; update only rows this chunk's Step 3 edits break. The full bgjob rewrite of this harness lands with the /implement checks chunk.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `BGJOB_STATUS=DEAD` must not parse stale step stdout as success.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- `bgjob wait` shell exit 0 on `WAIT` or `DEAD` must not advance the step.
- Existing sentinels may exist from prior attempts. Result env plus identity-checked registry state must decide current completion.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start`.
- Gate B Step 3 resume must not read only legacy `.step3-review-result.env` or relaunch via immediate-background fences.
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC`.
- Stale merge-input env satisfies KVs after `BGJOB_RC=0` without fresh child output.
- Step 3 normalize still reads `.step3-review-result.env` and misses `BGJOB_RC` or fresh loop status.
- Gate B resume still launches `design-step3-review.sh` immediate-background instead of rejoining via `bgjob wait`.
- `test-design-structure.sh` still pins notification-recovery literals and fails CI after skill migration.
- Allowlist row removed before all `plan-review.md` prose is migrated, causing `lint bg-wait-coverage` failure.

## Testing strategy

1. `bash scripts/test-design-structure.sh`
2. `bash skills/design/scripts/test-design-step3-review.sh`
3. `python3 -m pytest python/tests/review/test_plan_review.py -q`
4. `python3 python/cli.py lint bg-wait-coverage`
5. `python3 python/cli.py lint bg-wait-writer-parity`
6. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs in wrappers immediately before every `bgjob start`.
- Use `larch.io` helpers for result env writes and reads where practical.
- Use config constants for bgjob status and rc keys.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.

## Acceptance

1. `git grep -l "run_in_background" skills/design/references/plan-review.md` returns nothing; the `plan-review.md` row is removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
2. The migrated `design-step3-review.sh` harness-visible foreground stdout is exactly one `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>` line, harness-asserted in `test-design-step3-review.sh`.
3. Step 3 `DONE` continuation is gated on `BGJOB_RC=0` plus required loop envelope KVs at every migrated orchestrator branch; prompt-shape harnesses assert the gate text.
4. `_step3_normalize_read_result_env` and `--read-result-env` prefer `bgjob/design-step3-review.result.env` with legacy fallback, and `BGJOB_RC` is a required key (pinned in `test_plan_review.py`).
5. `.completed/step-3-terminal` keeps being written; Step 3 routing contracts stay unchanged; legacy hooks stay functional and inert.
6. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 260
diff_deleted: 190
mechanical_churn: true
diff_lines: 450

## Test plan
(no test plan section in plan-file)

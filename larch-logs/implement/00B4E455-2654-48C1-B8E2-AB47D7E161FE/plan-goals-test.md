## Goal
Implement issue #6534: [IMPLEMENTING] Migrate /design final-summary and brainstorm lanes to bgjob (#6524 chunk 5/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 5/11.

Scope: finish the /design migration — final-summary cancellation, external brainstorm lanes, the sentinel-host documentation, and the end-state narrowing of the design bg-wait marker helper; remove the now-clean /design rows from the bg-wait allowlist.

Dependencies: blocked by #6533 (chunk 4/11: /design Step 4 tail + Step 5c + Step 6). Merge it first (chunks 1-3 are transitive prerequisites through it).

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them. After this chunk, no /design surface may request `run_in_background`.

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Preserve every existing terminal sentinel (here: `.completed/step-final-summary`).
3. Make each migrated wrapper a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
4. **Clear or recreate each per-step merge-result env before `bgjob start`** (including per-lane brainstorm merge envs).
5. Treat `$DESIGN_TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
6. Gate normal continuation on both `BGJOB_RC=0` and required step KVs present in the final `DONE` stdout and/or the bgjob result env.
7. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the step's existing failure or stall branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
8. **Parallel lanes:** assign a unique `--step` slug per concurrent external brainstorm lane so registry rows and result envs cannot clobber each other.
9. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/design/SKILL.md
- Chunk-scoped: final-summary cancellation and brainstorm sections (Steps 3, 4 tail, and 5c landed in earlier chunks).
- Replace final-summary cancellation and brainstorm immediate-background instructions with `bgjob start` and chunked `bgjob wait` per `bgjob-wait.md`.
- Delete migrated premature notification recovery prose from these live call sites; keep only compatibility text that #6516 will remove later.
- Gate final-summary continuation on `BGJOB_RC=0` plus required KVs from the final `DONE` stdout and `$DESIGN_TMPDIR/bgjob/<step>.result.env`.
- After this chunk, `skills/design/SKILL.md` contains no `run_in_background` requests; remove its allowlist row (below).

### UPDATED: skills/design/references/brainstorm.md
- Convert external brainstorm lanes to per-lane bgjob start and wait, or foreground collection where parallelism is not needed.
- Keep Claude Agent fallback behavior unchanged.
- Require **unique `--step` slugs per parallel lane** (for example `design-brainstorm-framing`, `design-brainstorm-diverge`, `design-brainstorm-converge`).
- Truncate per-lane merge-result envs before each lane start.

### UPDATED: skills/design/references/sentinel-host-table.md
- Document bgjob result envs as completion truth.
- Keep terminal sentinels as compatibility transition markers.
- Name `design-step4-tail` result env as Step 4 completion truth.

### UPDATED: python/larch/design/design_core.py
- Chunk-scoped: end-state narrowing now that the last design caller migrates here.
- Retire `_bg_wait_marker_context` call paths.
- Keep only compatibility helpers still needed by retained legacy hooks, if any.

### UPDATED: python/larch/design/design_terminal.py
- Migrate final-summary cancellation to bgjob.
- Preserve `.completed/step-final-summary`.
- Allow `read_result_env_main` to read bgjob result env paths under `$DESIGN_TMPDIR/bgjob/`.
- Truncate merge-result env before final-summary start.

### UPDATED: python/tests/design/test_design_lifecycle.py
- Chunk-scoped: final-summary pins (Step 4 tail, Step 5c, and Step 6 pins landed in the previous chunk).
- Pin final-summary bgjob behavior.

### UPDATED: scripts/test-design-structure.sh
- Chunk-scoped: final-summary and brainstorm rows.
- Replace task-notification/immediate-background pins with `bgjob-wait.md` references for final-summary waits.
- Drop or rewrite `SHARED_DESIGN_WAIT_MD` notification-recovery `contains` / `not_contains` rows that conflict with this chunk's migrated fences.
- Add assertions that the migrated final-summary fences require `BGJOB_RC=0` gating and bgjob result-env reads.
- Keep sentinel compatibility assertions.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/design/SKILL.md` and `skills/design/references/brainstorm.md` rows (their prose is migrated by this chunk).
- Keep every other row; sibling chunks remove their own rows as they migrate those files.

### MAY_UPDATE: scripts/test-implement-anti-polling-rule.sh
- This harness also pins /design SKILL.md background-wait hot paths; update only rows this chunk's edits break. The full bgjob rewrite of this harness lands with the /implement checks chunk.

## Edge cases

- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` with no intervening prose or tools.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to failure or stall.
- Parallel brainstorm lanes must use distinct `--step` slugs so registry rows and result envs do not clobber each other.
- Stale merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each `bgjob start` (per lane).
- Recycled PID or PGID must never be signaled. Use identity-checked helpers only.
- Retained legacy hooks must remain functional for #6516, but migrated paths should not trip them.

## Failure modes

- Wrapper stdout gains banners and breaks harness parsing.
- A prompt path continues on `DONE` without checking `BGJOB_RC`.
- Parallel lanes reuse one `--step` slug and overwrite result envs mid-run.
- Allowlist rows removed while some design prose still requests `run_in_background`, causing `lint bg-wait-coverage` failure.
- `test-design-structure.sh` still pins notification-recovery literals and fails CI after skill migration.

## Testing strategy

1. `bash scripts/test-design-structure.sh`
2. `python3 -m pytest python/tests/design/test_design_lifecycle.py -q`
3. `python3 python/cli.py lint bg-wait-coverage`
4. `python3 python/cli.py lint bg-wait-writer-parity`
5. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- Prefer Python helpers behind `python3 python/cli.py` for non-trivial parsing, registry liveness, and result-env reads.
- Keep Bash wrappers thin and macOS Bash 3.2-compatible.
- Truncate merge-result env inputs immediately before every `bgjob start`.
- Use `larch.io` helpers for result env writes and reads where practical.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.

## Acceptance

1. `git grep -l "run_in_background" skills/design/` returns nothing; the `skills/design/SKILL.md` and `skills/design/references/brainstorm.md` rows are removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
2. Final-summary `DONE` continuation is gated on `BGJOB_RC=0` plus required KVs from the final `DONE` stdout and the bgjob result env; prompt-shape harnesses assert the gate text.
3. Brainstorm external lanes use unique per-lane `--step` slugs with per-lane merge-env truncation; Claude Agent fallback is unchanged.
4. `.completed/step-final-summary` keeps being written; every routing contract stays unchanged; legacy hooks stay functional and inert.
5. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.

diff_added: 170
diff_deleted: 130
mechanical_churn: true
diff_lines: 300

## Test plan
(no test plan section in plan-file)
